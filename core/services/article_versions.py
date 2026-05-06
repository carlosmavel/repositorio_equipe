"""Helpers para snapshots e versionamento de artigos.

As funções deste módulo apenas adicionam objetos à sessão ativa do SQLAlchemy e
atualizam os contadores do artigo em memória. Elas não executam commit para que
os fluxos chamadores mantenham artigo, anexos, notificações e snapshots no mesmo
limite transacional.
"""
from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from typing import Any

try:
    from ..database import db
    from ..enums import ArticleStatus, ArticleVisibility
    from ..models import ArticleVersion
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.database import db
    from core.enums import ArticleStatus, ArticleVisibility
    from core.models import ArticleVersion

_WORD_RE = re.compile(r"\S+", re.UNICODE)
_TEXT_HASH_SEPARATOR = "\x1f"


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (ArticleStatus, ArticleVisibility)):
        return value.value
    return str(value)


def extract_plain_text_for_count(text: str | None) -> str:
    """Extrai texto legível de HTML/texto e normaliza espaços para contagem segura."""
    without_tags = re.sub(r"<[^>]*>", " ", text or "")
    unescaped = html.unescape(without_tags).replace("\xa0", " ")
    return re.sub(r"\s+", " ", unescaped).strip()


def calculate_plain_text_char_count(text: str | None) -> int:
    """Conta caracteres do conteúdo textual legível, ignorando marcação HTML."""
    return len(extract_plain_text_for_count(text))


def calculate_text_char_count(text: str | None) -> int:
    """Conta caracteres do texto persistido no snapshot."""
    return len(text or "")


def calculate_reduction_percent(previous_count: int | None, new_count: int | None) -> float:
    """Calcula percentual de redução entre duas contagens textuais."""
    if previous_count is None or new_count is None or previous_count <= 0 or new_count >= previous_count:
        return 0.0
    return ((previous_count - new_count) / previous_count) * 100


def is_drastic_content_reduction(previous_count: int, new_count: int, reduction_percent: float | None) -> bool:
    """Aplica regras de redução significativa usadas no cliente e no backend."""
    percent_reduction = reduction_percent or 0
    return percent_reduction > 70 or (previous_count > 2000 and new_count < 300)


def calculate_text_word_count(text: str | None) -> int:
    """Conta palavras por sequências não brancas, compatível com HTML sanitizado."""
    normalized = (text or "").strip()
    if not normalized:
        return 0
    return len(_WORD_RE.findall(normalized))


