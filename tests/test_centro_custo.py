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
        est = Estabelecimento(codigo='EST1', nome_fantasia='Estab 1')
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
    with app.app_context():
        est_id = Estabelecimento.query.first().id
    response = client.post('/admin/centros_custo', data={
        'codigo': 'CC01',
        'nome': 'Centro 1',
        'estabelecimento_id': est_id,
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cc = CentroDeCusto.query.filter_by(codigo='CC01').first()
        assert cc is not None
        assert cc.estabelecimento_id == est_id
        assert cc.nome == 'Centro 1'
