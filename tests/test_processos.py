import pytest
from app import app, db
from core.models import (
    Processo,
    EtapaProcesso,
    CampoEtapa,
    RespostaEtapaOS,
    User,
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    Funcao,
)

@pytest.fixture
def base_app(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo='INST001', nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S1', estabelecimento=est)
        cel = Celula(nome='C1', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.flush()
        user = User(username='u', email='u@test', password_hash='x', estabelecimento=est, setor=setor, celula=cel)
        db.session.add(user)
        db.session.commit()
        with app_ctx.test_client() as c:
            c.user = user
            yield c


def login_admin(client):
    with app.app_context():
        inst = Instituicao(codigo='INST001', nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S1', estabelecimento=est)
        cel = Celula(nome='C1', estabelecimento=est, setor=setor)
        func = Funcao(codigo='admin', nome='Admin')
        user = User(username='admin', email='a@test', estabelecimento=est, setor=setor, celula=cel)
        user.set_password('x')
        user.permissoes_personalizadas.append(func)
        db.session.add_all([inst, est, setor, cel, func, user])
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid

def test_create_process_flow(base_app):
    with app.app_context():
        processo = Processo(nome='Proc', descricao='d')
        db.session.add(processo)
        db.session.flush()
        etapa = EtapaProcesso(nome='E1', ordem=1, processo=processo)
        db.session.add(etapa)
        db.session.flush()
        campo = CampoEtapa(nome='Campo', tipo='text', etapa=etapa)
        db.session.add(campo)
        db.session.flush()
        resp = RespostaEtapaOS(ordem_servico_id='os1', campo_etapa_id=campo.id, valor='v', preenchido_por=base_app.user.id)
        db.session.add(resp)
        db.session.commit()
        assert Processo.query.count() == 1
        assert etapa.processo_id == processo.id
        assert campo.etapa_id == etapa.id
        assert resp.campo_etapa_id == campo.id


def test_celulas_por_setor_endpoint(client):
    login_admin(client)
    with app.app_context():
        est = Estabelecimento.query.first()
        setor1 = Setor.query.filter_by(nome='S1').first()
        setor2 = Setor(nome='S2', estabelecimento=est)
        cel1 = Celula.query.filter_by(nome='C1').first()
        cel2 = Celula(nome='C2', estabelecimento=est, setor=setor2)
        db.session.add_all([setor2, cel2])
        db.session.commit()
        s1_id, s2_id = setor1.id, setor2.id
        c1_id, c2_id = cel1.id, cel2.id
    resp = client.get(f'/admin/setores/{s1_id}/celulas')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1 and data[0]['id'] == c1_id
    resp = client.get(f'/admin/setores/{s2_id}/celulas')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1 and data[0]['id'] == c2_id
