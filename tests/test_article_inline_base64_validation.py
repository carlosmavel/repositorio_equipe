from app import db
from core.enums import ArticleStatus, ArticleVisibility, Permissao
from core.models import (
    Article,
    Celula,
    Estabelecimento,
    Funcao,
    Instituicao,
    Setor,
    User,
)


FRIENDLY_MESSAGE = "A imagem colada no texto é muito grande"


def _add_permission(user, code):
    if isinstance(code, Permissao):
        code = code.value
    funcao = Funcao.query.filter_by(codigo=code).first()
    if not funcao:
        funcao = Funcao(codigo=code, nome=code)
        db.session.add(funcao)
        db.session.flush()
    user.permissoes_personalizadas.append(funcao)


def _create_author(username="autor_inline_base64", permissions=("artigo_criar",)):
    inst = Instituicao(codigo=f"I-{username[:8]}", nome="Instituição Inline")
    est = Estabelecimento(codigo=f"E-{username[:8]}", nome_fantasia="Est Inline", instituicao=inst)
    setor = Setor(nome=f"Setor {username}", estabelecimento=est)
    celula = Celula(nome=f"Célula {username}", estabelecimento=est, setor=setor)
    db.session.add_all([inst, est, setor, celula])
    db.session.flush()

    user = User(
        username=username,
        email=f"{username}@example.test",
        password_hash="x",
        estabelecimento=est,
        setor=setor,
        celula=celula,
    )
    db.session.add(user)
    db.session.flush()
    for permission in permissions:
        _add_permission(user, permission)
    db.session.commit()
    return user, {"inst": inst, "est": est, "setor": setor, "celula": celula}


def _login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["username"] = user.username


def _large_inline_image_html():
    payload = "A" * 4097
    return f'<p>Conteúdo com texto suficiente.</p><img src="data:image/png;base64,{payload}" alt="colada">'


def _uploaded_editor_image_html():
    return '<p>Conteúdo com imagem enviada.</p><img src="/uploads/editor/imagem.png" alt="enviada">'


def test_criacao_recusa_html_com_base64_grande(client):
    author, _org = _create_author("autor_cria_inline")
    _login(client, author)

    response = client.post(
        "/novo-artigo",
        data={
            "titulo": "Criação com base64 grande",
            "texto": _large_inline_image_html(),
            "visibility": "celula",
            "acao": "rascunho",
        },
    )

    assert response.status_code == 200
    assert FRIENDLY_MESSAGE in response.get_data(as_text=True)
    assert Article.query.filter_by(titulo="Criação com base64 grande").count() == 0


def test_criacao_aceita_html_com_uploads_editor(client):
    author, _org = _create_author("autor_cria_upload")
    _login(client, author)

    response = client.post(
        "/novo-artigo",
        data={
            "titulo": "Criação com upload editor",
            "texto": _uploaded_editor_image_html(),
            "visibility": "celula",
            "acao": "rascunho",
        },
    )

    assert response.status_code == 302
    article = Article.query.filter_by(titulo="Criação com upload editor").one()
    assert '/uploads/editor/imagem.png' in article.texto


def test_edicao_recusa_html_com_base64_grande(client):
    author, org = _create_author("autor_edita_inline")
    article = Article(
        titulo="Artigo antes do base64",
        texto="Conteúdo original suficiente para o teste.",
        status=ArticleStatus.RASCUNHO,
        user_id=author.id,
        celula_id=org["celula"].id,
        vis_celula_id=org["celula"].id,
        setor_id=org["setor"].id,
        estabelecimento_id=org["est"].id,
        instituicao_id=org["inst"].id,
        visibility=ArticleVisibility.CELULA,
    )
    db.session.add(article)
    db.session.commit()
    article_id = article.id
    _login(client, author)

    response = client.post(
        f"/artigo/{article_id}/editar",
        data={
            "titulo": "Artigo depois do base64",
            "texto": _large_inline_image_html(),
            "visibility": "celula",
            "acao": "salvar",
        },
    )

    assert response.status_code == 200
    assert FRIENDLY_MESSAGE in response.get_data(as_text=True)
    unchanged = Article.query.get(article_id)
    assert unchanged.titulo == "Artigo antes do base64"
    assert unchanged.texto == "Conteúdo original suficiente para o teste."


def test_edicao_aceita_html_com_uploads_editor(client):
    author, org = _create_author("autor_edita_upload")
    article = Article(
        titulo="Artigo antes do upload",
        texto="Conteúdo original suficiente para editar.",
        status=ArticleStatus.RASCUNHO,
        user_id=author.id,
        celula_id=org["celula"].id,
        vis_celula_id=org["celula"].id,
        setor_id=org["setor"].id,
        estabelecimento_id=org["est"].id,
        instituicao_id=org["inst"].id,
        visibility=ArticleVisibility.CELULA,
    )
    db.session.add(article)
    db.session.commit()
    article_id = article.id
    _login(client, author)

    response = client.post(
        f"/artigo/{article_id}/editar",
        data={
            "titulo": "Artigo depois do upload",
            "texto": _uploaded_editor_image_html(),
            "visibility": "celula",
            "acao": "salvar",
        },
    )

    assert response.status_code == 302
    updated = Article.query.get(article_id)
    assert updated.titulo == "Artigo depois do upload"
    assert '/uploads/editor/imagem.png' in updated.texto


def test_visualizacao_simples_de_artigo_antigo_com_base64_continua_funcionando(client):
    author, org = _create_author("autor_visualiza_inline")
    old_html = _large_inline_image_html()
    article = Article(
        titulo="Artigo antigo com base64",
        texto=old_html,
        status=ArticleStatus.RASCUNHO,
        user_id=author.id,
        celula_id=org["celula"].id,
        vis_celula_id=org["celula"].id,
        setor_id=org["setor"].id,
        estabelecimento_id=org["est"].id,
        instituicao_id=org["inst"].id,
        visibility=ArticleVisibility.CELULA,
    )
    db.session.add(article)
    db.session.commit()
    _login(client, author)

    response = client.get(f"/artigo/{article.id}")

    assert response.status_code == 200
    assert 'data:image/png;base64,' in response.get_data(as_text=True)
