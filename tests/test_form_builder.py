import pytest
from app import app, db
from models import Cargo, Instituicao, Estabelecimento, Setor, Celula, User, Formulario
from utils import user_can_access_form_builder

def setup_org(prefix):
    inst = Instituicao(nome=f'Inst_{prefix}')
    db.session.add(inst)
    db.session.flush()
    est = Estabelecimento(codigo=f'E_{prefix}', nome_fantasia='Est', instituicao_id=inst.id)
    db.session.add(est)
    db.session.flush()
    setor = Setor(nome=f'Set_{prefix}', estabelecimento_id=est.id)
    db.session.add(setor)
    db.session.flush()
    cel = Celula(nome=f'Cel_{prefix}', estabelecimento_id=est.id, setor_id=setor.id)
    db.session.add(cel)
    db.session.commit()
    return est.id, setor.id, cel.id


def create_user(username, atende=False):
    est_id, setor_id, cel_id = setup_org(username)
    cargo = Cargo(nome=f'Cargo_{username}', atende_ordem_servico=atende)
    db.session.add(cargo)
    db.session.flush()
    user = User(username=username, email=f'{username}@test', estabelecimento_id=est_id, setor_id=setor_id, celula_id=cel_id, cargo_id=cargo.id)
    user.set_password('x')
    db.session.add(user)
    db.session.commit()
    return user.id


@pytest.fixture
def client(app_ctx):
    with app_ctx.test_client() as client:
        yield client


def login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user


def test_permission_function(app_ctx):
    with app_ctx.app_context():
        user_allowed_id = create_user('u1', True)
        user_denied_id = create_user('u2', False)
        user_allowed = User.query.get(user_allowed_id)
        user_denied = User.query.get(user_denied_id)
        assert user_allowed.atende_ordem_servico is True
        assert user_denied.atende_ordem_servico is False
        assert user_can_access_form_builder(user_allowed) is True
        assert user_can_access_form_builder(user_denied) is False


def test_route_permission(client):
    with app.app_context():
        user_denied_id = create_user('deny', False)
    login(client, user_denied_id)
    resp = client.get('/ordem-servico/formularios/')
    assert resp.status_code == 302

    with app.app_context():
        user_allowed_id = create_user('allow', True)
    login(client, user_allowed_id)
    resp = client.get('/ordem-servico/formularios/')
    assert resp.status_code == 200


def test_create_formulario(client):
    with app.app_context():
        user_allowed_id = create_user('creator', True)
    login(client, user_allowed_id)
    resp = client.post('/ordem-servico/formularios/novo', data={'nome': 'Form1', 'estrutura': '{}'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Form1' in resp.data
    with app.app_context():
        assert Formulario.query.filter_by(nome='Form1').first() is not None
