import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import User, Instituicao, Estabelecimento, Setor, Celula, Cargo, Funcao
from utils import DEFAULT_NEW_USER_PASSWORD

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
        setor = Setor(nome='Setor1', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel1', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        base_ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
        with app.test_client() as client:
            client.base_ids = base_ids
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    ids = client.base_ids
    with app.app_context():
        f = Funcao.query.filter_by(codigo='admin').first()
        if not f:
            f = Funcao(codigo='admin', nome='Admin')
            db.session.add(f)
            db.session.commit()
        u = User(
            username='adm',
            email='adm@test',
            estabelecimento_id=ids['est'],
            setor_id=ids['setor'],
            celula_id=ids['cel'],
        )
        u.set_password('x')
        u.permissoes_personalizadas.append(f)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_create_user(client):
    login_admin(client)
    ids = client.base_ids
    response = client.post('/admin/usuarios', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'ativo_check': 'on',
        'estabelecimento_id': ids['est'],
        'setor_ids': [str(ids['setor'])],
        'celula_ids': [str(ids['cel'])]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'new@example.com'
        assert user.check_password(DEFAULT_NEW_USER_PASSWORD)
        assert user.ativo is True
        assert user.celula_id == ids['cel']
        assert user.setor_id == ids['setor']
        assert user.extra_celulas.filter_by(id=ids['cel']).count() == 1


def test_toggle_user_active(client):
    ids = client.base_ids
    with app.app_context():
        u = User(
            username='temp',
            email='temp@test.com',
            estabelecimento_id=ids['est'],
            setor_id=ids['setor'],
            celula_id=ids['cel']
        )
        u.set_password('Pass123!')
        u.extra_setores.append(Setor.query.get(ids['setor']))
        u.extra_celulas.append(Celula.query.get(ids['cel']))
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
    ids = client.base_ids
    with app.app_context():
        est = Estabelecimento.query.get(ids['est'])
        setor = Setor.query.get(ids['setor'])
        cel_id = ids['cel']
    response = client.post('/admin/usuarios', data={
        'username': 'celuser',
        'email': 'cel@example.com',
        'ativo_check': 'on',
        'estabelecimento_id': est.id,
        'setor_ids': [str(setor.id)],
        'celula_ids': [str(cel_id)]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        usr = User.query.filter_by(username='celuser').first()
        assert usr is not None
        assert usr.celula_id == cel_id
        assert usr.extra_celulas.filter_by(id=cel_id).count() == 1


def test_user_defaults_from_cargo(client):
    login_admin(client)
    ids = client.base_ids
    with app.app_context():
        cargo = Cargo(
            nome='Gestor TI', ativo=True
        )
        cargo.default_setores.append(Setor.query.get(ids['setor']))
        cargo.default_celulas.append(Celula.query.get(ids['cel']))
        db.session.add(cargo)
        db.session.commit()
        cargo_id = cargo.id
    response = client.post('/admin/usuarios', data={
        'username': 'gestor',
        'email': 'gestor@example.com',
        'ativo_check': 'on',
        'cargo_id': cargo_id
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        usr = User.query.filter_by(username='gestor').first()
        assert usr is not None
        assert usr.cargo_id == cargo_id
        assert usr.setor_id == ids['setor']
        assert usr.celula_id == ids['cel']


def test_get_permissoes_combinadas(client):
    login_admin(client)
    ids = client.base_ids
    with app.app_context():
        func1 = Funcao(codigo='A', nome='Perm A')
        func2 = Funcao(codigo='B', nome='Perm B')
        db.session.add_all([func1, func2])
        cargo = Cargo(nome='Tester', ativo=True)
        cargo.permissoes.append(func1)
        db.session.add_all([cargo])
        db.session.commit()
        cargo_id = cargo.id
        user = User(
            username='permuser',
            email='perm@example.com',
            estabelecimento_id=ids['est'],
            setor_id=ids['setor'],
            celula_id=ids['cel'],
            cargo_id=cargo_id,
        )
        user.set_password('x')
        user.permissoes_personalizadas.append(func2)
        db.session.add(user)
        db.session.commit()
        result = {f.codigo for f in user.get_permissoes()}
        assert result == {'A', 'B'}


def test_create_user_with_custom_permissions(client):
    login_admin(client)
    ids = client.base_ids
    with app.app_context():
        f1 = Funcao(codigo='X', nome='Perm X')
        f2 = Funcao(codigo='Y', nome='Perm Y')
        cargo = Cargo(nome='Dev', ativo=True)
        cargo.permissoes.append(f1)
        db.session.add_all([f1, f2, cargo])
        db.session.commit()
        cargo_id = cargo.id
        f2_id = f2.id
    response = client.post('/admin/usuarios', data={
        'username': 'uperm',
        'email': 'uperm@example.com',
        'ativo_check': 'on',
        'cargo_id': cargo_id,
        'estabelecimento_id': ids['est'],
        'setor_ids': [str(ids['setor'])],
        'celula_ids': [str(ids['cel'])],
        'funcao_ids': [str(f2_id)]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        u = User.query.filter_by(username='uperm').first()
        assert {f.codigo for f in u.get_permissoes()} == {'X', 'Y'}
        assert {f.id for f in u.permissoes_personalizadas} == {f2_id}
