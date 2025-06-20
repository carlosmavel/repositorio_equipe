import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Instituicao, Setor, Estabelecimento, Celula, User, Funcao

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
        db.session.commit()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

def login_admin(client):
    with app.app_context():
        est = Estabelecimento.query.first()
        setor = Setor(nome='Adm', estabelecimento=est)
        cel = Celula(nome='adm', estabelecimento=est, setor=setor)
        func = Funcao(codigo='admin', nome='Admin')
        user = User(username='adm', email='a@a', estabelecimento=est, setor=setor, celula=cel)
        user.set_password('x')
        user.permissoes_personalizadas.append(func)
        db.session.add_all([setor, cel, func, user])
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid

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
