import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import User, Instituicao, Estabelecimento, Setor, Celula
from utils import generate_token

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        inst = Instituicao(nome='Inst')
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
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

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
