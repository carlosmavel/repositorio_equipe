from flask import Blueprint, render_template, request, redirect, url_for, flash, session

try:
    from ..core.database import db
except ImportError:  # pragma: no cover
    from core.database import db

try:
    from ..core.models import OrdemServico, Processo, OrdemServicoLog
except ImportError:  # pragma: no cover
    from core.models import OrdemServico, Processo, OrdemServicoLog

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
    processos = Processo.query.order_by(Processo.nome).all()
    return render_template(
        'admin/ordens_servico.html',
        ordens=ordens,
        ordem_editar=ordem_editar,
        processos=processos,
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
            )
            try:
                db.session.add(ordem)
                db.session.commit()
                flash('Ordem de Serviço criada com sucesso!', 'success')
                return redirect(url_for('ordens_servico_bp.os_listar'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar ordem de serviço: {str(e)}', 'danger')
    processos = Processo.query.order_by(Processo.nome).all()
    return render_template('ordens_servico/nova_os.html', processos=processos, prioridades=OSPrioridade)


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

