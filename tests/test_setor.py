import pytest


from app import app, db
from core.models import Instituicao, Setor, Estabelecimento, Celula, User, Funcao

@pytest.fixture
def client(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(codigo='INST001', nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='EST1', nome_fantasia='Estab 1', instituicao_id=inst.id)
        db.session.add(est)
        db.session.commit()
        with app_ctx.test_client() as client:
            yield client
        
        

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
