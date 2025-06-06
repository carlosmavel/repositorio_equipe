import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Setor

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

def test_create_setor(client):
    login_admin(client)
    response = client.post('/admin/setores', data={
        'nome': 'Financeiro',
        'descricao': 'Setor Financeiro',
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        setor = Setor.query.filter_by(nome='Financeiro').first()
        assert setor is not None
        assert setor.descricao == 'Setor Financeiro'
        assert setor.ativo is True
