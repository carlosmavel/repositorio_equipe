import pytest


from app import app, db
from core.models import User, Instituicao, Estabelecimento, Setor, Celula
from core.utils import generate_token

@pytest.fixture
def client(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(codigo='INST001', nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab', instituicao=inst)
        setor = Setor(nome='Setor1', estabelecimento=est)
        cel = Celula(nome='Cel1', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.flush()
        u = User(
            username='temp',
            email='temp@example.com',
            estabelecimento=est,
            setor=setor,
            celula=cel,
        )
        u.set_password('OldPass1!')
        db.session.add(u)
        db.session.commit()
        with app_ctx.test_client() as client:
            yield client
        
        

def test_reset_password_token(client):
    with app.app_context():
        user = User.query.filter_by(username='temp').first()
        token = generate_token(user.id, 'reset')
    response = client.post(f'/reset-senha/{token}', data={
        'nova_senha': 'NovaPass1!',
        'confirmar_nova_senha': 'NovaPass1!'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='temp').first()
        assert user.check_password('NovaPass1!')
