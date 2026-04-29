from datetime import datetime
import os
import uuid

from flask import Blueprint, current_app as app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from werkzeug.utils import secure_filename

try:
    from ..core.database import db
    from ..core.models import Boletim, User
    from ..core.services.ocr_queue import enqueue_boletim_for_ocr
except ImportError:  # pragma: no cover
    from core.database import db
    from core.models import Boletim, User
    from core.services.ocr_queue import enqueue_boletim_for_ocr

boletins_bp = Blueprint('boletins_bp', __name__)


def _require_permission(permission_name: str, redirect_endpoint: str = 'pagina_inicial'):
    if 'user_id' not in session:
        flash('Por favor, faça login.', 'warning')
        return None, redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.has_permissao(permission_name):
        flash('Permissão negada.', 'danger')
        return None, redirect(url_for(redirect_endpoint))
    return user, None


def _ocr_status_badge(status: str) -> str:
    map_css = {
        'concluido': 'success',
        'pendente': 'warning',
        'processando': 'info',
        'erro': 'danger',
        'baixo_aproveitamento': 'secondary',
        'nao_aplicavel': 'light',
    }
    return map_css.get((status or '').lower(), 'dark')


@boletins_bp.route('/boletins', methods=['GET'], endpoint='boletins_listar')
def listar_boletins():
    user, denied = _require_permission('boletim_visualizar')
    if denied:
        return denied

    boletins = Boletim.query.order_by(Boletim.data_boletim.desc(), Boletim.id.desc()).all()
    return render_template(
        'boletins/listagem.html',
        boletins=boletins,
        can_manage=user.has_permissao('boletim_gerenciar'),
        badge_for=_ocr_status_badge,
    )


@boletins_bp.route('/boletins/novo', methods=['GET', 'POST'], endpoint='boletins_novo')
def novo_boletim():
    user, denied = _require_permission('boletim_gerenciar', redirect_endpoint='boletins_listar')
    if denied:
        return denied

    if request.method == 'POST':
        titulo = (request.form.get('titulo') or '').strip()
        data_raw = (request.form.get('data_boletim') or '').strip()
        arquivo = request.files.get('arquivo')

        if not titulo or not data_raw or not arquivo or not arquivo.filename:
            flash('Título, data e arquivo PDF são obrigatórios.', 'warning')
            return render_template('boletins/novo.html')

        if not arquivo.filename.lower().endswith('.pdf'):
            flash('Envie apenas arquivo PDF.', 'warning')
            return render_template('boletins/novo.html')

        try:
            data_boletim = datetime.strptime(data_raw, '%Y-%m-%d').date()
        except ValueError:
            flash('Data inválida.', 'warning')
            return render_template('boletins/novo.html')

        filename = f"{uuid.uuid4().hex}_{secure_filename(arquivo.filename)}"
        dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        arquivo.save(dest)

        boletim = Boletim(titulo=titulo, data_boletim=data_boletim, arquivo=filename, created_by=user.id)
        db.session.add(boletim)
        enqueue_boletim_for_ocr(boletim)
        db.session.commit()
        flash('Boletim cadastrado com sucesso.', 'success')
        return redirect(url_for('boletins_visualizar', id=boletim.id))

    return render_template('boletins/novo.html')


@boletins_bp.route('/boletins/<int:id>', methods=['GET'], endpoint='boletins_visualizar')
def visualizar_boletim(id: int):
    user, denied = _require_permission('boletim_visualizar', redirect_endpoint='boletins_listar')
    if denied:
        return denied

    boletim = Boletim.query.get_or_404(id)
    return render_template('boletins/visualizar.html', boletim=boletim, can_manage=user.has_permissao('boletim_gerenciar'))


@boletins_bp.route('/boletins/buscar', methods=['GET'], endpoint='boletins_buscar')
def buscar_boletins():
    user, denied = _require_permission('boletim_buscar', redirect_endpoint='boletins_listar')
    if denied:
        return denied

    termo = (request.args.get('q') or '').strip()
    query = Boletim.query
    if termo:
        like = f"%{termo}%"
        query = query.filter(or_(Boletim.titulo.ilike(like), Boletim.ocr_text.ilike(like)))

    boletins = query.order_by(Boletim.data_boletim.desc(), Boletim.id.desc()).all()
    return render_template('boletins/busca.html', boletins=boletins, termo=termo, can_manage=user.has_permissao('boletim_gerenciar'))


@boletins_bp.route('/boletins/<int:id>/editar', methods=['GET', 'POST'], endpoint='boletins_editar')
def editar_boletim(id: int):
    _, denied = _require_permission('boletim_gerenciar', redirect_endpoint='boletins_listar')
    if denied:
        return denied

    boletim = Boletim.query.get_or_404(id)
    if request.method == 'POST':
        boletim.titulo = (request.form.get('titulo') or boletim.titulo).strip() or boletim.titulo
        data_raw = (request.form.get('data_boletim') or '').strip()
        if data_raw:
            try:
                boletim.data_boletim = datetime.strptime(data_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Data inválida.', 'warning')
                return render_template('boletins/novo.html', boletim=boletim, modo_edicao=True)

        db.session.commit()
        flash('Boletim atualizado.', 'success')
        return redirect(url_for('boletins_visualizar', id=boletim.id))

    return render_template('boletins/novo.html', boletim=boletim, modo_edicao=True)


@boletins_bp.route('/boletins/<int:id>/reprocessar-ocr', methods=['POST'], endpoint='boletins_reprocessar_ocr')
def reprocessar_ocr_boletim(id: int):
    _, denied = _require_permission('boletim_gerenciar', redirect_endpoint='boletins_listar')
    if denied:
        return denied

    boletim = Boletim.query.get_or_404(id)
    enqueue_boletim_for_ocr(boletim)
    db.session.commit()
    flash('OCR reenfileirado para processamento.', 'success')
    return redirect(url_for('boletins_visualizar', id=id))


@boletins_bp.route('/boletins/<int:id>/excluir', methods=['POST'], endpoint='boletins_excluir')
def excluir_boletim(id: int):
    _, denied = _require_permission('boletim_gerenciar', redirect_endpoint='boletins_listar')
    if denied:
        return denied

    boletim = Boletim.query.get_or_404(id)
    db.session.delete(boletim)
    db.session.commit()
    flash('Boletim excluído com sucesso.', 'success')
    return redirect(url_for('boletins_listar'))
