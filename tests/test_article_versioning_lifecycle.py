import pytest

from app import app, db
from core.enums import ArticleStatus, ArticleVisibility, Permissao
from core.models import (
    Article,
    ArticleVersion,
    Celula,
    Estabelecimento,
    Funcao,
    Instituicao,
    Setor,
    User,
)
from core.services.article_versions import create_article_version_snapshot


@pytest.fixture
def article_org(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo="I-VERS", nome="Instituição Versionamento")
        est = Estabelecimento(
            codigo="E-VERS",
            nome_fantasia="Estabelecimento Versionamento",
            instituicao=inst,
        )
        setor = Setor(nome="Setor Versionamento", estabelecimento=est)
        cel = Celula(nome="Célula Versionamento", estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.flush()
        yield {"inst": inst, "est": est, "setor": setor, "cel": cel}


def _add_permission(user, code):
    if isinstance(code, Permissao):
        code = code.value
    funcao = Funcao.query.filter_by(codigo=code).first()
    if not funcao:
        funcao = Funcao(codigo=code, nome=code)
        db.session.add(funcao)
        db.session.flush()
    user.permissoes_personalizadas.append(funcao)
    db.session.flush()
    return funcao


def _create_user(username, org, permissions=()):
    user = User(
        username=username,
        email=f"{username}@example.test",
        password_hash="x",
        estabelecimento=org["est"],
        setor=org["setor"],
        celula=org["cel"],
    )
    db.session.add(user)
    db.session.flush()
    for permission in permissions:
        _add_permission(user, permission)
    db.session.commit()
    return user


def _login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["username"] = user.username


def _create_article(author, org, **overrides):
    defaults = dict(
        titulo="Título original",
        texto="Texto original com conteúdo suficiente",
        status=ArticleStatus.RASCUNHO,
        user_id=author.id,
        celula_id=org["cel"].id,
        visibility=ArticleVisibility.CELULA,
        vis_celula_id=org["cel"].id,
        setor_id=org["setor"].id,
        estabelecimento_id=org["est"].id,
        instituicao_id=org["inst"].id,
    )
    defaults.update(overrides)
    article = Article(**defaults)
    db.session.add(article)
    db.session.flush()
    return article


def _versions(article_id):
    return ArticleVersion.query.filter_by(article_id=article_id).order_by(ArticleVersion.id).all()


def test_service_calculates_versions_and_revisions_v01_v02_v10_v11_v20(article_org):
    author = _create_user("autor_calc", article_org)
    article = _create_article(author, article_org)

    actions = ["create_initial", "edit", "approve", "edit_after_approved", "approve"]
    expected_pairs = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 0)]

    actual_pairs = []
    for action in actions:
        if action == "approve":
            article.status = ArticleStatus.APROVADO
        snapshot = create_article_version_snapshot(article, author, action)
        actual_pairs.append((snapshot.version_number, snapshot.revision_number))
        db.session.flush()

    assert actual_pairs == expected_pairs
    assert (article.current_version_number, article.current_revision_number) == (2, 0)


def test_article_creation_route_creates_initial_snapshot(app_ctx, client, article_org):
    author = _create_user("autor_create_snapshot", article_org, ["artigo_criar"])
    _login(client, author)

    response = client.post(
        "/novo-artigo",
        data={
            "titulo": "Artigo com snapshot inicial",
            "texto": "<p>Conteúdo inicial do artigo.</p>",
            "visibility": "celula",
            "acao": "rascunho",
        },
    )

    assert response.status_code == 302
    article = Article.query.filter_by(titulo="Artigo com snapshot inicial").one()
    snapshots = _versions(article.id)
    assert len(snapshots) == 1
    assert snapshots[0].change_action == "create_initial"
    assert (snapshots[0].version_number, snapshots[0].revision_number) == (0, 1)
    assert snapshots[0].titulo == article.titulo
    assert snapshots[0].texto == "<p>Conteúdo inicial do artigo.</p>"


def test_editing_title_text_and_metadata_snapshots_state_before_overwrite_and_increments_revision(article_org):
    author = _create_user("autor_edit_snapshot", article_org)
    article = _create_article(author, article_org, tipo_id=None)
    initial = create_article_version_snapshot(article, author, "create_initial")
    db.session.flush()

    pre_edit = create_article_version_snapshot(
        article,
        author,
        "edit",
        source_status_before=article.status,
        source_status_after=article.status,
    )
    article.titulo = "Título alterado"
    article.texto = "Texto alterado"
    article.visibility = ArticleVisibility.SETOR
    article.vis_celula_id = None
    article.setor_id = article_org["setor"].id
    db.session.commit()

    assert (initial.version_number, initial.revision_number) == (0, 1)
    assert (pre_edit.version_number, pre_edit.revision_number) == (0, 2)
    assert pre_edit.titulo == "Título original"
    assert pre_edit.texto == "Texto original com conteúdo suficiente"
    assert pre_edit.visibility == ArticleVisibility.CELULA.value
    assert article.titulo == "Título alterado"
    assert article.texto == "Texto alterado"
    assert article.current_revision_number == 2


def test_approval_increments_version_number_and_resets_revision(app_ctx, client, article_org):
    author = _create_user("autor_approve_snapshot", article_org)
    reviewer = _create_user(
        "reviewer_approve_snapshot",
        article_org,
        [Permissao.ARTIGO_APROVAR_CELULA],
    )
    article = _create_article(author, article_org, status=ArticleStatus.PENDENTE)
    create_article_version_snapshot(article, author, "create_initial")
    db.session.commit()
    _login(client, reviewer)

    response = client.post(
        f"/aprovacao/{article.id}",
        data={"acao": "aprovar", "comentario": "Aprovado para publicação."},
    )

    assert response.status_code == 302
    article = Article.query.get(article.id)
    approve_snapshot = _versions(article.id)[-1]
    assert article.status == ArticleStatus.APROVADO
    assert (article.current_version_number, article.current_revision_number) == (1, 0)
    assert approve_snapshot.change_action == "approve"
    assert (approve_snapshot.version_number, approve_snapshot.revision_number) == (1, 0)


