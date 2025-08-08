import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app

try:
    from ..core.database import db
except ImportError:  # pragma: no cover
    from core.database import db

try:
    from ..core.models import OrdemServico, TipoOS, CargoProcesso, OrdemServicoLog, OrdemServicoComentario, User
except ImportError:  # pragma: no cover
    from core.models import OrdemServico, TipoOS, CargoProcesso, OrdemServicoLog, OrdemServicoComentario, User

try:
    from ..core.enums import OSStatus, OSPrioridade
except ImportError:  # pragma: no cover
    from core.enums import OSStatus, OSPrioridade

try:
    from ..core.utils import send_email
except ImportError:  # pragma: no cover
    from core.utils import send_email

try:
    from ..core.decorators import admin_required
except ImportError:  # pragma: no cover
    from core.decorators import admin_required

ordens_servico_bp = Blueprint('ordens_servico_bp', __name__)


def _usuario_pode_acessar_os(usuario, os_obj):
    """Verifica se o usuário tem permissão para acessar a OS."""
    if not usuario or not os_obj:
        return False
    if os_obj.criado_por_id == usuario.id:
        return True
    if usuario in os_obj.participantes:
        return True
    if os_obj.equipe_responsavel_id == getattr(usuario, 'celula_id', None) and usuario.pode_atender_os:
        return True
    return False


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
        origem = request.form.get('origem') or None
        observacoes = request.form.get('observacoes') or None
        atribuido_para_id = request.form.get('atribuido_para_id') or None
        if not titulo:
            flash('Título da Ordem de Serviço é obrigatório.', 'danger')
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
                ordem.origem = origem
                ordem.observacoes = observacoes
                ordem.atribuido_para_id = atribuido_para_id
                action_msg = 'atualizada'
            else:
                ordem = OrdemServico(
                    titulo=titulo,
                    descricao=descricao,
                    tipo_os_id=tipo_os_id,
                    equipe_responsavel_id=tipo_obj.equipe_responsavel_id if tipo_obj else None,
                    status=status,
                    prioridade=prioridade,
                    origem=origem,
                    observacoes=observacoes,
                    atribuido_para_id=atribuido_para_id,
                    criado_por_id=session.get('user_id'),
                )
                db.session.add(ordem)
                origem_status = None
                action_msg = 'criada'
            try:
                if status == OSStatus.AGUARDANDO.value and not ordem.pode_mudar_para_aguardando():
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
    return render_template(
        'admin/ordens_servico.html',
        ordens=ordens,
        ordem_editar=ordem_editar,
        tipos_os=tipos_os,
        prioridades=OSPrioridade,
        status_choices=OSStatus,
    )


@ordens_servico_bp.route('/admin/ordens_servico/delete/<ordem_id>', methods=['POST'])
@admin_required
def admin_delete_ordem(ordem_id):
    ordem = OrdemServico.query.get_or_404(ordem_id)
    try:
        db.session.delete(ordem)
        db.session.commit()
        flash('Ordem de Serviço removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao remover ordem de serviço: {str(e)}', 'danger')
    return redirect(url_for('ordens_servico_bp.admin_ordens_servico'))


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
        origem = request.form.get('origem') or None
        observacoes = request.form.get('observacoes') or None
        if not titulo:
            flash('Título da Ordem de Serviço é obrigatório.', 'danger')
        else:
            ordem = OrdemServico(
                titulo=titulo,
                descricao=descricao,
                tipo_os_id=tipo_os_id,
                prioridade=prioridade,
                origem=origem,
                observacoes=observacoes,
                criado_por_id=session.get('user_id'),
                equipe_responsavel_id=tipo_obj.equipe_responsavel_id if tipo_obj else None,
            )
            try:
                db.session.add(ordem)
                db.session.commit()
                flash('Ordem de Serviço criada com sucesso!', 'success')
                return redirect(url_for('ordens_servico_bp.os_listar'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar ordem de serviço: {str(e)}', 'danger')
    usuario = User.query.get(session['user_id'])
    tipos_os = []
    if usuario and usuario.cargo_id:
        sub_ids = [cp.subprocesso_id for cp in CargoProcesso.query.filter_by(cargo_id=usuario.cargo_id).all()]
        if sub_ids:
            tipos_os = TipoOS.query.filter(TipoOS.subprocesso_id.in_(sub_ids)).order_by(TipoOS.nome).all()
    return render_template('ordens_servico/nova_os.html', tipos_os=tipos_os, prioridades=OSPrioridade)


@ordens_servico_bp.route('/os', endpoint='os_listar')
def os_listar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordens = OrdemServico.query.order_by(OrdemServico.data_criacao.desc()).all()
    return render_template('ordens_servico/listar_os.html', ordens=ordens)


@ordens_servico_bp.route('/os/<ordem_id>', endpoint='os_detalhar')
def os_detalhar(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordem = OrdemServico.query.get_or_404(ordem_id)
    return render_template('ordens_servico/detalhe_os.html', ordem=ordem)


@ordens_servico_bp.route('/os/minhas', endpoint='os_minhas')
def os_minhas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordens = OrdemServico.query.order_by(OrdemServico.data_criacao.desc()).all()
    return render_template('ordens_servico/minhas_os.html', ordens=ordens)


@ordens_servico_bp.route('/os/atendimento', methods=['GET'], endpoint='os_atendimento')
def os_atendimento():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    if not usuario or not usuario.pode_atender_os:
        abort(403)
    query = OrdemServico.query.filter_by(equipe_responsavel_id=usuario.celula_id)
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
    ordem = OrdemServico.query.get_or_404(ordem_id)
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
    ordem = OrdemServico.query.get_or_404(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    novo_status = request.form.get('status')
    if novo_status not in [s.value for s in OSStatus]:
        abort(400)
    if novo_status == OSStatus.AGUARDANDO.value and not ordem.pode_mudar_para_aguardando():
        flash('Formulário obrigatório não preenchido', 'danger')
        return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.id))
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
    return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.id))


@ordens_servico_bp.post('/os/<ordem_id>/comentario', endpoint='os_comentar')
def os_comentar(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = OrdemServico.query.get_or_404(ordem_id)
    if not _usuario_pode_acessar_os(usuario, ordem):
        abort(403)
    mensagem = request.form.get('mensagem', '').strip()
    if mensagem:
        comentario = OrdemServicoComentario(os_id=ordem.id, usuario_id=usuario.id, mensagem=mensagem)
        db.session.add(comentario)
        db.session.commit()
    return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.id))


@ordens_servico_bp.post('/os/<ordem_id>/anexo', endpoint='os_anexo')
def os_anexo(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = OrdemServico.query.get_or_404(ordem_id)
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
    return redirect(url_for('ordens_servico_bp.os_atendimento_detalhar', ordem_id=ordem.id))


@ordens_servico_bp.route('/os/<ordem_id>/historico', methods=['GET'], endpoint='os_historico')
def os_historico(ordem_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    usuario = User.query.get(session['user_id'])
    ordem = OrdemServico.query.get_or_404(ordem_id)
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

