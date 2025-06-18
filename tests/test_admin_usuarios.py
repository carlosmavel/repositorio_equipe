import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import User, Instituicao, Estabelecimento, Setor, Celula
from utils import DEFAULT_NEW_USER_PASSWORD

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'


def test_create_user(client):
    login_admin(client)
    response = client.post('/admin/usuarios', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'role': 'colaborador',
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'new@example.com'
        assert user.check_password(DEFAULT_NEW_USER_PASSWORD)
        assert user.ativo is True


def test_toggle_user_active(client):
    with app.app_context():
        u = User(username='temp', email='temp@test.com')
        u.set_password('Pass123!')
        db.session.add(u)
        db.session.commit()
        uid = u.id
    login_admin(client)
    response = client.post(f'/admin/usuarios/toggle_ativo/{uid}', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        u = User.query.get(uid)
        assert u.ativo is False


def test_create_user_with_celula(client):
    login_admin(client)
    with app.app_context():
        inst = Instituicao(nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Setor1', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel1', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        cel_id = cel.id
    response = client.post('/admin/usuarios', data={
        'username': 'celuser',
        'email': 'cel@example.com',
        'role': 'colaborador',
        'ativo_check': 'on',
        'celula_id': cel_id
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        usr = User.query.filter_by(username='celuser').first()
        assert usr is not None
        assert usr.celula_id == cel_id
