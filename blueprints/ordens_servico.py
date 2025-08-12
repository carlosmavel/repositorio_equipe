import os
import json
from collections import defaultdict
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app
from sqlalchemy import or_

try:
    from ..core.database import db
except ImportError:  # pragma: no cover
    from core.database import db

try:
    from ..core.models import (
        OrdemServico,
        TipoOS,
        OrdemServicoLog,
        OrdemServicoComentario,
        User,
        Formulario,
        Celula,
        Equipamento,
        Sistema,
        ProcessoEtapa,
        processo_etapa_cargo_abre,
    )
except ImportError:  # pragma: no cover
    from core.models import (
        OrdemServico,
        TipoOS,
        OrdemServicoLog,
        OrdemServicoComentario,
        User,
        Formulario,
        Celula,
        Equipamento,
        Sistema,
        ProcessoEtapa,
        processo_etapa_cargo_abre,
    )

try:
    from ..core.enums import OSStatus, OSPrioridade
except ImportError:  # pragma: no cover
    from core.enums import OSStatus, OSPrioridade

try:
    from ..core.utils import send_email, gerar_codigo_os
except ImportError:  # pragma: no cover
    from core.utils import send_email, gerar_codigo_os

try:
    from ..core.decorators import admin_required
except ImportError:  # pragma: no cover
    from core.decorators import admin_required

ordens_servico_bp = Blueprint('ordens_servico_bp', __name__)

SISTEMA_STATUS = ['Ativo', 'Inativo']
EQUIPAMENTO_STATUS = ['Operacional', 'Manutenção', 'Inativo']


def _usuario_pode_acessar_os(usuario, os_obj):
    """Verifica se o usuário tem permissão para acessar a OS."""
    if not usuario or not os_obj:
        return False
    if os_obj.status == OSStatus.RASCUNHO.value:
        return os_obj.criado_por_id == usuario.id
    if os_obj.criado_por_id == usuario.id:
        return True
    if usuario in os_obj.participantes:
        return True
    if os_obj.equipe_responsavel_id == getattr(usuario, 'celula_id', None) and usuario.pode_atender_os:
        return True
    return False


def _get_ordem_servico(identifier):
    """Recupera OrdemServico por id (UUID) ou código."""
    ordem = OrdemServico.query.get(identifier)
    if not ordem:
        ordem = OrdemServico.query.filter_by(codigo=identifier).first()
    if not ordem:
        abort(404)
    return ordem