def calculate_text_hash(article_or_text: Any, title: str | None = None, status: Any = None, visibility: Any = None) -> str:
    """Gera hash SHA-256 estável do conteúdo textual e metadados principais.

    O primeiro argumento pode ser um Article (preferencial) ou diretamente o
    texto. Quando for Article, título/status/visibilidade são lidos dele.
    """
    if hasattr(article_or_text, "texto"):
        article = article_or_text
        text = article.texto
        title = article.titulo
        status = article.status
        visibility = article.visibility
    else:
        text = article_or_text

    payload = _TEXT_HASH_SEPARATOR.join(
        [
            title or "",
            text or "",
            _enum_value(status) or "",
            _enum_value(visibility) or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot_changed_user(changed_by_user: Any | None) -> dict[str, Any]:
    """Retorna um snapshot textual do usuário alterador e de sua hierarquia."""
    if not changed_by_user:
        return {
            "changed_by_user_id": None,
            "changed_by_username": None,
            "changed_by_email": None,
            "changed_by_nome_completo": None,
            "changed_by_cargo_nome": None,
            "changed_by_setor_nome": None,
            "changed_by_celula_nome": None,
            "changed_by_estabelecimento_nome_fantasia": None,
        }

    cargo = getattr(changed_by_user, "cargo", None)
    setor = getattr(changed_by_user, "setor", None)
    celula = getattr(changed_by_user, "celula", None)
    estabelecimento = getattr(changed_by_user, "estabelecimento", None)
    return {
        "changed_by_user_id": getattr(changed_by_user, "id", None),
        "changed_by_username": getattr(changed_by_user, "username", None),
        "changed_by_email": getattr(changed_by_user, "email", None),
        "changed_by_nome_completo": getattr(changed_by_user, "nome_completo", None),
        "changed_by_cargo_nome": getattr(cargo, "nome", None),
        "changed_by_setor_nome": getattr(setor, "nome", None),
        "changed_by_celula_nome": getattr(celula, "nome", None),
        "changed_by_estabelecimento_nome_fantasia": getattr(estabelecimento, "nome_fantasia", None),
    }


def _next_version_revision(article: Any, change_action: str) -> tuple[int, int]:
    current_version = int(getattr(article, "current_version_number", 0) or 0)
    current_revision = int(getattr(article, "current_revision_number", 0) or 0)

    if change_action in {"create_initial", "initial_create"}:
        return 0, 1
    if change_action == "approve":
        return current_version + 1, 0
    # envio para aprovação, edição pós-aprovação, ajuste, rejeição, revisão e restauração.
    return current_version, current_revision + 1


def _safe_int(value: Any | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _drastic_reduction_metrics(text_char_count: int, drastic_reduction_data: dict[str, Any] | None) -> dict[str, Any]:
    previous_count = None
    new_count = None
    reduction_percent = None
    detected = False
    threshold_percent = 50.0

    if drastic_reduction_data:
        previous_count = _safe_int(
            drastic_reduction_data.get("previous_char_count")
            if "previous_char_count" in drastic_reduction_data
            else drastic_reduction_data.get("previous_text_char_count")
        )
        new_count = _safe_int(drastic_reduction_data.get("new_char_count"))
        reduction_percent = _safe_float(drastic_reduction_data.get("reduction_percent"))
        detected = bool(drastic_reduction_data.get("drastic_reduction", False))
        threshold_percent = float(drastic_reduction_data.get("threshold_percent", threshold_percent))

    if new_count is None:
        new_count = text_char_count
    if reduction_percent is None:
        reduction_percent = calculate_reduction_percent(previous_count, new_count)

    if drastic_reduction_data and "drastic_reduction" in drastic_reduction_data:
        detected = bool(drastic_reduction_data.get("drastic_reduction"))
    elif reduction_percent is not None:
        detected = reduction_percent >= threshold_percent

    return {
        "previous_text_char_count": previous_count,
        "text_reduction_percent": reduction_percent,
        "drastic_reduction_detected": detected,
        "previous_char_count": previous_count,
        "new_char_count": new_count,
        "reduction_percent": reduction_percent,
        "drastic_reduction": detected,
    }


def _words_for_comparison(text: str | None) -> list[str]:
    """Normaliza texto legível para comparar palavras entre versões."""
    plain_text = extract_plain_text_for_count(text).casefold()
    return re.findall(r"\w+", plain_text, re.UNICODE)


def _counter_delta_items(from_words: list[str], to_words: list[str]) -> list[dict[str, int | str]]:
    from collections import Counter

    removed_counter = Counter(from_words) - Counter(to_words)
    added_counter = Counter(to_words) - Counter(from_words)
    words = sorted(set(removed_counter) | set(added_counter))
    return [
        {
            "word": word,
            "removed": int(removed_counter.get(word, 0)),
            "added": int(added_counter.get(word, 0)),
        }
        for word in words
    ]


def compare_article_versions(from_version: ArticleVersion, to_version: ArticleVersion) -> dict[str, Any]:
    """Compara dois snapshots do mesmo artigo usando apenas texto e metadados.

    A comparação é propositalmente simples: calcula deltas de caracteres em
    título/texto, contagens de palavras adicionadas/removidas e uma lista de
    metadados textuais que mudaram entre os snapshots. Anexos não participam.
    """
    if from_version.article_id != to_version.article_id:
        raise ValueError("As versões comparadas devem pertencer ao mesmo artigo.")

    from_text = from_version.texto or ""
    to_text = to_version.texto or ""
    from_title = from_version.titulo or ""
    to_title = to_version.titulo or ""
    from_words = _words_for_comparison(from_text)
    to_words = _words_for_comparison(to_text)
    word_deltas = _counter_delta_items(from_words, to_words)

    metadata_fields = (
        ("status", "Status"),
        ("visibility", "Visibilidade"),
        ("tipo_id", "Tipo"),
        ("area_id", "Área"),
        ("sistema_id", "Sistema"),
        ("instituicao_id", "Instituição"),
        ("estabelecimento_id", "Estabelecimento"),
        ("setor_id", "Setor"),
        ("vis_celula_id", "Célula de visibilidade"),
        ("celula_id", "Célula autora"),
        ("user_id_original_author", "Autor original"),
    )
    metadata_changes = []
    for field, label in metadata_fields:
        from_value = getattr(from_version, field, None)
        to_value = getattr(to_version, field, None)
        if from_value != to_value:
            metadata_changes.append({
                "field": field,
                "label": label,
                "from": from_value,
                "to": to_value,
            })

    return {
        "char_delta": len(to_text) - len(from_text),
        "title_char_delta": len(to_title) - len(from_title),
        "text_char_delta": len(to_text) - len(from_text),
        "from_text_char_count": len(from_text),
        "to_text_char_count": len(to_text),
        "from_title_char_count": len(from_title),
        "to_title_char_count": len(to_title),
        "words_added_count": sum(item["added"] for item in word_deltas),
        "words_removed_count": sum(item["removed"] for item in word_deltas),
        "word_deltas": word_deltas,
        "metadata_changes": metadata_changes,
    }


def create_article_version_snapshot(
    article,
    changed_by_user,
    change_action,
    change_reason=None,
    source_status_before=None,
    source_status_after=None,
    force_version=None,
    force_revision=None,
    correlation_id=None,
    drastic_reduction_data=None,
):
    """Cria snapshot versionado do estado atual do artigo na sessão ativa.

    A função atualiza `article.current_version_number` e
    `article.current_revision_number`, adiciona `ArticleVersion` à sessão e
    retorna a instância criada. Não há commit aqui por desenho transacional.
    """
    version_number, revision_number = _next_version_revision(article, change_action)
    if force_version is not None:
        version_number = int(force_version)
    if force_revision is not None:
        revision_number = int(force_revision)

    titulo = article.titulo or ""
    texto = article.texto or ""
    text_char_count = calculate_text_char_count(texto)
    metrics = _drastic_reduction_metrics(text_char_count, drastic_reduction_data)

    snapshot = ArticleVersion(
        article=article,
        article_id=getattr(article, "id", None),
        version_number=version_number,
        revision_number=revision_number,
        titulo=titulo,
        texto=texto,
        status=_enum_value(article.status) or ArticleStatus.RASCUNHO.value,
        visibility=_enum_value(article.visibility) or ArticleVisibility.CELULA.value,
        tipo_id=article.tipo_id,
        area_id=article.area_id,
        sistema_id=article.sistema_id,
        instituicao_id=article.instituicao_id,
        estabelecimento_id=article.estabelecimento_id,
        setor_id=article.setor_id,
        vis_celula_id=article.vis_celula_id,
        celula_id=article.celula_id,
        user_id_original_author=article.user_id,
        change_action=change_action,
        change_reason=change_reason,
        source_status_before=_enum_value(source_status_before),
        source_status_after=_enum_value(source_status_after),
        title_char_count=len(titulo),
        text_char_count=text_char_count,
        text_word_count=calculate_text_word_count(texto),
        content_hash=calculate_text_hash(article),
        correlation_id=correlation_id,
        created_at=datetime.now(timezone.utc),
        **snapshot_changed_user(changed_by_user),
        **metrics,
    )
    article.current_version_number = version_number
    article.current_revision_number = revision_number
    db.session.add(snapshot)
    return snapshot


RELEVANT_ARTICLE_FIELDS = (
    "titulo",
    "texto",
    "status",
    "visibility",
    "tipo_id",
    "area_id",
    "sistema_id",
    "instituicao_id",
    "estabelecimento_id",
    "setor_id",
    "vis_celula_id",
    "celula_id",
)


def article_relevant_state_changed(article, **new_values) -> bool:
    """Indica se uma alteração toca campos auditados/versionados."""
    for field, new_value in new_values.items():
        if field not in RELEVANT_ARTICLE_FIELDS:
            continue
        old_value = getattr(article, field)
        if field in {"status", "visibility"}:
            old_value = _enum_value(old_value)
            new_value = _enum_value(new_value)
        if old_value != new_value:
            return True
    return False
