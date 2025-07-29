import pytest


from app import app, db
from models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User, Article, ArticleStatus
from enums import Permissao

@pytest.fixture
def client(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Setor', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
        with app_ctx.test_client() as client:
            client.base_ids = ids
            yield client
        
        

def login_user(client, perms=None):
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
        user = User(username='u', email='u@test', estabelecimento_id=ids['est'], setor_id=ids['setor'], celula_id=ids['cel'])
        user.set_password('x')
        for f in funcoes:
            user.permissoes_personalizadas.append(f)
        db.session.add(user)
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_novo_artigo_requires_permission(client):
    login_user(client, [])
    resp = client.get('/novo-artigo')
    assert resp.status_code == 302
    assert '/meus-artigos' in resp.headers['Location']

    login_user(client, ['artigo_criar'])
    resp = client.get('/novo-artigo')
    assert resp.status_code == 200

def test_aprovacao_requires_permission(client):
    login_user(client, [])
    resp = client.get('/aprovacao')
    assert resp.status_code == 302

    login_user(client, [Permissao.ARTIGO_APROVAR_CELULA])
    resp = client.get('/aprovacao')
    assert resp.status_code == 200
