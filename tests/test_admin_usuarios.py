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
        admin_func = Funcao(nome_codigo='admin')
        admin_cargo = Cargo(nome='Admin', ativo=True)
        admin_cargo.funcoes.append(admin_func)
        db.session.add_all([admin_func, admin_cargo])
        db.session.flush()
        admin = User(username='adm', email='adm@test.com', estabelecimento_id=est.id,
                     setor_id=setor.id, celula_id=cel.id, cargo=admin_cargo)
        admin.set_password('pass')
        db.session.add(admin)
        db.session.commit()
        base_ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id, 'admin': admin.id}
        with app.test_client() as client:
            client.base_ids = base_ids
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = client.base_ids['admin']


def test_create_user(client):
    login_admin(client)
    ids = client.base_ids
    response = client.post('/admin/usuarios', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'role': 'colaborador',
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
        'role': 'colaborador',
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
        'role': 'colaborador',
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


def test_user_permissions_inherit_and_customize(client):
    login_admin(client)
    ids = client.base_ids
    with app.app_context():
        func_edit = Funcao(nome_codigo='editor')
        cargo = Cargo(nome='EditorCargo', ativo=True)
        cargo.funcoes.append(func_edit)
        db.session.add_all([func_edit, cargo])
        db.session.commit()
        cargo_id = cargo.id
        func_id = func_edit.id
    # Create user without selecting the permission (should remove)
    response = client.post('/admin/usuarios', data={
        'username': 'noedit',
        'email': 'noedit@example.com',
        'role': 'colaborador',
        'ativo_check': 'on',
        'cargo_id': cargo_id,
        'estabelecimento_id': ids['est'],
        'setor_ids': [str(ids['setor'])],
        'celula_ids': [str(ids['cel'])]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        usr = User.query.filter_by(username='noedit').first()
        assert 'editor' not in usr.get_permissoes()
    # Create user adding admin permission extra
    response = client.post('/admin/usuarios', data={
        'username': 'extraadmin',
        'email': 'extraadmin@example.com',
        'role': 'colaborador',
        'ativo_check': 'on',
        'cargo_id': cargo_id,
        'funcao_ids': [str(func_id), str(Funcao.query.filter_by(nome_codigo='admin').first().id)],
        'estabelecimento_id': ids['est'],
        'setor_ids': [str(ids['setor'])],
        'celula_ids': [str(ids['cel'])]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        usr = User.query.filter_by(username='extraadmin').first()
        perms = usr.get_permissoes()
        assert 'editor' in perms
        assert 'admin' in perms

