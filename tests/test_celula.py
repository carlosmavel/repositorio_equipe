import pytest


from app import app, db
from models import Instituicao, Estabelecimento, Setor, Celula, User, Funcao

@pytest.fixture
def client(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Setor 1', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.commit()
        with app_ctx.test_client() as client:
            yield client
        
        

def login_admin(client):
    with app.app_context():
        est = Estabelecimento.query.first()
        setor = Setor.query.first()
        cel = Celula(nome='admCel', estabelecimento=est, setor=setor)
        func = Funcao(codigo='admin', nome='Admin')
        user = User(username='adm', email='a@a', estabelecimento=est, setor=setor, celula=cel)
        user.set_password('x')
        user.permissoes_personalizadas.append(func)
        db.session.add_all([cel, func, user])
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


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
