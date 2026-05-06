from app import db
from core.enums import Permissao
from core.models import (
    Article,
    ArticleStatus,
    ArticleVersion,
    ArticleVisibility,
    Celula,
    Estabelecimento,
    Funcao,
    Instituicao,
    Setor,
    User,
)


RICH_ARTICLE_HTML = """<h2>Subtítulo seguro</h2>
<ul>
<li><strong>Item importante</strong></li>
</ul>
<img src="/static/icons/file-icon.png" alt="Imagem do artigo">"""

RICH_FROM_VERSION_HTML = """<h2>Histórico antigo</h2>
<ul>
<li><strong>Item antigo</strong></li>
</ul>
<img src="/static/icons/file-icon.png" alt="Imagem antiga">"""

RICH_TO_VERSION_HTML = """<h2>Histórico novo</h2>
<ul>
<li><strong>Item novo</strong></li>
</ul>
<img src="/static/icons/file-icon.png" alt="Imagem nova">"""


def _add_permission(user, code):
    funcao = Funcao.query.filter_by(codigo=code).first()
    if funcao is None:
        funcao = Funcao(codigo=code, nome=code)
        db.session.add(funcao)
        db.session.flush()
    user.permissoes_personalizadas.append(funcao)


def _create_article_with_versions():
    inst = Instituicao(codigo="HTML001", nome="Instituição HTML")
    est = Estabelecimento(codigo="HTML-EST", nome_fantasia="Est HTML", instituicao=inst)
    setor = Setor(nome="Setor HTML", estabelecimento=est)
    celula = Celula(nome="Célula HTML", estabelecimento=est, setor=setor)
    db.session.add_all([inst, est, setor, celula])
    db.session.flush()

    author = User(
        username="autor_html",
        email="autor-html@example.com",
        password_hash="x",
        estabelecimento=est,
        setor=setor,
        celula=celula,
    )
    reviewer = User(
        username="revisor_html",
        email="revisor-html@example.com",
        password_hash="x",
        estabelecimento=est,
        setor=setor,
        celula=celula,
    )
    db.session.add_all([author, reviewer])
    db.session.flush()
    _add_permission(reviewer, "admin")
    _add_permission(reviewer, Permissao.ARTIGO_APROVAR_TODAS.value)

    artigo = Article(
        titulo="Artigo com HTML seguro",
        texto=RICH_ARTICLE_HTML,
        user_id=author.id,
        celula_id=celula.id,
        vis_celula_id=celula.id,
        setor_id=setor.id,
        estabelecimento_id=est.id,
        instituicao_id=inst.id,
        visibility=ArticleVisibility.CELULA,
        status=ArticleStatus.PENDENTE,
    )
    db.session.add(artigo)
    db.session.flush()

    from_version = ArticleVersion(
        article_id=artigo.id,
        version_number=1,
        revision_number=0,
        titulo="Versão antiga com HTML seguro",
        texto=RICH_FROM_VERSION_HTML,
        status=ArticleStatus.PENDENTE.value,
        visibility=ArticleVisibility.CELULA.value,
        change_action="submit_for_approval",
        title_char_count=29,
        text_char_count=len(RICH_FROM_VERSION_HTML),
        text_word_count=4,
    )
    to_version = ArticleVersion(
        article_id=artigo.id,
        version_number=1,
        revision_number=1,
        titulo="Versão nova com HTML seguro",
        texto=RICH_TO_VERSION_HTML,
        status=ArticleStatus.APROVADO.value,
        visibility=ArticleVisibility.CELULA.value,
        change_action="approve",
        title_char_count=27,
        text_char_count=len(RICH_TO_VERSION_HTML),
        text_word_count=4,
    )
    db.session.add_all([from_version, to_version])
    db.session.commit()
    return artigo, from_version, to_version, reviewer


def _login_as(client, user):
    with client.session_transaction() as sess:
        sess["username"] = user.username
        sess["user_id"] = user.id


def _assert_rendered_without_added_breaks(response, *html_fragments):
    assert response.status_code == 200
    rendered = response.get_data(as_text=True)
    for fragment in html_fragments:
        assert fragment in rendered
    assert ".replace('\\n', '<br>')" not in rendered
    assert ".replace('\\n','<br>')" not in rendered


def test_rich_article_html_is_preserved_in_view_approval_and_history(client):
    artigo, from_version, to_version, reviewer = _create_article_with_versions()
    _login_as(client, reviewer)

    article_response = client.get(f"/artigo/{artigo.id}")
    _assert_rendered_without_added_breaks(article_response, RICH_ARTICLE_HTML)

    approval_response = client.get(f"/aprovacao/{artigo.id}")
    _assert_rendered_without_added_breaks(approval_response, RICH_ARTICLE_HTML)

    version_response = client.get(f"/artigo/{artigo.id}/versoes/{to_version.id}")
    _assert_rendered_without_added_breaks(version_response, RICH_TO_VERSION_HTML)

    compare_response = client.get(
        f"/artigo/{artigo.id}/versoes/comparar",
        query_string={"from": from_version.id, "to": to_version.id},
    )
    _assert_rendered_without_added_breaks(
        compare_response,
        RICH_FROM_VERSION_HTML,
        RICH_TO_VERSION_HTML,
    )