@pytest.mark.parametrize(
    ("route_action", "expected_action", "expected_after"),
    [
        ("ajustar", "request_adjustment", ArticleStatus.EM_AJUSTE.value),
        ("rejeitar", "reject", ArticleStatus.REJEITADO.value),
    ],
)
def test_adjustment_and_rejection_snapshots_store_source_status_before_and_after(
    app_ctx, client, article_org, route_action, expected_action, expected_after
):
    author = _create_user(f"autor_{route_action}", article_org)
    reviewer = _create_user(
        f"reviewer_{route_action}",
        article_org,
        [Permissao.ARTIGO_REVISAR_CELULA],
    )
    article = _create_article(author, article_org, status=ArticleStatus.PENDENTE)
    create_article_version_snapshot(article, author, "create_initial")
    db.session.commit()
    _login(client, reviewer)

    response = client.post(
        f"/aprovacao/{article.id}",
        data={"acao": route_action, "comentario": "Decisão com comentário."},
    )

    assert response.status_code == 302
    snapshot = _versions(article.id)[-1]
    assert snapshot.change_action == expected_action
    assert snapshot.source_status_before == ArticleStatus.PENDENTE.value
    assert snapshot.source_status_after == expected_after


def test_revision_request_snapshot_stores_source_status_before_and_after(app_ctx, client, article_org):
    author = _create_user("autor_revision_request", article_org)
    article = _create_article(author, article_org, status=ArticleStatus.APROVADO)
    create_article_version_snapshot(article, author, "create_initial")
    db.session.commit()
    _login(client, author)

    response = client.post(
        f"/solicitar_revisao/{article.id}",
        data={"comentario": "Solicito revisão deste artigo."},
    )

    assert response.status_code == 302
    snapshot = _versions(article.id)[-1]
    assert snapshot.change_action == "request_revision"
    assert snapshot.source_status_before == ArticleStatus.APROVADO.value
    assert snapshot.source_status_after == ArticleStatus.EM_REVISAO.value


def test_restore_updates_current_article_creates_restore_snapshot_and_keeps_old_snapshots_immutable(
    app_ctx, client, article_org
):
    author = _create_user("autor_restore", article_org)
    admin = _create_user("admin_restore", article_org, ["admin"])
    article = _create_article(author, article_org, status=ArticleStatus.APROVADO)
    original = create_article_version_snapshot(article, author, "create_initial")
    article.titulo = "Título atual"
    article.texto = "Texto atual"
    edited = create_article_version_snapshot(article, author, "edit_after_approved")
    db.session.commit()
    old_snapshots = {
        snap.id: (snap.titulo, snap.texto, snap.version_number, snap.revision_number)
        for snap in [original, edited]
    }
    _login(client, admin)

    response = client.post(
        f"/artigo/{article.id}/versoes/{original.id}/restaurar",
        data={"motivo": "Voltar ao conteúdo original."},
    )

    assert response.status_code == 302
    article = Article.query.get(article.id)
    snapshots = _versions(article.id)
    restore_snapshot = snapshots[-1]
    assert article.titulo == "Título original"
    assert article.texto == "Texto original com conteúdo suficiente"
    assert restore_snapshot.change_action == "restore_version"
    assert restore_snapshot.titulo == "Título original"
    assert restore_snapshot.change_reason == "Voltar ao conteúdo original."
    for snap in snapshots[:-1]:
        assert (snap.titulo, snap.texto, snap.version_number, snap.revision_number) == old_snapshots[snap.id]


def test_user_without_admin_or_restore_permission_cannot_restore(app_ctx, client, article_org):
    author = _create_user("autor_denied_restore", article_org)
    article = _create_article(author, article_org)
    original = create_article_version_snapshot(article, author, "create_initial")
    article.titulo = "Título que deve permanecer"
    article.texto = "Texto que deve permanecer"
    create_article_version_snapshot(article, author, "edit")
    db.session.commit()
    _login(client, author)

    response = client.post(
        f"/artigo/{article.id}/versoes/{original.id}/restaurar",
        data={"motivo": "Tentativa sem permissão."},
    )

    assert response.status_code == 302
    article = Article.query.get(article.id)
    snapshots = _versions(article.id)
    assert article.titulo == "Título que deve permanecer"
    assert article.texto == "Texto que deve permanecer"
    assert all(snapshot.change_action != "restore_version" for snapshot in snapshots)


def test_drastic_reduction_snapshot_records_flags_counts_and_percent(article_org):
    author = _create_user("autor_drastic_history", article_org)
    article = _create_article(author, article_org, texto="x" * 1000)
    create_article_version_snapshot(article, author, "create_initial")
    article.texto = "x" * 250

    snapshot = create_article_version_snapshot(
        article,
        author,
        "edit",
        drastic_reduction_data={
            "previous_char_count": 1000,
            "new_char_count": 250,
            "reduction_percent": 75,
            "drastic_reduction": True,
        },
    )
    db.session.commit()

    assert snapshot.drastic_reduction is True
    assert snapshot.drastic_reduction_detected is True
    assert snapshot.previous_char_count == 1000
    assert snapshot.previous_text_char_count == 1000
    assert snapshot.new_char_count == 250
    assert snapshot.reduction_percent == 75
    assert snapshot.text_reduction_percent == 75
