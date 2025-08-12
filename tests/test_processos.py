import pytest
from app import app, db
from core.models import Processo, EtapaProcesso, CampoEtapa, RespostaEtapaOS, User, Instituicao, Estabelecimento, Setor, Celula

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
