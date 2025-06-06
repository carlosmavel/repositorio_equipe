import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Cargo

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


def test_create_cargo(client):
    login_admin(client)
    response = client.post('/admin/cargos', data={
        'nome': 'Analista',
        'descricao': 'Analisa as coisas',
        'nivel_hierarquico': '3',
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cargo = Cargo.query.filter_by(nome='Analista').first()
        assert cargo is not None
        assert cargo.descricao == 'Analisa as coisas'
        assert cargo.nivel_hierarquico == 3
        assert cargo.ativo is True
