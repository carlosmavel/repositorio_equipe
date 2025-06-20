import os
import pytest

# Configure environment variables before importing the app
os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Estabelecimento, Instituicao, Setor, Celula, Cargo, Funcao, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        inst = Instituicao(nome='Inst 1')
        db.session.add(inst)
        db.session.flush()

        admin_est = Estabelecimento(codigo='ADM', nome_fantasia='AdminEst', instituicao_id=inst.id)
        db.session.add(admin_est)
        db.session.flush()
        admin_setor = Setor(nome='SetAdm', estabelecimento_id=admin_est.id)
        db.session.add(admin_setor)
        db.session.flush()
        admin_cel = Celula(nome='CelAdm', estabelecimento_id=admin_est.id, setor_id=admin_setor.id)
        db.session.add(admin_cel)
        db.session.flush()

        admin_func = Funcao(nome_codigo='admin')
        admin_cargo = Cargo(nome='Admin', ativo=True)
        admin_cargo.funcoes.append(admin_func)
        db.session.add_all([admin_func, admin_cargo])
        db.session.flush()

        admin = User(
            username='adm', email='adm@test.com', estabelecimento_id=admin_est.id,
            setor_id=admin_setor.id, celula_id=admin_cel.id, cargo=admin_cargo
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


def test_create_estabelecimento_saves_address_and_phone(client):
    login_admin(client)
    with app.app_context():
        inst_id = Instituicao.query.first().id
    response = client.post('/admin/estabelecimentos', data={
        'codigo': 'TST1',
        'nome_fantasia': 'Teste',
        'razao_social': 'Empresa Teste',
        'cnpj': '12.345.678/0001-90',
        'inscricao_estadual': '123456',
        'inscricao_municipal': '654321',
        'tipo_estabelecimento': 'Matriz',
        'cep': '12345-678',
        'logradouro': 'Rua Teste',
        'numero': '100',
        'complemento': 'Sala 1',
        'bairro': 'Centro',
        'cidade': 'Teste',
        'estado': 'TS',
        'pais': 'Brasil',
        'telefone_principal': '11-1111-1111',
        'telefone_secundario': '22-2222-2222',
        'email_contato': 'contato@teste.com',
        'data_abertura': '2024-01-01',
        'observacoes': 'Obs',
        'ativo_check': 'on',
        'instituicao_id': inst_id
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        est = Estabelecimento.query.filter_by(codigo='TST1').first()
        assert est is not None
        assert est.logradouro == 'Rua Teste'
        assert est.telefone_principal == '11-1111-1111'
        assert est.telefone_secundario == '22-2222-2222'
        assert est.inscricao_estadual == '123456'
        assert est.inscricao_municipal == '654321'
        assert est.pais == 'Brasil'
