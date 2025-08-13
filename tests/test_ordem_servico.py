import re
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
    Equipamento,
    Sistema,
    Cargo,
)
from core.utils import gerar_codigo_os
from core.enums import OSStatus
from blueprints.ordens_servico import _usuario_pode_acessar_os


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
        equip = Equipamento(nome='Eq1')
        db.session.add_all([proc, etapa, tipo, equip])
        db.session.commit()
        proc_id = tipo.id
        equip_id = equip.id
    # create
    resp = client.post('/admin/ordens_servico', data={
        'titulo': 'OS1',
        'descricao': 'desc',
        'tipo_os_id': proc_id,
        'equipamento_id': equip_id,
        'status': 'rascunho',
        'prioridade': 'baixa'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        os_obj = OrdemServico.query.filter_by(titulo='OS1').first()
        assert os_obj is not None
        os_id = os_obj.id
        os_codigo = os_obj.codigo
        assert re.match(r'^[A-Z]\d{6}$', os_codigo)
        assert os_obj.tipo_os_id == proc_id
        assert os_obj.equipamento_id == equip_id
    # update
    resp = client.post('/admin/ordens_servico', data={
        'id_para_atualizar': os_id,
        'titulo': 'OS1 edit',
        'descricao': 'd2',
        'tipo_os_id': proc_id,
        'equipamento_id': equip_id,
        'status': 'cancelada'
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        os_obj = OrdemServico.query.filter_by(codigo=os_codigo).first()
        assert os_obj.titulo == 'OS1 edit'
        assert os_obj.tipo_os_id == proc_id
        assert os_obj.status == 'cancelada'
    # delete
    resp = client.post(f'/admin/ordens_servico/delete/{os_id}', follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert OrdemServico.query.filter_by(codigo=os_codigo).first() is None


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
            codigo=gerar_codigo_os(),
            titulo='OS2',
            descricao='desc',
            tipo_os=tipo,
            status='rascunho',
            criado_por_id=user.id,
        )
        db.session.add_all([proc, etapa, tipo, os_obj])
        db.session.commit()
        os_id = os_obj.id
        os_codigo = os_obj.codigo
    resp = client.post(
        f'/os/{os_id}/status',
        data={'status': 'aguardando_atendimento'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert 'Formulário obrigatório não preenchido' in resp.get_data(as_text=True)
    with app.app_context():
        assert OrdemServico.query.filter_by(codigo=os_codigo).first().status == 'rascunho'


def test_validacao_condicional_campos(client):
    login_admin(client)
    with app.app_context():
        proc = Processo(nome='ProcV')
        etapa = ProcessoEtapa(nome='EtapaV', ordem=1, processo=proc)
        cel = Celula.query.first()
        tipo_sis = TipoOS(nome='Suporte ao Sistema', descricao='d', equipe_responsavel_id=cel.id)
        tipo_eq = TipoOS(nome='Manutenção de Equipamento', descricao='d', equipe_responsavel_id=cel.id)
        etapa.tipos_os.extend([tipo_sis, tipo_eq])
        equip = Equipamento(nome='EqX')
        sist = Sistema(nome='SisX')
        db.session.add_all([proc, etapa, tipo_sis, tipo_eq, equip, sist])
        db.session.commit()
        tipo_sis_id = tipo_sis.id
        tipo_eq_id = tipo_eq.id
        equip_id = equip.id
        sist_id = sist.id
    resp = client.post('/admin/ordens_servico', data={
        'titulo': 'OS S',
        'descricao': 'd',
        'tipo_os_id': tipo_sis_id,
        'status': 'rascunho'
    }, follow_redirects=True)
    assert "O campo Sistema é obrigatório" in resp.get_data(as_text=True)
    resp = client.post('/admin/ordens_servico', data={
        'titulo': 'OS E',
        'descricao': 'd',
        'tipo_os_id': tipo_eq_id,
        'status': 'rascunho'
    }, follow_redirects=True)
    assert "O campo Equipamento é obrigatório" in resp.get_data(as_text=True)
    resp = client.post('/admin/ordens_servico', data={
        'titulo': 'OS S ok',
        'descricao': 'd',
        'tipo_os_id': tipo_sis_id,
        'sistema_id': sist_id,
        'status': 'rascunho'
    }, follow_redirects=True)
    assert resp.status_code == 200
    resp = client.post('/admin/ordens_servico', data={
        'titulo': 'OS E ok',
        'descricao': 'd',
        'tipo_os_id': tipo_eq_id,
        'equipamento_id': equip_id,
        'status': 'rascunho'
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_codigo_os_formato_unicidade_incremento(client):
    login_admin(client)
    with app.app_context():
        proc = Processo(nome='ProcC')
        etapa = ProcessoEtapa(nome='EtapaC', ordem=1, processo=proc)
        cel = Celula.query.first()
        tipo = TipoOS(nome='TipoC', descricao='d', equipe_responsavel_id=cel.id)
        etapa.tipos_os.append(tipo)
        user = User.query.filter_by(username='admin').first()
        db.session.add_all([proc, etapa, tipo])
        db.session.commit()

        codigo1 = gerar_codigo_os()
        os1 = OrdemServico(
            codigo=codigo1,
            titulo='OS A',
            descricao='d',
            tipo_os=tipo,
            status='rascunho',
            criado_por_id=user.id,
        )
        db.session.add(os1)
        db.session.commit()

        codigo2 = gerar_codigo_os()
        os2 = OrdemServico(
            codigo=codigo2,
            titulo='OS B',
            descricao='d',
            tipo_os=tipo,
            status='rascunho',
            criado_por_id=user.id,
        )
        db.session.add(os2)
        db.session.commit()

        assert re.match(r'^[A-Z]\d{6}$', codigo1)
        assert re.match(r'^[A-Z]\d{6}$', codigo2)
        assert codigo1 != codigo2
        assert codigo1[0] == codigo2[0]
        assert int(codigo2[1:]) == int(codigo1[1:]) + 1


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


def test_os_listar_filtra_por_celulas(client):
    login_admin(client)
    with app.app_context():
        est = Estabelecimento.query.first()
        setor = Setor.query.first()
        cel1 = Celula.query.first()
        cel2 = Celula(nome='C2', estabelecimento=est, setor=setor)
        db.session.add(cel2)
        admin = User.query.filter_by(username='admin').first()
        tipo1 = TipoOS(nome='T1', descricao='d', equipe_responsavel_id=cel1.id)
        tipo2 = TipoOS(nome='T2', descricao='d', equipe_responsavel_id=cel2.id)
        db.session.add_all([tipo1, tipo2])
        db.session.commit()
        os1 = OrdemServico(
            codigo=gerar_codigo_os(),
            titulo='OS A',
            descricao='d',
            tipo_os=tipo1,
            equipe_responsavel_id=cel1.id,
            status=OSStatus.AGUARDANDO_ATENDIMENTO.value,
            criado_por_id=admin.id,
        )
        db.session.add(os1)
        db.session.commit()
        os2 = OrdemServico(
            codigo=gerar_codigo_os(),
            titulo='OS B',
            descricao='d',
            tipo_os=tipo2,
            equipe_responsavel_id=cel2.id,
            status=OSStatus.AGUARDANDO_ATENDIMENTO.value,
            criado_por_id=admin.id,
        )
        db.session.add(os2)
        db.session.commit()
    resp = client.get('/os')
    data = resp.get_data(as_text=True)
    assert 'OS A' in data
    assert 'OS B' not in data


def test_os_detalhar_respeita_permissoes(client):
    login_admin(client)
    with app.app_context():
        est = Estabelecimento.query.first()
        setor = Setor.query.first()
        cel1 = Celula.query.first()
        cel2 = Celula(nome='C3', estabelecimento=est, setor=setor)
        user2 = User(username='u2', email='u2@test', estabelecimento=est, setor=setor, celula=cel2)
        user2.set_password('x')
        db.session.add_all([cel2, user2])
        db.session.commit()
        admin = User.query.filter_by(username='admin').first()
        tipo1 = TipoOS(nome='T3', descricao='d', equipe_responsavel_id=cel1.id)
        tipo2 = TipoOS(nome='T4', descricao='d', equipe_responsavel_id=cel2.id)
        db.session.add_all([tipo1, tipo2])
        db.session.commit()
        os_permitida = OrdemServico(
            codigo=gerar_codigo_os(),
            titulo='OS OK',
            descricao='d',
            tipo_os=tipo1,
            equipe_responsavel_id=cel1.id,
            status=OSStatus.AGUARDANDO_ATENDIMENTO.value,
            criado_por_id=admin.id,
        )
        db.session.add(os_permitida)
        db.session.commit()
        os_negada = OrdemServico(
            codigo=gerar_codigo_os(),
            titulo='OS NO',
            descricao='d',
            tipo_os=tipo2,
            equipe_responsavel_id=cel2.id,
            status=OSStatus.AGUARDANDO_ATENDIMENTO.value,
            criado_por_id=user2.id,
        )
        db.session.add(os_negada)
        db.session.commit()
        permitida_id = os_permitida.id
        negada_id = os_negada.id
    assert client.get(f'/os/{permitida_id}').status_code == 200
    assert client.get(f'/os/{negada_id}').status_code == 403


def test_acesso_os_celulas_por_hierarquia(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo='I1', nome='Inst1')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est1', instituicao=inst)
        setor = Setor(nome='S1', estabelecimento=est)
        cel_principal = Celula(nome='C0', estabelecimento=est, setor=setor)
        cel_sub = Celula(nome='C1', estabelecimento=est, setor=setor)
        cargo_lider = Cargo(nome='Lider', nivel_hierarquico=5, pode_atender_os=True)
        cargo_op = Cargo(nome='Operador', nivel_hierarquico=6, pode_atender_os=True)
        db.session.add_all([inst, est, setor, cel_principal, cel_sub, cargo_lider, cargo_op])
        db.session.commit()

        lider = User(
            username='lider',
            email='l@test',
            estabelecimento=est,
            setor=setor,
            celula=cel_principal,
            cargo=cargo_lider,
        )
        lider.set_password('x')
        lider.extra_celulas.extend([cel_principal, cel_sub])

        operador = User(
            username='op',
            email='o@test',
            estabelecimento=est,
            setor=setor,
            celula=cel_principal,
            cargo=cargo_op,
        )
        operador.set_password('x')
        operador.extra_celulas.extend([cel_principal, cel_sub])
        db.session.add_all([lider, operador])
        db.session.commit()

        tipo = TipoOS(nome='T', descricao='d', equipe_responsavel_id=cel_sub.id)
        db.session.add(tipo)
        db.session.commit()

        os_obj = OrdemServico(
            codigo=gerar_codigo_os(),
            titulo='OS',
            descricao='d',
            tipo_os=tipo,
            equipe_responsavel_id=cel_sub.id,
            criado_por_id=lider.id,
        )
        db.session.add(os_obj)
        db.session.commit()

        assert _usuario_pode_acessar_os(lider, os_obj) is True
        assert _usuario_pode_acessar_os(operador, os_obj) is False


def test_os_modal_endpoint(client):
    login_admin(client)
    with app.app_context():
        cel = Celula.query.first()
        proc = Processo(nome='ProcM')
        etapa = ProcessoEtapa(nome='EtapaM', ordem=1, processo=proc)
        tipo = TipoOS(nome='TipoM', descricao='d', equipe_responsavel_id=cel.id)
        etapa.tipos_os.append(tipo)
        user = User.query.filter_by(username='admin').first()
        os_obj = OrdemServico(
            codigo=gerar_codigo_os(),
            titulo='OS modal test',
            descricao='desc',
            tipo_os=tipo,
            status=OSStatus.AGUARDANDO_ATENDIMENTO.value,
            criado_por=user,
        )
        db.session.add_all([proc, etapa, tipo, os_obj])
        db.session.commit()
        codigo = os_obj.codigo
    resp = client.get(f'/os/{codigo}/modal')
    assert resp.status_code == 200
    assert 'OS modal test' in resp.get_data(as_text=True)


def test_etapas_por_processo_endpoint(client):
    login_admin(client)
    with app.app_context():
        proc1 = Processo(nome='ProcA')
        proc2 = Processo(nome='ProcB')
        e1 = ProcessoEtapa(nome='EtapaA', ordem=1, processo=proc1)
        e2 = ProcessoEtapa(nome='EtapaB', ordem=1, processo=proc2)
        db.session.add_all([proc1, proc2, e1, e2])
        db.session.commit()
        proc1_id, proc2_id = proc1.id, proc2.id
        e1_id, e2_id = e1.id, e2.id
    resp = client.get(f'/admin/tipos_os/etapas/{proc1_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['id'] == e1_id
    resp = client.get(f'/admin/tipos_os/etapas/{proc2_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]['id'] == e2_id

