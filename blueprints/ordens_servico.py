from flask import Blueprint, render_template, request, redirect, url_for, flash, session

try:
    from ..database import db
except ImportError:  # pragma: no cover
    from database import db

try:
    from ..models import OrdemServico, Processo
except ImportError:  # pragma: no cover
    from models import OrdemServico, Processo

try:
    from ..decorators import admin_required
except ImportError:  # pragma: no cover
    from decorators import admin_required

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
        processo_id = request.form.get('processo_id') or None
        status = request.form.get('status', 'aberta').strip() or 'aberta'
        if not titulo:
            flash('Título da Ordem de Serviço é obrigatório.', 'danger')
        else:
            if id_para_atualizar:
                ordem = OrdemServico.query.get_or_404(id_para_atualizar)
                ordem.titulo = titulo
                ordem.descricao = descricao
                ordem.processo_id = processo_id
                ordem.status = status
                action_msg = 'atualizada'
            else:
                ordem = OrdemServico(
                    titulo=titulo,
                    descricao=descricao,
                    processo_id=processo_id,
                    status=status,
                )
                db.session.add(ordem)
                action_msg = 'criada'
            try:
                db.session.commit()
                flash(f'Ordem de Serviço {action_msg} com sucesso!', 'success')
                return redirect(url_for('ordens_servico_bp.admin_ordens_servico'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar ordem de serviço: {str(e)}', 'danger')
        if id_para_atualizar:
            ordem_editar = OrdemServico.query.get(id_para_atualizar)
    ordens = OrdemServico.query.order_by(OrdemServico.created_at.desc()).all()
    processos = Processo.query.order_by(Processo.nome).all()
    return render_template(
        'admin/ordens_servico.html',
        ordens=ordens,
        ordem_editar=ordem_editar,
        processos=processos,
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
        processo_id = request.form.get('processo_id') or None
        if not titulo:
            flash('Título da Ordem de Serviço é obrigatório.', 'danger')
        else:
            ordem = OrdemServico(
                titulo=titulo,
                descricao=descricao,
                processo_id=processo_id,
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
    return render_template('ordens_servico/nova_os.html', processos=processos)


@ordens_servico_bp.route('/os', endpoint='os_listar')
def os_listar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ordens = OrdemServico.query.order_by(OrdemServico.created_at.desc()).all()
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
    ordens = OrdemServico.query.order_by(OrdemServico.created_at.desc()).all()
    return render_template('ordens_servico/minhas_os.html', ordens=ordens)

