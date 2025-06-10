import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Estabelecimento, CentroDeCusto, Celula

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab')
        db.session.add(est)
        db.session.flush()
        cc = CentroDeCusto(codigo='CC1', nome='CC 1', estabelecimento_id=est.id)
        db.session.add(cc)
        db.session.commit()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'


def test_create_celula(client):
    login_admin(client)
    with app.app_context():
        est_id = Estabelecimento.query.first().id
        cc_id = CentroDeCusto.query.first().id
    response = client.post('/admin/celulas', data={
        'nome': 'Cel 1',
        'estabelecimento_id': est_id,
        'centro_custo_id': cc_id,
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cel = Celula.query.filter_by(nome='Cel 1').first()
        assert cel is not None
        assert cel.estabelecimento_id == est_id
        assert cel.centro_custo_id == cc_id
        assert cel.ativo is True
