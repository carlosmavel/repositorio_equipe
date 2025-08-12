import pytest

from app import app, db
from core.models import (
    OrdemServico,
    Processo,
    ProcessoEtapa,
    TipoOS,
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    User,
    Funcao,
    Formulario,
)


@pytest.fixture
def client(app_ctx):
    with app_ctx.test_client() as client:
        yield client


def login_admin(client):
    with app.app_context():
        inst = Instituicao(codigo='INST001', nome='Inst')
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
        etapa = ProcessoEtapa(nome='Etapa', ordem=1, processo=proc)
        cel = Celula.query.first()
        tipo = TipoOS(nome='Tipo', descricao='d', equipe_responsavel_id=cel.id)
        etapa.tipos_os.append(tipo)
        db.session.add_all([proc, etapa, tipo])
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


def test_os_mudar_status_bloqueia_quando_form_obrigatorio(client):
    login_admin(client)
    with app.app_context():
        proc = Processo(nome='Proc2')
        etapa = ProcessoEtapa(nome='Etapa2', ordem=1, processo=proc)
        cel = Celula.query.first()
        tipo = TipoOS(
            nome='Tipo2',
            descricao='d',
            equipe_responsavel_id=cel.id,
            obrigatorio_preenchimento=True,
        )
        etapa.tipos_os.append(tipo)
        user = User.query.filter_by(username='admin').first()
        os_obj = OrdemServico(
            titulo='OS2',
            descricao='desc',
            tipo_os=tipo,
            status='rascunho',
            criado_por_id=user.id,
        )
        db.session.add_all([proc, etapa, tipo, os_obj])
        db.session.commit()
        os_id = os_obj.id
    resp = client.post(
        f'/os/{os_id}/status',
        data={'status': 'aguardando_atendimento'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert 'Formulário obrigatório não preenchido' in resp.get_data(as_text=True)
    with app.app_context():
        assert OrdemServico.query.get(os_id).status == 'rascunho'


def test_get_formulario_vinculado(client):
    login_admin(client)
    with app.app_context():
        proc = Processo(nome='ProcF')
        etapa = ProcessoEtapa(nome='EtapaF', ordem=1, processo=proc)
        cel = Celula.query.first()
        form = Formulario(nome='Form', estrutura='[{"tipo":"text","label":"Pergunta","obrigatoria":true}]')
        db.session.add_all([proc, etapa, form])
        db.session.commit()
        tipo = TipoOS(
            nome='TipoF',
            descricao='d',
            equipe_responsavel_id=cel.id,
            formulario_vinculado_id=form.id,
            obrigatorio_preenchimento=True,
        )
        etapa.tipos_os.append(tipo)
        db.session.add(tipo)
        db.session.commit()
        tipo_id = tipo.id
    resp = client.get(f'/os/tipo/{tipo_id}/formulario')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['obrigatorio'] is True
    assert 'Pergunta' in data['html']
    assert 'required' in data['html']


def test_os_nova_lista_tipos_para_usuario_sem_cargo(client):
    login_admin(client)
    with app.app_context():
        proc = Processo(nome='ProcN')
        etapa = ProcessoEtapa(nome='EtapaN', ordem=1, processo=proc)
        cel = Celula.query.first()
        tipo = TipoOS(nome='TipoN', descricao='d', equipe_responsavel_id=cel.id)
        etapa.tipos_os.append(tipo)
        db.session.add_all([proc, etapa, tipo])
        db.session.commit()
    resp = client.get('/os/nova')
    assert resp.status_code == 200
    assert 'TipoN' in resp.get_data(as_text=True)

