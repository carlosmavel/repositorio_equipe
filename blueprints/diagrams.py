"""Adaptadores HTTP (HTML e API) para diagramas.

Este módulo traduz request/response apenas; políticas e transações permanecem nos
serviços em :mod:`core.services.diagrams`.
"""

from functools import wraps
import hashlib
import json

from flask import Blueprint, abort, jsonify, make_response, redirect, render_template, request, session, url_for

try:
    from ..core.database import db
    from ..core.models import Diagram, DiagramVersion, User
    from ..core.services.diagrams.access import DiagramAccessDenied, require_view, scoped_diagrams
    from ..core.services.diagrams.commands import archive_diagram, copy_template, create_diagram, restore_diagram, save_diagram, save_diagram_payload
    from ..core.services.diagrams.schema import DiagramSchemaError, validate_save_payload
    from ..core.services.diagrams.rendering import get_preview
except ImportError:  # pragma: no cover - execução direta
    from core.database import db
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
    diagrams = scoped_diagrams(Diagram.query, user).order_by(Diagram.updated_at.desc()).all()
    return render_template('diagrams/index.html', diagrams=diagrams)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>')
@authenticated
def diagram_editor(user, diagram_id):
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    return render_template('diagrams/editor.html', diagram=diagram)


@diagrams_bp.get('/api/diagramas')
@authenticated
def api_diagrams(user):
    return jsonify([_serialize(item) for item in scoped_diagrams(Diagram.query, user).all()])


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
