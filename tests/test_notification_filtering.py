import pytest
from io import BytesIO


from app import app, db
from core.models import (
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    User,
    Funcao,
    Notification,
)
from core.enums import Permissao


def add_perm(user, code):
    if isinstance(code, Permissao):
        code = code.value
    f = Funcao.query.filter_by(codigo=code).first()
    if not f:
        f = Funcao(codigo=code, nome=code)
        db.session.add(f)
        db.session.flush()
    user.permissoes_personalizadas.append(f)
    db.session.commit()


@pytest.fixture
def client_with_users(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(codigo='INST001', nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S1', estabelecimento=est)
        cel1 = Celula(nome='C1', estabelecimento=est, setor=setor)
        cel2 = Celula(nome='C2', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel1, cel2])
        db.session.flush()
        author = User(username='auth', email='a@test', password_hash='x',
                      estabelecimento=est, setor=setor, celula=cel1)
        ap1 = User(username='ap1', email='ap1@test', password_hash='x',
                   estabelecimento=est, setor=setor, celula=cel1)
        ap2 = User(username='ap2', email='ap2@test', password_hash='x',
                   estabelecimento=est, setor=setor, celula=cel2)
        db.session.add_all([author, ap1, ap2])
        db.session.flush()
        add_perm(author, 'artigo_criar')
        add_perm(ap1, Permissao.ARTIGO_APROVAR_CELULA)
        add_perm(ap2, Permissao.ARTIGO_APROVAR_CELULA)
        db.session.commit()
        data = {'author': author, 'ap1': ap1, 'ap2': ap2}
        with app_ctx.test_client() as client:
            yield client, data
        
        


def login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = user.username


def test_notification_only_for_allowed_users(client_with_users):
    client, data = client_with_users
    login(client, data['author'])
    resp = client.post('/novo-artigo', data={
        'titulo': 'T',
        'texto': '<p>x</p>',
        'acao': 'enviar',
        'visibility': 'celula'
    })
    assert resp.status_code == 302
    n1 = Notification.query.filter_by(user_id=data['ap1'].id).count()
    n2 = Notification.query.filter_by(user_id=data['ap2'].id).count()
    assert n1 == 1
    assert n2 == 0
