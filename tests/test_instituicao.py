import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Instituicao, Cargo, Funcao, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        admin_func = Funcao(nome_codigo='admin')
        admin_cargo = Cargo(nome='Admin', ativo=True)
        admin_cargo.funcoes.append(admin_func)
        db.session.add_all([admin_func, admin_cargo])
        db.session.flush()
        admin = User(username='adm', email='adm@test.com', estabelecimento_id=None,
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


def test_update_instituicao(client):
    with app.app_context():
        inst = Instituicao(nome='Inst A', descricao='Old')
        db.session.add(inst)
        db.session.commit()
        inst_id = inst.id
    login_admin(client)
    response = client.post('/admin/instituicoes', data={
        'id_para_atualizar': inst_id,
        'nome': 'Inst B',
        'descricao': 'Nova',
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        inst = Instituicao.query.get(inst_id)
        assert inst.nome == 'Inst B'
        assert inst.descricao == 'Nova'
        assert inst.ativo is True


def test_toggle_instituicao_active(client):
    with app.app_context():
        inst = Instituicao(nome='Ativa')
        db.session.add(inst)
        db.session.commit()
        inst_id = inst.id
    login_admin(client)
    response = client.post(f'/admin/instituicoes/toggle_ativo/{inst_id}', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        inst = Instituicao.query.get(inst_id)
        assert inst.ativo is False
