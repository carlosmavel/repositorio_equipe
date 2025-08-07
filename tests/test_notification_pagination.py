import pytest
from app import app, db
from core.models import Notification, User, Instituicao, Estabelecimento, Setor, Celula

@pytest.fixture
def client_with_notifications(app_ctx):
    with app.app_context():
        inst = Instituicao(nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S1', estabelecimento=est)
        cel = Celula(nome='C1', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.flush()
        user = User(username='u', email='u@test', password_hash='x',
                    estabelecimento=est, setor=setor, celula=cel)
        db.session.add(user)
        db.session.flush()
        for i in range(25):
            n = Notification(user_id=user.id, message=f'N{i}', url='#')
            db.session.add(n)
        db.session.commit()
        with app_ctx.test_client() as client:
            client.user = user
            yield client

def login(client):
    with client.session_transaction() as sess:
        sess['user_id'] = client.user.id
        sess['username'] = client.user.username

def test_api_requires_login(client_with_notifications):
    client = client_with_notifications
    resp = client.get('/api/notifications')
    assert resp.status_code == 401

def test_notifications_pagination(client_with_notifications):
    client = client_with_notifications
    login(client)
    resp = client.get('/api/notifications?offset=0&limit=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 10
    resp2 = client.get('/api/notifications?offset=10&limit=10')
    data2 = resp2.get_json()
    assert len(data2) == 10
    resp3 = client.get('/api/notifications?offset=20&limit=10')
    data3 = resp3.get_json()
    assert len(data3) == 5
