import pytest

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User


@pytest.fixture
def client(app_ctx):
    with app.app_context():
        inst = Instituicao(nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Set', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        with app_ctx.test_client() as client:
            client.base_ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
            yield client


def login_admin(client):
    ids = client.base_ids
    with app.app_context():
        f = Funcao.query.filter_by(codigo='admin').first()
        if not f:
            f = Funcao(codigo='admin', nome='Admin')
            db.session.add(f)
            db.session.commit()
        u = User(
            username='adm',
            email='adm@test',
            estabelecimento_id=ids['est'],
            setor_id=ids['setor'],
            celula_id=ids['cel'],
        )
        u.set_password('x')
        u.permissoes_personalizadas.append(f)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_admin_dashboard(client):
    login_admin(client)
    resp = client.get('/admin/dashboard')
    assert resp.status_code == 200
