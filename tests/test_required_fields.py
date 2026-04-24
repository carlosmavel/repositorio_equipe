import pytest
from io import BytesIO
from app import app, db
from core.models import (
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    Funcao,
    User,
    Article,
)
from core.enums import Permissao, ArticleStatus


@pytest.fixture
def client(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo='I1', nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S', estabelecimento=est)
        cel = Celula(nome='C', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.commit()
        ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
        with app_ctx.test_client() as client:
            client.base_ids = ids
            yield client


def _login_user(client, perms=None):
    perms = perms or []
    ids = client.base_ids
    with app.app_context():
        db.session.query(User).delete()
        db.session.commit()
        funcoes = []
        for code in perms:
            if isinstance(code, Permissao):
                code = code.value
            f = Funcao.query.filter_by(codigo=code).first()
            if not f:
                f = Funcao(codigo=code, nome=code)
                db.session.add(f)
                db.session.flush()
            funcoes.append(f)
        user = User(
            username='u', email='u@test', password_hash='x',
            estabelecimento_id=ids['est'], setor_id=ids['setor'], celula_id=ids['cel']
        )
        for f in funcoes:
            user.permissoes_personalizadas.append(f)
        db.session.add(user)
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['username'] = 'u'
    return uid


@pytest.mark.parametrize("comentario", [" ", "<p><br></p>"])
def test_approve_requires_comment(client, comentario):
    _login_user(client, [Permissao.ARTIGO_APROVAR_CELULA])
    with app.app_context():
        inst = Instituicao.query.first()
        est = Estabelecimento.query.first()
        setor = Setor.query.first()
        cel = Celula.query.first()
        author = User(username='a', email='a@test', password_hash='x',
                      estabelecimento=est, setor=setor, celula=cel)
        db.session.add(author)
        db.session.commit()
        art = Article(
            titulo='T', texto='C', status=ArticleStatus.PENDENTE,
            user_id=author.id, celula_id=cel.id, setor_id=setor.id,
            estabelecimento_id=est.id, instituicao_id=inst.id
        )
        db.session.add(art)
        db.session.commit()
        aid = art.id
    client.post(f'/aprovacao/{aid}', data={'acao': 'aprovar', 'comentario': comentario}, follow_redirects=True)
    with app.app_context():
        art = Article.query.get(aid)
        assert art.status == ArticleStatus.PENDENTE
        assert art.comments.count() == 0


def test_novo_artigo_requires_fields(client):
    _login_user(client, ['artigo_criar'])
    client.post('/novo-artigo', data={'titulo': '', 'texto': '', 'visibility': 'celula', 'acao': 'enviar'}, follow_redirects=True)
    with app.app_context():
        assert Article.query.count() == 0




def test_novo_artigo_accepts_attachment_without_text(client):
    _login_user(client, ['artigo_criar'])
    client.post('/novo-artigo', data={
        'titulo': 'OCR sem texto',
        'texto': '',
        'visibility': 'celula',
        'acao': 'enviar',
        'files': (BytesIO(b'conteudo teste ocr'), 'ocr.txt'),
    }, content_type='multipart/form-data', follow_redirects=True)

    with app.app_context():
        artigo = Article.query.filter_by(titulo='OCR sem texto').first()
        assert artigo is not None
        assert artigo.status == ArticleStatus.PENDENTE

def test_editar_artigo_requires_fields(client):
    uid = _login_user(client, ['artigo_criar', Permissao.ARTIGO_EDITAR_CELULA])
    with app.app_context():
        user = User.query.get(uid)
        inst = Instituicao.query.first()
        art = Article(
            titulo='T', texto='C', status=ArticleStatus.RASCUNHO,
            user_id=uid, celula_id=user.celula_id, setor_id=user.setor_id,
            estabelecimento_id=user.estabelecimento_id, instituicao_id=inst.id
        )
        db.session.add(art)
        db.session.commit()
        aid = art.id
    client.post(f'/artigo/{aid}/editar', data={'titulo': '', 'texto': '', 'acao': 'salvar', 'visibility': 'celula'}, follow_redirects=True)
    with app.app_context():
        art = Article.query.get(aid)
        assert art.titulo == 'T'
        assert art.texto == 'C'


def test_editar_artigo_buttons_visible_for_editor_with_permission(client):
    author_id = _login_user(client, ['artigo_criar'])
    with app.app_context():
        author = User.query.get(author_id)
        inst = Instituicao.query.first()
        art = Article(
            titulo='Rascunho compartilhado', texto='Conteúdo', status=ArticleStatus.RASCUNHO,
            user_id=author_id, celula_id=author.celula_id, setor_id=author.setor_id,
            estabelecimento_id=author.estabelecimento_id, instituicao_id=inst.id
        )
        db.session.add(art)
        db.session.commit()
        aid = art.id

    _login_user(client, [Permissao.ARTIGO_EDITAR_CELULA])
    response = client.get(f'/artigo/{aid}/editar')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'name="acao" value="salvar"' in html
    assert 'name="acao" value="enviar"' in html

