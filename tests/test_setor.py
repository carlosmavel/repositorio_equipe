import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Instituicao, Setor, Estabelecimento, Cargo, Funcao, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        inst = Instituicao(nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='EST1', nome_fantasia='Estab 1', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        admin_func = Funcao(nome_codigo='admin')
        admin_cargo = Cargo(nome='Admin', ativo=True)
        admin_cargo.funcoes.append(admin_func)
        db.session.add_all([admin_func, admin_cargo])
        db.session.flush()
        admin = User(username='adm', email='adm@test.com', estabelecimento_id=est.id,
                     setor_id=None, celula_id=None, cargo=admin_cargo)
        admin.set_password('pass')
        db.session.add(admin)
        db.session.commit()
        with app.test_client() as client:
            client.admin_id = admin.id
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = client.admin_id

def test_create_setor(client):
    login_admin(client)
    with app.app_context():
        est_id = Estabelecimento.query.first().id
    response = client.post('/admin/setores', data={
        'nome': 'Financeiro',
        'descricao': 'Setor Financeiro',
        'ativo_check': 'on',
        'estabelecimento_id': est_id
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        setor = Setor.query.filter_by(nome='Financeiro').first()
        assert setor is not None
        assert setor.descricao == 'Setor Financeiro'
        assert setor.ativo is True
