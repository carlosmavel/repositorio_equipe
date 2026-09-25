"""Adaptadores HTTP (HTML e API) para diagramas.

Este módulo traduz request/response apenas; políticas e transações permanecem nos
serviços em :mod:`core.services.diagrams`.
"""

from functools import wraps
import hashlib
import json

from flask import Blueprint, abort, jsonify, make_response, redirect, render_template, request, session, url_for
from sqlalchemy import asc, desc

try:
    from ..core.database import db
    from ..core.enums import DiagramScope, DiagramType
    from ..core.models import Diagram, DiagramVersion, User
    from ..core.services.diagrams.access import DiagramAccessDenied, require_view, scoped_diagrams
    from ..core.services.diagrams.commands import archive_diagram, copy_template, create_diagram, restore_diagram, save_diagram, save_diagram_payload
    from ..core.services.diagrams.schema import DiagramSchemaError, validate_save_payload
    from ..core.services.diagrams.rendering import get_preview
except ImportError:  # pragma: no cover - execução direta
    from core.database import db
    from core.enums import DiagramScope, DiagramType
    from core.models import Diagram, DiagramVersion, User
    from core.services.diagrams.access import DiagramAccessDenied, require_view, scoped_diagrams
    from core.services.diagrams.commands import archive_diagram, copy_template, create_diagram, restore_diagram, save_diagram, save_diagram_payload
    from core.services.diagrams.schema import DiagramSchemaError, validate_save_payload
    from core.services.diagrams.rendering import get_preview


diagrams_bp = Blueprint('diagrams_bp', __name__)


def authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
        if not user:
            if request.path.startswith('/api/'):
                return jsonify(error='Autenticação necessária.'), 401
            return redirect(url_for('login', next=request.url))
        return view(user, *args, **kwargs)
    return wrapped


def _payload():
    return request.get_json(silent=True) or request.form.to_dict()


def _serialize(diagram):
    return {
        'id': str(diagram.id), 'title': diagram.title, 'document': diagram.document,
        'owner_id': diagram.owner_id, 'celula_id': diagram.celula_id,
        'current_version': diagram.current_version,
        'current_version_id': str(diagram.current_version_id) if diagram.current_version_id else None,
        'lock_version': diagram.lock_version,
        'archived': diagram.archived_at is not None,
    }


@diagrams_bp.errorhandler(DiagramAccessDenied)
def access_denied(error):
    if request.path.startswith('/api/'):
        return jsonify(error=str(error)), 403
    abort(403, description=str(error))


@diagrams_bp.get('/diagramas')
@authenticated
def diagrams_index(user):
    return redirect(url_for('diagrams_bp.biblioteca'))


def _diagram_listing(user, *, diagram_type, mine=False):
    """Filtra, ordena e pagina no banco uma coleção de diagramas."""
    query = scoped_diagrams(Diagram.query, user).filter(Diagram.diagram_type == diagram_type)
    if mine:
        query = query.filter(Diagram.owner_id == user.id)

    search = request.args.get('q', '').strip()
    selected_scope = request.args.get('escopo', '').strip()
    selected_order = request.args.get('ordem', 'recentes').strip()
    if search:
        query = query.filter(Diagram.name.ilike(f'%{search}%'))
    valid_scopes = {scope.value for scope in DiagramScope}
    if selected_scope in valid_scopes:
        query = query.filter(Diagram.scope == DiagramScope(selected_scope))
    else:
        selected_scope = ''

    ordering = {
        'nome': (asc(Diagram.name), asc(Diagram.id)),
        'antigos': (asc(Diagram.updated_at), asc(Diagram.id)),
        'recentes': (desc(Diagram.updated_at), desc(Diagram.id)),
    }
    if selected_order not in ordering:
        selected_order = 'recentes'
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 12, type=int), 1), 48)
    pagination = query.order_by(*ordering[selected_order]).paginate(
        page=page, per_page=per_page, error_out=False,
    )
    return pagination, {
        'q': search,
        'escopo': selected_scope,
        'ordem': selected_order,
        'per_page': per_page,
    }


@diagrams_bp.get('/diagramas/biblioteca')
@authenticated
def biblioteca(user):
    pagination, filters = _diagram_listing(user, diagram_type=DiagramType.DIAGRAM)
    return render_template('diagramas/biblioteca.html', pagination=pagination,
                           diagrams=pagination.items, filters=filters)


@diagrams_bp.get('/diagramas/meus-diagramas')
@authenticated
def meus_diagramas(user):
    pagination, filters = _diagram_listing(
        user, diagram_type=DiagramType.DIAGRAM, mine=True,
    )
    return render_template('diagramas/meus_diagramas.html', pagination=pagination,
                           diagrams=pagination.items, filters=filters)


