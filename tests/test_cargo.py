import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Cargo, Instituicao, Estabelecimento, Setor, Celula, Funcao, User

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
        base_ids = {'setor': setor.id, 'cel': cel.id, 'admin': admin.id}
        with app.test_client() as client:
            client.base_ids = base_ids
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = client.base_ids['admin']


def test_create_cargo(client):
    login_admin(client)
    ids = client.base_ids
    response = client.post('/admin/cargos', data={
        'nome': 'Analista',
        'descricao': 'Analisa as coisas',
        'nivel_hierarquico': '3',
        'ativo_check': 'on',
        'setor_ids': [str(ids['setor'])],
        'celula_ids': [str(ids['cel'])]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cargo = Cargo.query.filter_by(nome='Analista').first()
        assert cargo is not None
        assert cargo.descricao == 'Analisa as coisas'
        assert cargo.nivel_hierarquico == 3
        assert cargo.ativo is True
        assert cargo.default_setores.filter_by(id=ids['setor']).count() == 1
        assert cargo.default_celulas.filter_by(id=ids['cel']).count() == 1
