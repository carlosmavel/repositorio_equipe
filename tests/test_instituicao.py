import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Instituicao

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


def test_create_instituicao(client):
    login_admin(client)
    response = client.post('/admin/instituicoes', data={
        'nome': 'Inst 1',
        'descricao': 'Descricao',
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        inst = Instituicao.query.filter_by(nome='Inst 1').first()
        assert inst is not None
        assert inst.descricao == 'Descricao'
        assert inst.ativo is True
