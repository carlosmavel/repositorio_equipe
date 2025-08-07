import pytest
from app import app, db
from core.models import Notification, User, Instituicao, Estabelecimento, Setor, Celula

@pytest.fixture
def client_with_notification(app_ctx):
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
        notif = Notification(user_id=user.id, message='N', url='#')
        db.session.add(notif)
        db.session.commit()
        with app_ctx.test_client() as client:
            client.user = user
            client.notification = notif
            yield client


def login(client):
    with client.session_transaction() as sess:
        sess['user_id'] = client.user.id
        sess['username'] = client.user.username


def test_mark_notification_read(client_with_notification):
    client = client_with_notification
    login(client)
    nid = client.notification.id
    resp = client.post(f'/api/notifications/{nid}/read')
    assert resp.status_code == 200
    with app.app_context():
        n = Notification.query.get(nid)
        assert n.lido is True


def test_mark_notification_read_requires_login(client_with_notification):
    client = client_with_notification
    nid = client.notification.id
    resp = client.post(f'/api/notifications/{nid}/read')
    assert resp.status_code == 401
