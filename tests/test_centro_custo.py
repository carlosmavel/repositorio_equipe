import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Estabelecimento, CentroDeCusto

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        # Create establishment to satisfy FK
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab', razao_social='R', ativo=True)
        db.session.add(est)
        db.session.commit()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()


def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'


def test_create_centro_custo(client):
    login_admin(client)
    est = Estabelecimento.query.first()
    response = client.post('/admin/centros_custo', data={
        'codigo': 'CC1',
        'nome': 'Centro 1',
        'estabelecimento_id': est.id,
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cc = CentroDeCusto.query.filter_by(codigo='CC1').first()
        assert cc is not None
        assert cc.nome == 'Centro 1'
        assert cc.ativo is True