@diagrams_bp.get('/diagramas/modelos')
@authenticated
def modelos(user):
    pagination, filters = _diagram_listing(user, diagram_type=DiagramType.TEMPLATE)
    return render_template('diagramas/modelos.html', pagination=pagination,
                           diagrams=pagination.items, filters=filters)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>')
@authenticated
def diagram_editor(user, diagram_id):
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    return render_template('diagrams/editor.html', diagram=diagram)


@diagrams_bp.get('/api/diagramas')
@authenticated
def api_diagrams(user):
    return jsonify([_serialize(item) for item in scoped_diagrams(Diagram.query, user).all()])


@diagrams_bp.get('/api/diagramas/metadados')
@authenticated
def api_diagram_metadata_list(user):
    query = scoped_diagrams(Diagram.query, user)
    requested_type = request.args.get('tipo')
    if requested_type == 'modelo':
        query = query.filter(Diagram.diagram_type == 'template')
    return jsonify([{
        'id': str(item.id),
        'title': item.title,
        'diagram_type': item.diagram_type.value,
        'preview_url': url_for('diagrams_bp.api_diagram_preview', diagram_id=item.id),
    } for item in query.order_by(Diagram.updated_at.desc()).all()])


@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/metadados')
@authenticated
def api_diagram_metadata(user, diagram_id):
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    return jsonify({
        'id': str(diagram.id),
        'title': diagram.title,
        'preview_url': url_for('diagrams_bp.api_diagram_preview', diagram_id=diagram.id),
    })


@diagrams_bp.post('/api/diagramas')
@authenticated
def api_create_diagram(user):
    data = _payload()
    if not str(data.get('title', '')).strip():
        return jsonify(error='title é obrigatório.'), 400
    diagram = create_diagram(user, data['title'], data.get('document'), celula_id=data.get('celula_id'))
    return jsonify(_serialize(diagram)), 201


@diagrams_bp.put('/api/diagramas/<uuid:diagram_id>')
@authenticated
def api_save_diagram(user, diagram_id):
    diagram = db.get_or_404(Diagram, diagram_id)
    try:
        if request.mimetype == 'multipart/form-data':
            data = json.loads(request.form.get('payload', ''))
            uploads = request.files.to_dict()
            preview = uploads.pop('preview', None)
        else:
            data = request.get_json(silent=False)
            uploads = {}
            preview = None
        payload = validate_save_payload(data, uploads, preview=preview)
        diagram = save_diagram_payload(user, diagram, payload, title=data.get('title'))
    except (DiagramSchemaError, json.JSONDecodeError) as error:
        return jsonify(error=str(error)), 400
    except ValueError as error:
        status = 409 if 'outra sessão' in str(error) else 400
        return jsonify(error=str(error)), status
    return jsonify(_serialize(diagram))


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/copiar')
@authenticated
def api_copy_diagram(user, diagram_id):
    diagram = copy_template(user, db.get_or_404(Diagram, diagram_id), title=_payload().get('title'))
    return jsonify(_serialize(diagram)), 201


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/restaurar/<int:version_number>')
@authenticated
def api_restore_diagram(user, diagram_id, version_number):
    diagram = db.get_or_404(Diagram, diagram_id)
    version = DiagramVersion.query.filter_by(diagram_id=diagram.id, number=version_number).first_or_404()
    return jsonify(_serialize(restore_diagram(user, diagram, version)))


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/arquivar')
@authenticated
def api_archive_diagram(user, diagram_id):
    return jsonify(_serialize(archive_diagram(user, db.get_or_404(Diagram, diagram_id))))


def _preview_response(diagram, user, version=None):
    content, content_type = get_preview(diagram, user, version=version)
    if content is None:
        abort(404)
    response = make_response(content)
    response.headers['Content-Type'] = content_type or 'image/png'
    response.headers['Cache-Control'] = 'private, max-age=300'
    response.set_etag(hashlib.sha256(content).hexdigest())
    return response.make_conditional(request)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>/preview')
@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/preview')
@authenticated
def api_diagram_preview(user, diagram_id):
    return _preview_response(db.get_or_404(Diagram, diagram_id), user)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>/versoes/<int:version_number>/preview')
@authenticated
def diagram_version_preview(user, diagram_id, version_number):
    diagram = db.get_or_404(Diagram, diagram_id)
    version = DiagramVersion.query.filter_by(
        diagram_id=diagram.id, version_number=version_number
    ).first_or_404()
    return _preview_response(diagram, user, version)