@ordens_servico_bp.route('/admin/ordens_servico', methods=['GET', 'POST'])
@admin_required
def admin_ordens_servico():
    ordem_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id')
        if edit_id:
            ordem_editar = OrdemServico.query.get_or_404(edit_id)
    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar')
        titulo = request.form.get('titulo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        tipo_os_id = request.form.get('tipo_os_id') or None
        tipo_obj = TipoOS.query.get(tipo_os_id) if tipo_os_id else None
        status = request.form.get('status', OSStatus.RASCUNHO.value)
        prioridade = request.form.get('prioridade') or None
        equipamento_id = request.form.get('equipamento_id', type=int)
        sistema_id = request.form.get('sistema_id', type=int)
        observacoes = request.form.get('observacoes') or None
        atribuido_para_id = request.form.get('atribuido_para_id') or None
        if not titulo:
            flash('Título da Ordem de Serviço é obrigatório.', 'danger')
        elif not (equipamento_id or sistema_id):
            flash('Informe ao menos Equipamento ou Sistema.', 'danger')
        else:
            if id_para_atualizar:
                ordem = OrdemServico.query.get_or_404(id_para_atualizar)
                origem_status = ordem.status
                ordem.titulo = titulo
                ordem.descricao = descricao
                ordem.tipo_os_id = tipo_os_id
                ordem.equipe_responsavel_id = tipo_obj.equipe_responsavel_id if tipo_obj else None
                ordem.status = status
                ordem.prioridade = prioridade
                ordem.equipamento_id = equipamento_id
                ordem.sistema_id = sistema_id
                ordem.observacoes = observacoes
                ordem.atribuido_para_id = atribuido_para_id
                action_msg = 'atualizada'
            else:
                ordem = OrdemServico(
                    codigo=gerar_codigo_os(),
                    titulo=titulo,
                    descricao=descricao,
                    tipo_os_id=tipo_os_id,
                    equipe_responsavel_id=tipo_obj.equipe_responsavel_id if tipo_obj else None,
                    status=status,
                    prioridade=prioridade,
                    equipamento_id=equipamento_id,
                    sistema_id=sistema_id,
                    observacoes=observacoes,
                    atribuido_para_id=atribuido_para_id,
                    criado_por_id=session.get('user_id'),
                )
                db.session.add(ordem)
                origem_status = None
                action_msg = 'criada'
            try:
                if status == OSStatus.AGUARDANDO_ATENDIMENTO.value and not ordem.pode_mudar_para_aguardando():
                    raise ValueError('Formulário obrigatório não preenchido')
                db.session.commit()
                log = OrdemServicoLog(
                    os_id=ordem.id,
                    usuario_id=session.get('user_id'),
                    acao='status_alterado' if origem_status and origem_status != status else 'criada',
                    origem_status=origem_status,
                    destino_status=ordem.status,
                )
                db.session.add(log)
                db.session.commit()
                if origem_status != ordem.status:
                    try:
                        send_email(ordem.criado_por.email, 'Status da OS atualizado', f'Sua OS agora está em {ordem.status}')
                    except Exception:
                        pass
                flash(f'Ordem de Serviço {action_msg} com sucesso!', 'success')
                return redirect(url_for('ordens_servico_bp.admin_ordens_servico'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar ordem de serviço: {str(e)}', 'danger')
        if id_para_atualizar:
            ordem_editar = OrdemServico.query.get(id_para_atualizar)
    ordens = OrdemServico.query.order_by(OrdemServico.data_criacao.desc()).all()
    tipos_os = TipoOS.query.order_by(TipoOS.nome).all()
    equipamentos = Equipamento.query.order_by(Equipamento.nome).all()
    sistemas = Sistema.query.order_by(Sistema.nome).all()
    return render_template(
        'admin/ordens_servico.html',
        ordens=ordens,
        ordem_editar=ordem_editar,
        tipos_os=tipos_os,
        equipamentos=equipamentos,
        sistemas=sistemas,
        prioridades=OSPrioridade,
        status_choices=OSStatus,
    )


@ordens_servico_bp.route('/admin/ordens_servico/delete/<ordem_id>', methods=['POST'])
@admin_required
def admin_delete_ordem(ordem_id):
    ordem = _get_ordem_servico(ordem_id)
    try:
        db.session.delete(ordem)
        db.session.commit()
        flash('Ordem de Serviço removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover ordem de serviço: {str(e)}', 'danger')
    return redirect(url_for('ordens_servico_bp.admin_ordens_servico'))


@ordens_servico_bp.route('/admin/tipos_os', methods=['GET', 'POST'], endpoint='tipos_os_admin')
@admin_required
def tipos_os_admin():
    tipo_editar = None
    if request.method == 'GET':
        edit_id = request.args.get('edit_id', type=int)
        if edit_id:
            tipo_editar = TipoOS.query.get_or_404(edit_id)
    if request.method == 'POST':
        id_para_atualizar = request.form.get('id_para_atualizar', type=int)
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        etapa_id = request.form.get('etapa_id')
        equipe_responsavel_id = request.form.get('equipe_responsavel_id', type=int)
        formulario_vinculado_id = request.form.get('formulario_vinculado_id', type=int)
        obrigatorio_preenchimento = request.form.get('obrigatorio_preenchimento') == 'on'
        if not nome or not etapa_id:
            flash('Nome e Etapa são obrigatórios.', 'danger')
        else:
            etapa = ProcessoEtapa.query.get(etapa_id)
            if id_para_atualizar:
                tipo = TipoOS.query.get_or_404(id_para_atualizar)
                tipo.nome = nome
                tipo.descricao = descricao
                tipo.equipe_responsavel_id = equipe_responsavel_id
                tipo.formulario_vinculado_id = formulario_vinculado_id
                tipo.obrigatorio_preenchimento = obrigatorio_preenchimento
                tipo.etapas = [etapa] if etapa else []
                action_msg = 'atualizado'
            else:
                tipo = TipoOS(
                    nome=nome,
                    descricao=descricao,
                    equipe_responsavel_id=equipe_responsavel_id,
                    formulario_vinculado_id=formulario_vinculado_id,
                    obrigatorio_preenchimento=obrigatorio_preenchimento,
                )
                if etapa:
                    tipo.etapas.append(etapa)
                db.session.add(tipo)
                action_msg = 'criado'
            try:
                db.session.commit()
                flash(f'Tipo de OS {action_msg} com sucesso!', 'success')
                return redirect(url_for('ordens_servico_bp.tipos_os_admin'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar tipo de OS: {str(e)}', 'danger')
        if id_para_atualizar:
            tipo_editar = TipoOS.query.get(id_para_atualizar)
    tipos = TipoOS.query.order_by(TipoOS.nome).all()
    etapas = ProcessoEtapa.query.order_by(ProcessoEtapa.nome).all()
    celulas = Celula.query.order_by(Celula.nome).all()
    formularios_list = Formulario.query.order_by(Formulario.nome).all()
    formularios_dict = {f.id: f for f in formularios_list}
    return render_template(
        'admin/tipos_os.html',
        tipos=tipos,
        tipo_editar=tipo_editar,
        etapas=etapas,
        celulas=celulas,
        formularios=formularios_list,
        formularios_dict=formularios_dict,
    )


@ordens_servico_bp.route('/admin/tipos_os/delete/<int:id>', methods=['POST'], endpoint='tipos_os_admin_delete')
@admin_required
def tipos_os_admin_delete(id):
    tipo = TipoOS.query.get_or_404(id)
    try:
        db.session.delete(tipo)
        db.session.commit()
        flash('Tipo de OS removido com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover Tipo de OS: {str(e)}', 'danger')
    return redirect(url_for('ordens_servico_bp.tipos_os_admin'))


@ordens_servico_bp.route('/os/nova', methods=['GET', 'POST'], endpoint='os_nova')
def os_nova():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        tipo_os_id = request.form.get('tipo_os_id') or None
        tipo_obj = TipoOS.query.get(tipo_os_id) if tipo_os_id else None
        prioridade = request.form.get('prioridade') or None
        equipamento_id = request.form.get('equipamento_id', type=int)
        sistema_id = request.form.get('sistema_id', type=int)
        observacoes = request.form.get('observacoes') or None
        acao = request.form.get('action')
        status = (
            OSStatus.AGUARDANDO_ATENDIMENTO.value
            if acao == 'enviar'
            else OSStatus.RASCUNHO.value
        )
        if not titulo:
            flash('Título da Ordem de Serviço é obrigatório.', 'danger')
        elif not (equipamento_id or sistema_id):
            flash('Informe ao menos Equipamento ou Sistema.', 'danger')
        else:
            ordem = OrdemServico(
                codigo=gerar_codigo_os(),
                titulo=titulo,
                descricao=descricao,
                tipo_os_id=tipo_os_id,
                prioridade=prioridade,
                equipamento_id=equipamento_id,
                sistema_id=sistema_id,
                observacoes=observacoes,
                criado_por_id=session.get('user_id'),
                equipe_responsavel_id=tipo_obj.equipe_responsavel_id if tipo_obj else None,
                status=status,
            )
            try:
                if status == OSStatus.AGUARDANDO_ATENDIMENTO.value and not ordem.pode_mudar_para_aguardando():
                    raise ValueError('Formulário obrigatório não preenchido')
                db.session.add(ordem)
                db.session.commit()
                if status == OSStatus.RASCUNHO.value:
                    flash('Rascunho salvo com sucesso!', 'success')
                    return redirect(url_for('ordens_servico_bp.os_minhas'))
                flash('Ordem de Serviço enviada com sucesso!', 'success')
                return redirect(url_for('ordens_servico_bp.os_listar'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar ordem de serviço: {str(e)}', 'danger')
    usuario = User.query.get(session['user_id'])
    query = TipoOS.query
    if usuario and usuario.cargo_id:
        query = (
            query.join(TipoOS.etapas)
            .outerjoin(
                processo_etapa_cargo_abre,
                ProcessoEtapa.id == processo_etapa_cargo_abre.c.etapa_id,
            )
            .filter(
                (processo_etapa_cargo_abre.c.cargo_id == usuario.cargo_id)
                | (processo_etapa_cargo_abre.c.cargo_id.is_(None))
            )
        )
    tipos_os = query.order_by(TipoOS.nome).distinct().all()
    equipamentos = Equipamento.query.order_by(Equipamento.nome).all()
    sistemas = Sistema.query.order_by(Sistema.nome).all()
    return render_template(
        'ordens_servico/nova_os.html',
        tipos_os=tipos_os,
        prioridades=OSPrioridade,
        usuario=usuario,
        equipamentos=equipamentos,
        sistemas=sistemas,
    )


@ordens_servico_bp.get('/os/tipo/<int:tipo_id>/formulario', endpoint='os_formulario_vinculado')
def os_formulario_vinculado(tipo_id):
    if 'user_id' not in session:
        return jsonify({'html': '', 'obrigatorio': False})
    tipo = TipoOS.query.get_or_404(tipo_id)
    html = ''
    if tipo.formulario_vinculado_id:
        formulario = Formulario.query.get(tipo.formulario_vinculado_id)
        if formulario and formulario.estrutura:
            try:
                estrutura = json.loads(formulario.estrutura)
            except ValueError:
                estrutura = []
            html = render_template('ordens_servico/_formulario_vinculado.html', estrutura=estrutura)
    return jsonify({'html': html, 'obrigatorio': tipo.obrigatorio_preenchimento})


@ordens_servico_bp.route('/os', endpoint='os_listar')
def os_listar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordens = (
        OrdemServico.query.filter(OrdemServico.status != OSStatus.RASCUNHO.value)
        .order_by(OrdemServico.data_criacao.desc())
        .all()
    )
    return render_template('ordens_servico/listar_os.html', ordens=ordens, status_enum=OSStatus)


@ordens_servico_bp.route('/os/<ordem_id>', endpoint='os_detalhar')
def os_detalhar(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordem = _get_ordem_servico(ordem_id)
    return render_template('ordens_servico/detalhe_os.html', ordem=ordem, status_enum=OSStatus)


@ordens_servico_bp.route('/os/minhas', endpoint='os_minhas')
def os_minhas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordens = (
        OrdemServico.query.filter_by(criado_por_id=session['user_id'])
        .order_by(OrdemServico.data_criacao.desc())
        .all()
    )
    rascunhos = [o for o in ordens if o.status == OSStatus.RASCUNHO.value]
    ordens = [o for o in ordens if o.status != OSStatus.RASCUNHO.value]
    return render_template('ordens_servico/minhas_os.html', ordens=ordens, rascunhos=rascunhos, status_enum=OSStatus)


@ordens_servico_bp.route('/os/kanban', endpoint='os_kanban')
def os_kanban():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordens = (
        OrdemServico.query.filter_by(criado_por_id=session['user_id'])
        .order_by(OrdemServico.data_criacao.desc())
        .all()
    )
    columns = defaultdict(list)
    for os_obj in ordens:
        st = os_obj.status
        if st == OSStatus.RASCUNHO.value:
            columns['rascunho'].append(os_obj)
        elif st in [
            OSStatus.AGUARDANDO_ATENDIMENTO.value,
            OSStatus.AGUARDANDO_INFORMACOES_SOLICITANTE.value,
            OSStatus.AGUARDANDO_INTERACAO_TERCEIRO.value,
        ]:
            columns['aguardando'].append(os_obj)
        elif st == OSStatus.EM_ATENDIMENTO.value:
            columns['em_atendimento'].append(os_obj)
        elif st in [
            OSStatus.ENCAMINHADA_PARA_OUTRA_EQUIPE.value,
            OSStatus.PAUSADA.value,
        ]:
            columns['pendente'].append(os_obj)
        elif st == OSStatus.CONCLUIDA.value:
            columns['concluida'].append(os_obj)
        elif st in [OSStatus.CANCELADA.value, OSStatus.REJEITADA.value]:
            columns['cancelada'].append(os_obj)
        else:
            columns['pendente'].append(os_obj)
    labels = {
        'rascunho': 'Rascunho',
        'aguardando': 'Aguardando',
        'em_atendimento': 'Em Atendimento',
        'pendente': 'Pendente',
        'concluida': 'Concluída',
        'cancelada': 'Cancelada',
    }
    order = ['rascunho', 'aguardando', 'em_atendimento', 'pendente', 'concluida', 'cancelada']
    return render_template(
        'ordens_servico/kanban.html',
        columns=columns,
        labels=labels,
        order=order,
        show_draft=True,
        title='Acompanhar OS',
    )


@ordens_servico_bp.route('/os/atendimento/kanban', endpoint='os_kanban_atendimento')
def os_kanban_atendimento():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    if not usuario or not usuario.pode_atender_os:
        abort(403)
    ordens = (
        OrdemServico.query.filter_by(equipe_responsavel_id=usuario.celula_id)
        .filter(OrdemServico.status != OSStatus.RASCUNHO.value)
        .order_by(OrdemServico.data_criacao.desc())
        .all()
    )
    columns = defaultdict(list)
    for os_obj in ordens:
        st = os_obj.status
        if st in [
            OSStatus.AGUARDANDO_ATENDIMENTO.value,
            OSStatus.AGUARDANDO_INFORMACOES_SOLICITANTE.value,
            OSStatus.AGUARDANDO_INTERACAO_TERCEIRO.value,
        ]:
            columns['aguardando'].append(os_obj)
        elif st == OSStatus.EM_ATENDIMENTO.value:
            columns['em_atendimento'].append(os_obj)
        elif st in [
            OSStatus.ENCAMINHADA_PARA_OUTRA_EQUIPE.value,
            OSStatus.PAUSADA.value,
        ]:
            columns['pendente'].append(os_obj)
        elif st == OSStatus.CONCLUIDA.value:
            columns['concluida'].append(os_obj)
        elif st in [OSStatus.CANCELADA.value, OSStatus.REJEITADA.value]:
            columns['cancelada'].append(os_obj)
        else:
            columns['pendente'].append(os_obj)
    labels = {
        'aguardando': 'Aguardando',
        'em_atendimento': 'Em Atendimento',
        'pendente': 'Pendente',
        'concluida': 'Concluída',
        'cancelada': 'Cancelada',
    }
    order = ['aguardando', 'em_atendimento', 'pendente', 'concluida', 'cancelada']
    return render_template(
        'ordens_servico/kanban.html',
        columns=columns,
        labels=labels,
        order=order,
        show_draft=False,
        title='Kanban de OS',
    )


@ordens_servico_bp.route('/os/atendimento', methods=['GET'], endpoint='os_atendimento')
def os_atendimento():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    if not usuario or not usuario.pode_atender_os:
        abort(403)
    query = OrdemServico.query.filter_by(equipe_responsavel_id=usuario.celula_id).filter(
        OrdemServico.status != OSStatus.RASCUNHO.value
    )
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    tipo = request.args.get('tipo')
    if tipo:
        query = query.filter_by(tipo_os_id=tipo)
    busca = request.args.get('busca', '').strip()
    if busca:
        query = query.filter(OrdemServico.titulo.ilike(f'%{busca}%'))
    ordens = query.order_by(OrdemServico.data_criacao.desc()).all()
    tipos_os = TipoOS.query.order_by(TipoOS.nome).all()
    return render_template(
        'ordens_servico/atendimento_list.html',
        ordens=ordens,
        tipos_os=tipos_os,
        status_choices=OSStatus,
    )


@ordens_servico_bp.route('/os/atendimento/<ordem_id>', methods=['GET'], endpoint='os_atendimento_detalhar')
def os_atendimento_detalhar(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = _get_ordem_servico(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    comentarios = OrdemServicoComentario.query.filter_by(os_id=ordem.id).order_by(OrdemServicoComentario.data_hora.asc()).all()
    return render_template(
        'ordens_servico/atendimento_detalhe.html',
        ordem=ordem,
        comentarios=comentarios,
        status_choices=OSStatus,
    )


@ordens_servico_bp.post('/os/<ordem_id>/status', endpoint='os_mudar_status')
def os_mudar_status(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = _get_ordem_servico(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    novo_status = request.form.get('status')
    if novo_status not in [s.value for s in OSStatus]:
        abort(400)
    if novo_status == OSStatus.AGUARDANDO_ATENDIMENTO.value and not ordem.pode_mudar_para_aguardando():
        flash('Formulário obrigatório não preenchido', 'danger')
        return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.codigo))
    origem = ordem.status
    ordem.status = novo_status
    log = OrdemServicoLog(
        os_id=ordem.id,
        usuario_id=usuario.id,
        acao='status_alterado',
        origem_status=origem,
        destino_status=novo_status,
    )
    db.session.add(log)
    db.session.commit()
    return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.codigo))


@ordens_servico_bp.post('/os/<ordem_id>/comentario', endpoint='os_comentar')
def os_comentar(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = _get_ordem_servico(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    mensagem = request.form.get('mensagem', '').strip()
    if mensagem:
        comentario = OrdemServicoComentario(os_id=ordem.id, usuario_id=usuario.id, mensagem=mensagem)
        db.session.add(comentario)
        db.session.commit()
    return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.codigo))


@ordens_servico_bp.post('/os/<ordem_id>/anexo', endpoint='os_anexo')
def os_anexo(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = _get_ordem_servico(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    arquivo = request.files.get('anexo')
    if arquivo and arquivo.filename:
        filename = arquivo.filename
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        path = os.path.join(upload_dir, filename)
        arquivo.save(path)
        comentario = OrdemServicoComentario(os_id=ordem.id, usuario_id=usuario.id, mensagem='', anexo=filename)
        db.session.add(comentario)
        db.session.commit()
    return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.codigo))


@ordens_servico_bp.route('/os/<ordem_id>/historico', methods=['GET'], endpoint='os_historico')
def os_historico(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = _get_ordem_servico(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    logs = OrdemServicoLog.query.filter_by(os_id=ordem.id).order_by(OrdemServicoLog.data_hora.asc()).all()
    historico = [
        {
            'acao': l.acao,
            'origem_status': l.origem_status,
            'destino_status': l.destino_status,
            'data_hora': l.data_hora.isoformat(),
        }
        for l in logs
    ]
    return jsonify(historico)


# ----------------------------
# CRUD de Sistemas
# ----------------------------


@ordens_servico_bp.route('/os/sistemas')
@admin_required
def sistemas_list():
    search = request.args.get('q', '')
    status = request.args.get('status', '')
    sort = request.args.get('sort', 'nome')
    page = request.args.get('page', type=int, default=1)

    query = Sistema.query
    if search:
        query = query.filter(Sistema.nome.ilike(f'%{search}%'))
    if status:
        query = query.filter(Sistema.status == status)

    order_col = Sistema.status if sort == 'status' else Sistema.nome
    sistemas = query.order_by(order_col).paginate(page=page, per_page=10)

    return render_template(
        'admin/sistemas_list.html',
        sistemas=sistemas,
        search=search,
        status=status,
        sort=sort,
        status_options=SISTEMA_STATUS,
    )


@ordens_servico_bp.route('/os/sistemas/novo', methods=['GET', 'POST'])
@admin_required
def sistemas_novo():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao') or None
        responsavel = request.form.get('responsavel') or None
        observacoes = request.form.get('observacoes') or None
        status = request.form.get('status', 'Ativo')
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif Sistema.query.filter_by(nome=nome).first():
            flash('Nome já cadastrado.', 'danger')
        else:
            sistema = Sistema(
                nome=nome,
                descricao=descricao,
                responsavel=responsavel,
                observacoes=observacoes,
                status=status,
            )
            db.session.add(sistema)
            db.session.commit()
            flash('Sistema salvo com sucesso!', 'success')
            return redirect(url_for('ordens_servico_bp.sistemas_list'))
    return render_template(
        'admin/sistema_form.html', sistema=None, status_options=SISTEMA_STATUS
    )


@ordens_servico_bp.route('/os/sistemas/<int:sistema_id>/editar', methods=['GET', 'POST'])
@admin_required
def sistemas_editar(sistema_id):
    sistema = Sistema.query.get_or_404(sistema_id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao') or None
        responsavel = request.form.get('responsavel') or None
        observacoes = request.form.get('observacoes') or None
        status = request.form.get('status', 'Ativo')
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif (
            Sistema.query.filter(Sistema.id != sistema.id, Sistema.nome == nome).first()
        ):
            flash('Nome já cadastrado.', 'danger')
        else:
            sistema.nome = nome
            sistema.descricao = descricao
            sistema.responsavel = responsavel
            sistema.observacoes = observacoes
            sistema.status = status
            db.session.commit()
            flash('Sistema salvo com sucesso!', 'success')
            return redirect(url_for('ordens_servico_bp.sistemas_list'))
    return render_template(
        'admin/sistema_form.html', sistema=sistema, status_options=SISTEMA_STATUS
    )


@ordens_servico_bp.route('/os/sistemas/<int:sistema_id>/excluir', methods=['POST'])
@admin_required
def sistemas_excluir(sistema_id):
    sistema = Sistema.query.get_or_404(sistema_id)
    db.session.delete(sistema)
    db.session.commit()
    flash('Sistema excluído com sucesso!', 'success')
    return redirect(url_for('ordens_servico_bp.sistemas_list'))


# ----------------------------
# CRUD de Equipamentos
# ----------------------------


@ordens_servico_bp.route('/os/equipamentos')
@admin_required
def equipamentos_list():
    search = request.args.get('q', '')
    status = request.args.get('status', '')
    localizacao = request.args.get('localizacao', '')
    sort = request.args.get('sort', 'nome')
    page = request.args.get('page', type=int, default=1)

    query = Equipamento.query
    if search:
        query = query.filter(Equipamento.nome.ilike(f'%{search}%'))
    if status:
        query = query.filter(Equipamento.status == status)
    if localizacao:
        query = query.filter(Equipamento.localizacao == localizacao)

    order_col = Equipamento.status if sort == 'status' else Equipamento.nome
    equipamentos = query.order_by(order_col).paginate(page=page, per_page=10)

    locais = [
        l[0]
        for l in db.session.query(Equipamento.localizacao)
        .distinct()
        .filter(Equipamento.localizacao.isnot(None))
        .all()
    ]

    return render_template(
        'admin/equipamentos_list.html',
        equipamentos=equipamentos,
        search=search,
        status=status,
        localizacao=localizacao,
        sort=sort,
        status_options=EQUIPAMENTO_STATUS,
        locais=locais,
    )


@ordens_servico_bp.route('/os/equipamentos/novo', methods=['GET', 'POST'])
@admin_required
def equipamentos_novo():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        patrimonio = request.form.get('patrimonio') or None
        serial = request.form.get('serial') or None
        localizacao = request.form.get('localizacao') or None
        status = request.form.get('status', 'Operacional')
        observacoes = request.form.get('observacoes') or None
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif patrimonio and Equipamento.query.filter_by(patrimonio=patrimonio).first():
            flash('Patrimônio já cadastrado.', 'danger')
        else:
            equipamento = Equipamento(
                nome=nome,
                patrimonio=patrimonio,
                serial=serial,
                localizacao=localizacao,
                status=status,
                observacoes=observacoes,
            )
            db.session.add(equipamento)
            db.session.commit()
            flash('Equipamento salvo com sucesso!', 'success')
            return redirect(url_for('ordens_servico_bp.equipamentos_list'))
    return render_template(
        'admin/equipamento_form.html',
        equipamento=None,
        status_options=EQUIPAMENTO_STATUS,
    )


@ordens_servico_bp.route('/os/equipamentos/<int:equipamento_id>/editar', methods=['GET', 'POST'])
@admin_required
def equipamentos_editar(equipamento_id):
    equipamento = Equipamento.query.get_or_404(equipamento_id)
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        patrimonio = request.form.get('patrimonio') or None
        serial = request.form.get('serial') or None
        localizacao = request.form.get('localizacao') or None
        status = request.form.get('status', 'Operacional')
        observacoes = request.form.get('observacoes') or None
        if not nome:
            flash('Nome é obrigatório.', 'danger')
        elif patrimonio and (
            Equipamento.query.filter(
                Equipamento.id != equipamento.id, Equipamento.patrimonio == patrimonio
            ).first()
        ):
            flash('Patrimônio já cadastrado.', 'danger')
        else:
            equipamento.nome = nome
            equipamento.patrimonio = patrimonio
            equipamento.serial = serial
            equipamento.localizacao = localizacao
            equipamento.status = status
            equipamento.observacoes = observacoes
            db.session.commit()
            flash('Equipamento salvo com sucesso!', 'success')
            return redirect(url_for('ordens_servico_bp.equipamentos_list'))
    return render_template(
        'admin/equipamento_form.html',
        equipamento=equipamento,
        status_options=EQUIPAMENTO_STATUS,
    )


@ordens_servico_bp.route('/os/equipamentos/<int:equipamento_id>/excluir', methods=['POST'])
@admin_required
def equipamentos_excluir(equipamento_id):
    equipamento = Equipamento.query.get_or_404(equipamento_id)
    db.session.delete(equipamento)
    db.session.commit()
    flash('Equipamento excluído com sucesso!', 'success')
    return redirect(url_for('ordens_servico_bp.equipamentos_list'))


# ----------------------------
# APIs para Sistemas e Equipamentos
# ----------------------------


@ordens_servico_bp.route('/api/sistemas')
def api_sistemas():
    q = request.args.get('q', '')
    query = Sistema.query
    if q:
        query = query.filter(Sistema.nome.ilike(f'%{q}%'))
    sistemas = query.order_by(Sistema.nome).limit(10).all()
    return jsonify([{'id': s.id, 'nome': s.nome} for s in sistemas])


@ordens_servico_bp.route('/api/equipamentos')
def api_equipamentos():
    q = request.args.get('q', '')
    query = Equipamento.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            or_(
                Equipamento.nome.ilike(like),
                Equipamento.patrimonio.ilike(like),
                Equipamento.serial.ilike(like),
            )
        )
    equipamentos = query.order_by(Equipamento.nome).limit(10).all()
    return jsonify(
        [
            {
                'id': e.id,
                'nome': e.nome,
                'patrimonio': e.patrimonio,
                'serial': e.serial,
                'status': e.status,
                'localizacao': e.localizacao,
            }
            for e in equipamentos
        ]
    )

