from datetime import datetime
import os
import re
import uuid

from flask import Blueprint, current_app as app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import and_, case, false, func, literal_column, or_, text
from werkzeug.utils import secure_filename

try:
    from ..core.database import db
    from ..core.models import Boletim, User
    from ..core.services.ocr_queue import enqueue_boletim_for_ocr
    from ..core.utils import build_like_pattern, strip_accents
except ImportError:  # pragma: no cover
    from core.database import db
    from core.models import Boletim, User
    from core.services.ocr_queue import enqueue_boletim_for_ocr
    from core.utils import build_like_pattern, strip_accents

boletins_bp = Blueprint('boletins_bp', __name__)


BOLETIM_FTS_CONFIG = literal_column("'portuguese'")


def _boletim_titulo_ocr_text_expression():
    return func.coalesce(Boletim.titulo, '') + ' ' + func.coalesce(Boletim.ocr_text, '')


def _boletim_tsvector_expression():
    return func.to_tsvector(BOLETIM_FTS_CONFIG, _boletim_titulo_ocr_text_expression())


def _boletim_phrase_tsquery_condition(termo: str):
    return _boletim_tsvector_expression().op('@@')(
        func.phraseto_tsquery(BOLETIM_FTS_CONFIG, termo)
    )


def _require_permission(permission_name: str, redirect_endpoint: str = 'pagina_inicial'):
    if 'user_id' not in session:
        flash('Por favor, faça login.', 'warning')
        return None, redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not user.has_permissao(permission_name):
        flash('Permissão negada.', 'danger')
        return None, redirect(url_for(redirect_endpoint))
    return user, None


def _require_any_permission(permission_names: tuple[str, ...], redirect_endpoint: str = 'pagina_inicial'):
    if 'user_id' not in session:
        flash('Por favor, faça login.', 'warning')
        return None, redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or not any(user.has_permissao(p) for p in permission_names):
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
    user, denied = _require_any_permission(('boletim_visualizar', 'boletim_buscar'))
    if denied:
        return denied

    boletins = Boletim.query.order_by(Boletim.data_boletim.desc(), Boletim.id.desc()).all()
    return render_template(
        'boletins/listagem.html',
        boletins=boletins,
        can_manage=user.has_permissao('boletim_gerenciar'),
        can_search=user.has_permissao('boletim_buscar'),
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
    page = request.args.get('page', 1, type=int)
    per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)

    bind = db.session.get_bind()
    is_postgresql = bool(bind and bind.dialect.name == 'postgresql')
    supports_unaccent = False
    if is_postgresql:
        try:
            supports_unaccent = bool(
                db.session.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname='unaccent'")
                ).scalar()
            )
        except Exception:
            supports_unaccent = False

    def _normalize_for_search(value):
        return strip_accents(re.sub(r'\s+', ' ', value or '').lower())

    if not is_postgresql:
        try:
            db.session.connection().connection.create_function('normalize_search', 1, _normalize_for_search)
        except Exception:
            pass

    def _sql_normalize_whitespace(expression):
        coalesced = func.coalesce(expression, '')
        if is_postgresql:
            return func.regexp_replace(coalesced, r'\s+', ' ', 'g')

        normalized = coalesced
        for char in ('\n', '\r', '\t'):
            normalized = func.replace(normalized, char, ' ')
        return normalized

    def _sql_strip_accents(expression):
        if not is_postgresql:
            return func.normalize_search(expression)

        normalized = func.lower(_sql_normalize_whitespace(expression))
        for accented, plain in (
            ('á', 'a'), ('à', 'a'), ('â', 'a'), ('ã', 'a'), ('ä', 'a'),
            ('é', 'e'), ('è', 'e'), ('ê', 'e'), ('ë', 'e'),
            ('í', 'i'), ('ì', 'i'), ('î', 'i'), ('ï', 'i'),
            ('ó', 'o'), ('ò', 'o'), ('ô', 'o'), ('õ', 'o'), ('ö', 'o'),
            ('ú', 'u'), ('ù', 'u'), ('û', 'u'), ('ü', 'u'),
            ('ç', 'c'),
        ):
            normalized = func.replace(normalized, accented, plain)
        return normalized

    query = Boletim.query
    order_by = [Boletim.data_boletim.desc(), Boletim.created_at.desc()]
    if termo:
        has_wildcard = '%' in termo
        termo_busca = termo if has_wildcard else re.sub(r'\s+', ' ', termo)
        like_normalized = build_like_pattern(strip_accents(termo_busca).lower())
        exact_normalized = strip_accents(re.sub(r'\s+', ' ', termo).lower())
        exact_like_normalized = build_like_pattern(exact_normalized)

        titulo_normalizado = _sql_normalize_whitespace(Boletim.titulo)
        ocr_normalizado = _sql_normalize_whitespace(Boletim.ocr_text)
        titulo_sem_acento = _sql_strip_accents(Boletim.titulo)
        ocr_sem_acento = _sql_strip_accents(Boletim.ocr_text)
        conditions = []
        phrase_tsquery = None
        if is_postgresql and not has_wildcard:
            phrase_tsquery = func.phraseto_tsquery(BOLETIM_FTS_CONFIG, termo_busca)
            conditions.append(_boletim_tsvector_expression().op('@@')(phrase_tsquery))
        conditions.extend([
            titulo_sem_acento.ilike(like_normalized),
            ocr_sem_acento.ilike(like_normalized),
        ])
        if is_postgresql and supports_unaccent:
            conditions.extend([
                func.unaccent(titulo_normalizado).ilike(like_normalized),
                func.unaccent(ocr_normalizado).ilike(like_normalized),
            ])
        query = query.filter(or_(*conditions))

        # Ranking simples: título exato/normalizado, OCR exato/normalizado,
        # match aproximado com %, e por fim boletim mais recente como desempate.
        titulo_exact_match = false() if has_wildcard else titulo_sem_acento.ilike(exact_like_normalized)
        ocr_exact_match = false() if has_wildcard else ocr_sem_acento.ilike(exact_like_normalized)
        titulo_approx_match = titulo_sem_acento.ilike(like_normalized)
        ocr_approx_match = ocr_sem_acento.ilike(like_normalized)
        relevance_score = case(
            (titulo_exact_match, 300),
            (ocr_exact_match, 200),
            (titulo_approx_match, 100),
            (ocr_approx_match, 50),
            else_=0,
        )
        if is_postgresql and phrase_tsquery is not None:
            relevance_score = relevance_score + func.ts_rank_cd(_boletim_tsvector_expression(), phrase_tsquery)

        order_by = [relevance_score.desc(), *order_by]

    pagination = query.order_by(*order_by).paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        'boletins/busca.html',
        boletins=pagination.items,
        termo=termo,
        can_manage=user.has_permissao('boletim_gerenciar'),
        badge_for=_ocr_status_badge,
        pagination=pagination,
        per_page=per_page,
    )


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
