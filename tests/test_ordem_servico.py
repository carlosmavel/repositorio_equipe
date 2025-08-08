import pytest

from app import app, db
from core.models import OrdemServico, Processo, Subprocesso, TipoOS, Instituicao, Estabelecimento, Setor, Celula, User, Funcao


@pytest.fixture
def client(app_ctx):
    with app_ctx.test_client() as client:
        yield client


def login_admin(client):
    with app.app_context():
        inst = Instituicao(nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S1', estabelecimento=est)
        cel = Celula(nome='C1', estabelecimento=est, setor=setor)
        func = Funcao(codigo='admin', nome='Admin')
        db.session.add_all([inst, est, setor, cel, func])
        user = User(username='admin', email='a@test', estabelecimento=est, setor=setor, celula=cel)
        user.set_password('x')
        user.permissoes_personalizadas.append(func)
        db.session.add(user)
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_crud_ordem_servico(client):
    login_admin(client)
    with app.app_context():
        proc = Processo(nome='Proc')
        sub = Subprocesso(nome='Sub', processo=proc)
        cel = Celula.query.first()
        tipo = TipoOS(nome='Tipo', descricao='d', subprocesso=sub, equipe_responsavel_id=cel.id)
        db.session.add_all([proc, sub, tipo])
        db.session.commit()
        proc_id = tipo.id
    # create
    resp = client.post('/admin/ordens_servico', data={
        'titulo': 'OS1',
        'descricao': 'desc',
        'tipo_os_id': proc_id,
        'status': 'rascunho',
        'prioridade': 'baixa'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        os_obj = OrdemServico.query.filter_by(titulo='OS1').first()
        assert os_obj is not None
        os_id = os_obj.id
        assert os_obj.tipo_os_id == proc_id
    # update
    resp = client.post('/admin/ordens_servico', data={
        'id_para_atualizar': os_id,
        'titulo': 'OS1 edit',
        'descricao': 'd2',
        'tipo_os_id': proc_id,
        'status': 'cancelada'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        os_obj = OrdemServico.query.get(os_id)
        assert os_obj.titulo == 'OS1 edit'
        assert os_obj.tipo_os_id == proc_id
        assert os_obj.status == 'cancelada'
    # delete
    resp = client.post(f'/admin/ordens_servico/delete/{os_id}', follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert OrdemServico.query.get(os_id) is None

