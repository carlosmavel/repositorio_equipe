"""Sincronização idempotente do catálogo de permissões."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from ..models import Funcao
    from ..permission_catalog import CATALOG, CATALOG_BY_CODE, CODE_ALIASES, DEPRECATED_CODES
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.models import Funcao
    from core.permission_catalog import CATALOG, CATALOG_BY_CODE, CODE_ALIASES, DEPRECATED_CODES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PermissionSyncResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


def sync_permission_catalog(session: Session) -> PermissionSyncResult:
    """Sincroniza permissões por ``codigo`` com upsert idempotente.

    - Cria o registro quando ``codigo`` não existe.
    - Atualiza somente registros gerenciados pelo sistema.
    - Atualiza somente campos gerenciados pelo catálogo (atualmente ``nome``).
    - Não remove registros extras já existentes no banco.
    - Alterações de ``codigo`` só são aceitas via alias explícito em ``CODE_ALIASES``.
    """

    _validate_catalog_rules()

    created = 0
    updated = 0
    unchanged = 0

    _ensure_no_implicit_code_changes(session)

    alias_to_canonical = CODE_ALIASES.copy()
    aliases_by_canonical: dict[str, set[str]] = {}
    for alias_code, canonical_code in alias_to_canonical.items():
        aliases_by_canonical.setdefault(canonical_code, set()).add(alias_code)

    for item in CATALOG:
        existing = session.query(Funcao).filter_by(codigo=item.codigo).one_or_none()

        if existing is None:
            existing = _resolve_alias_candidate(session, item.codigo, aliases_by_canonical.get(item.codigo, set()))

        if existing is None:
            session.add(Funcao(codigo=item.codigo, nome=item.nome, managed_by_system=True))
            created += 1
            continue

        changed = False
        if not existing.managed_by_system:
            existing.managed_by_system = True
            changed = True

        if existing.codigo != item.codigo:
            existing.codigo = item.codigo
            changed = True

        if existing.nome != item.nome:
            existing.nome = item.nome
            changed = True

        if changed:
            updated += 1
        else:
            unchanged += 1

    result = PermissionSyncResult(created=created, updated=updated, unchanged=unchanged)
    logger.info(
        "permission_catalog_sync",
        extra={
            "event": "permission_catalog_sync",
            "created_count": result.created,
            "updated_count": result.updated,
            "unchanged_count": result.unchanged,
            "catalog_size": len(CATALOG),
        },
    )
    return result


def _resolve_alias_candidate(session: Session, canonical_code: str, aliases: set[str]) -> Funcao | None:
    if not aliases:
        return None

    for alias_code in aliases:
        alias_row = session.query(Funcao).filter_by(codigo=alias_code, managed_by_system=True).one_or_none()
        if alias_row is not None:
            return alias_row

    return None


def _validate_catalog_rules() -> None:
    for alias_code, canonical_code in CODE_ALIASES.items():
        if canonical_code not in CATALOG_BY_CODE:
            raise RuntimeError(
                f"Alias '{alias_code}' aponta para código canônico inexistente '{canonical_code}'."
            )


def _ensure_no_implicit_code_changes(session: Session) -> None:
    allowed_codes = set(CATALOG_BY_CODE) | set(CODE_ALIASES) | set(DEPRECATED_CODES)
    unmanaged_customized = (
        session.query(Funcao)
        .filter(Funcao.managed_by_system.is_(True), Funcao.codigo.notin_(allowed_codes))
        .all()
    )

    if unmanaged_customized:
        invalid_codes = ", ".join(sorted(funcao.codigo for funcao in unmanaged_customized))
        raise RuntimeError(
            "Foram encontrados códigos gerenciados pelo sistema sem regra explícita de lifecycle "
            f"(alias/deprecated): {invalid_codes}"
        )


def sync_permission_catalog_with_lock(session: Session) -> PermissionSyncResult | None:
    """Executa sincronização sob lock advisory quando disponível.

    Retorna ``None`` quando não for possível obter lock (outra instância já está sincronizando).
    """

    bind = session.get_bind()
    if bind is None:
        return sync_permission_catalog(session)

    dialect = bind.dialect.name
    if dialect != "postgresql":
        return sync_permission_catalog(session)

    lock_key = 918273645
    lock_acquired = session.execute(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": lock_key},
    ).scalar()

    if not lock_acquired:
        logger.info(
            "permission_catalog_sync_skipped",
            extra={"event": "permission_catalog_sync_skipped", "reason": "lock_not_acquired"},
        )
        return None

    try:
        return sync_permission_catalog(session)
    finally:
        session.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": lock_key},
        )
