import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Instituicao, Estabelecimento, Setor, Celula, Cargo, Funcao, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        inst = Instituicao(nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Setor 1', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        admin_cel = Celula(nome='AdminCel', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(admin_cel)
        db.session.flush()
        admin_func = Funcao(nome_codigo='admin')
        admin_cargo = Cargo(nome='Admin', ativo=True)
        admin_cargo.funcoes.append(admin_func)
        db.session.add_all([admin_func, admin_cargo])
        db.session.flush()
        admin = User(
            username='adm', email='adm@test.com', estabelecimento_id=est.id,
            setor_id=setor.id, celula_id=admin_cel.id, cargo=admin_cargo
        )
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


def test_create_celula(client):
    login_admin(client)
    with app.app_context():
        est_id = Estabelecimento.query.first().id
        setor_id = Setor.query.first().id
    response = client.post('/admin/celulas', data={
        'nome': 'Cel 1',
        'estabelecimento_id': est_id,
        'setor_id': setor_id,
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cel = Celula.query.filter_by(nome='Cel 1').first()
        assert cel is not None
        assert cel.estabelecimento_id == est_id
        assert cel.setor_id == setor_id
        assert cel.ativo is True


def test_update_celula(client):
    with app.app_context():
        est_id = Estabelecimento.query.first().id
        setor_id = Setor.query.first().id
        cel = Celula(nome='Orig', estabelecimento_id=est_id, setor_id=setor_id)
        db.session.add(cel)
        db.session.commit()
        cel_id = cel.id
    login_admin(client)
    response = client.post('/admin/celulas', data={
        'id_para_atualizar': cel_id,
        'nome': 'Atual',
        'estabelecimento_id': est_id,
        'setor_id': setor_id,
        'ativo_check': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cel = Celula.query.get(cel_id)
        assert cel.nome == 'Atual'
        assert cel.ativo is True


def test_toggle_celula_active(client):
    with app.app_context():
        est_id = Estabelecimento.query.first().id
        setor_id = Setor.query.first().id
        cel = Celula(nome='Temp', estabelecimento_id=est_id, setor_id=setor_id)
        db.session.add(cel)
        db.session.commit()
        cel_id = cel.id
    login_admin(client)
    response = client.post(f'/admin/celulas/toggle_ativo/{cel_id}', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cel = Celula.query.get(cel_id)
        assert cel.ativo is False
