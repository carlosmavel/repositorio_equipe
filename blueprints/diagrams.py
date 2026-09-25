"""Adaptadores HTTP (HTML e API) para diagramas.

Este módulo traduz request/response apenas; políticas e transações permanecem nos
serviços em :mod:`core.services.diagrams`.
"""

from functools import wraps
import base64
import hashlib
import json
from uuid import UUID

from flask import Blueprint, abort, current_app, jsonify, make_response, redirect, render_template, request, session, url_for
from sqlalchemy import asc, desc

try:
    from ..core.database import db
    from ..core.enums import DiagramScope, DiagramType
    from ..core.models import Article, ArticleDiagram, Diagram, DiagramAsset, DiagramVersion, User
    from ..core.utils import user_can_view_article
    from ..core.services.diagrams.access import (
        DiagramAccessDenied, can_create_diagram, can_edit_diagram, can_render_diagram_in_article, require_view,
        scoped_diagrams,
    )
    from ..core.services.diagrams.commands import DiagramVersionConflict, archive_diagram, copy_template, create_diagram, get_diagram_version_history, restore_diagram, restore_diagram_version, save_diagram, save_diagram_payload
    from ..core.services.diagrams.schema import DiagramSchemaError, validate_save_payload
    from ..core.services.diagrams.rendering import get_preview
    from ..core.services.diagrams.metadata import preview_state, serialize_diagram_metadata
    from ..core.services.diagrams.storage import get_storage
except ImportError:  # pragma: no cover - execução direta
    from core.database import db
    from core.enums import DiagramScope, DiagramType
    from core.models import Article, ArticleDiagram, Diagram, DiagramAsset, DiagramVersion, User
    from core.utils import user_can_view_article
    from core.services.diagrams.access import (
        DiagramAccessDenied, can_create_diagram, can_edit_diagram, can_render_diagram_in_article, require_view,
        scoped_diagrams,
    )
    from core.services.diagrams.commands import DiagramVersionConflict, archive_diagram, copy_template, create_diagram, get_diagram_version_history, restore_diagram, restore_diagram_version, save_diagram, save_diagram_payload
    from core.services.diagrams.schema import DiagramSchemaError, validate_save_payload
    from core.services.diagrams.rendering import get_preview
    from core.services.diagrams.metadata import preview_state, serialize_diagram_metadata
    from core.services.diagrams.storage import get_storage


diagrams_bp = Blueprint('diagrams_bp', __name__)


def feature_enabled(name):
    """Falha fechada para flags desconhecidas e devolve 404 sem revelar rotas."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_app.config.get(name, False):
                abort(404)
            return view(*args, **kwargs)
        return wrapped
    return decorator


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
        'archived_by_user_id': diagram.archived_by_user_id,
    }


def _visible_consumers(diagram, user):
    """Consulta a tabela materializada e não vaza artigos sem acesso."""
    articles = (Article.query.join(ArticleDiagram)
                .filter(ArticleDiagram.diagram_id == diagram.id)
                .order_by(Article.titulo, Article.id).all())
    return [article for article in articles if user_can_view_article(user, article)]


def _consumer_payload(diagram, user):
    visible = _visible_consumers(diagram, user)
    total = ArticleDiagram.query.filter_by(diagram_id=diagram.id).count()
    return {
        'diagram_id': str(diagram.id),
        'total': total,
        'hidden_count': total - len(visible),
        'articles': [{
            'id': article.id,
            'title': article.titulo,
            'url': url_for('articles_bp.artigo', artigo_id=article.id),
        } for article in visible],
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
@feature_enabled('FEATURE_DIAGRAM_LIBRARY')
@authenticated
def biblioteca(user):
    pagination, filters = _diagram_listing(user, diagram_type=DiagramType.DIAGRAM)
    return render_template('diagramas/biblioteca.html', pagination=pagination,
                           diagrams=pagination.items, filters=filters)


@diagrams_bp.get('/diagramas/meus-diagramas')
@feature_enabled('FEATURE_DIAGRAM_LIBRARY')
@authenticated
def meus_diagramas(user):
    pagination, filters = _diagram_listing(
        user, diagram_type=DiagramType.DIAGRAM, mine=True,
    )
    return render_template('diagramas/meus_diagramas.html', pagination=pagination,
                           diagrams=pagination.items, filters=filters,
                           can_create_diagram=can_create_diagram(user))


@diagrams_bp.get('/diagramas/modelos')
@feature_enabled('FEATURE_DIAGRAM_LIBRARY')
@authenticated
def modelos(user):
    pagination, filters = _diagram_listing(user, diagram_type=DiagramType.TEMPLATE)
    return render_template('diagramas/modelos.html', pagination=pagination,
                           diagrams=pagination.items, filters=filters)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>')
@feature_enabled('FEATURE_DIAGRAM_EDITOR')
@authenticated
def diagram_editor(user, diagram_id):
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    return render_template(
        'diagrams/editor.html', diagram=diagram,
        can_edit_diagram=can_edit_diagram(user, diagram),
    )


@diagrams_bp.get('/diagramas/<uuid:diagram_id>/historico')
@feature_enabled('FEATURE_DIAGRAM_EDITOR')
@authenticated
def diagram_history(user, diagram_id):
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    pagination = get_diagram_version_history(
        diagram.id, user, page=max(request.args.get('page', 1, type=int), 1), per_page=20,
    )
    return render_template('diagrams/history.html', diagram=diagram, pagination=pagination)


@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/versoes')
@authenticated
def api_diagram_versions(user, diagram_id):
    pagination = get_diagram_version_history(
        diagram_id, user, page=max(request.args.get('page', 1, type=int), 1),
        per_page=min(max(request.args.get('per_page', 20, type=int), 1), 100),
    )
    return jsonify({
        'items': [{
            'id': str(version.id), 'number': version.number,
            'reason': version.reason, 'author_id': version.author_id,
            'created_at': version.created_at.isoformat(),
            'preview_url': url_for('diagrams_bp.diagram_version_preview',
                                   diagram_id=diagram_id, version_number=version.number),
        } for version in pagination.items],
        'page': pagination.page, 'pages': pagination.pages, 'total': pagination.total,
    })


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/versoes/<uuid:version_id>/restaurar')
@authenticated
def api_restore_diagram_version(user, diagram_id, version_id):
    data = _payload()
    try:
        base_version_id = data.get('base_version_id')
        if not base_version_id:
            raise ValueError('base_version_id é obrigatório.')
        restored = restore_diagram_version(
            diagram_id, version_id, UUID(str(base_version_id)), user,
            data.get('reason') or 'Restauração de versão histórica',
        )
    except DiagramVersionConflict as error:
        return jsonify(error=str(error)), 409
    except (ValueError, TypeError) as error:
        return jsonify(error=str(error)), 400
    return jsonify(version_id=str(restored.id), version_number=restored.number), 201


@diagrams_bp.get('/api/diagramas')
@authenticated
def api_diagrams(user):
    return jsonify([_serialize(item) for item in scoped_diagrams(Diagram.query, user).all()])


@diagrams_bp.get('/api/diagramas/capabilities')
@authenticated
def api_diagram_capabilities(user):
    """Capacidades globais do seletor; ações ainda revalidam acesso no serviço."""
    can_create = can_create_diagram(user)
    can_link = scoped_diagrams(Diagram.query, user).filter(
        Diagram.diagram_type == DiagramType.DIAGRAM
    ).first() is not None
    can_copy = can_create and scoped_diagrams(Diagram.query, user).filter(
        Diagram.diagram_type == DiagramType.TEMPLATE
    ).first() is not None
    return jsonify(
        can_create=can_create,
        can_link=can_link,
        can_copy_template=can_copy,
        create_reason=None if can_create else 'Você não tem permissão para criar diagramas.',
        link_reason=None if can_link else 'Nenhum diagrama comum acessível para vincular.',
        copy_reason=(None if can_copy else
                     ('Você não tem permissão para criar diagramas.' if not can_create
                      else 'Nenhum modelo acessível para copiar.')),
    )


@diagrams_bp.get('/api/diagramas/metadados')
@authenticated
def api_diagram_metadata_list(user):
    query = scoped_diagrams(Diagram.query, user)
    requested_type = request.args.get('tipo', '').strip().lower()
    type_map = {
        'diagrama': DiagramType.DIAGRAM, 'diagram': DiagramType.DIAGRAM,
        'modelo': DiagramType.TEMPLATE, 'template': DiagramType.TEMPLATE,
    }
    if requested_type:
        if requested_type not in type_map:
            return jsonify(error='tipo deve ser diagrama ou modelo.'), 400
        query = query.filter(Diagram.diagram_type == type_map[requested_type])
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(Diagram.name.ilike(f'%{search}%'))
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
    pagination = query.order_by(Diagram.updated_at.desc(), Diagram.id).paginate(
        page=page, per_page=per_page, error_out=False,
    )
    return jsonify(
        items=[_metadata_payload(item, user) for item in pagination.items],
        page=pagination.page, pages=pagination.pages,
        per_page=per_page, total=pagination.total,
    )


def _metadata_payload(diagram, user, *, article=None):
    editable_scene = article is None and can_edit_diagram(user, diagram)
    return serialize_diagram_metadata(
        diagram, user, article=article,
        preview_url=(url_for('diagrams_bp.embedded_diagram_preview',
                             article_id=article.id, diagram_id=diagram.id)
                     if article else
                     url_for('diagrams_bp.api_diagram_preview', diagram_id=diagram.id)),
        view_url=url_for('diagrams_bp.diagram_editor', diagram_id=diagram.id),
        editor_url=url_for('diagrams_bp.diagram_editor', diagram_id=diagram.id),
        scene_url=url_for('diagrams_bp.api_diagram_scene', diagram_id=diagram.id,
                          mode='edit' if editable_scene else None),
        save_url=url_for('diagrams_bp.api_save_diagram', diagram_id=diagram.id),
    )


@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/metadados')
@authenticated
def api_diagram_metadata(user, diagram_id):
    # A mesma resposta cobre UUID inexistente, arquivado e fora do escopo.
    diagram = scoped_diagrams(Diagram.query, user).filter(Diagram.id == diagram_id).first_or_404()
    response = jsonify(_metadata_payload(diagram, user))
    response.set_etag(str(diagram.current_version_id or diagram.current_version))
    return response.make_conditional(request)


@diagrams_bp.get('/api/artigos/<int:article_id>/diagramas/<uuid:diagram_id>/metadados')
@authenticated
def api_embedded_diagram_metadata(user, article_id, diagram_id):
    """Entrega somente capacidades e preview raster do contexto do artigo."""
    article = db.session.get(Article, article_id)
    diagram = db.session.get(Diagram, diagram_id)
    if not can_render_diagram_in_article(user, diagram, article):
        abort(404)
    response = jsonify(_metadata_payload(diagram, user, article=article))
    response.set_etag(str(diagram.current_version_id or diagram.current_version))
    return response.make_conditional(request)


@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/cena')
@authenticated
def api_diagram_scene(user, diagram_id):
    """Entrega a cena editável e os BinaryFiles somente a usuários autorizados."""
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    # A capacidade é reavaliada no instante do carregamento. Isso fecha a
    # janela entre a consulta de metadados e a montagem de um editor editável.
    if request.args.get('mode') == 'edit' and not can_edit_diagram(user, diagram):
        raise DiagramAccessDenied('Usuário sem permissão para editar o diagrama.')
    document = diagram.document if isinstance(diagram.document, dict) else {}
    descriptors = document.get('files', {})
    assets = {
        asset.sha256: asset for asset in (
            diagram.current_version_record.assets if diagram.current_version_record else []
        ) if asset.kind == 'asset'
    }
    files = {}
    for file_id, descriptor in descriptors.items():
        asset = assets.get(descriptor.get('sha256'))
        if not asset:
            continue
        content_type = descriptor.get('mimeType') or asset.content_type or 'application/octet-stream'
        encoded = base64.b64encode(get_storage().read(asset.storage_key)).decode('ascii')
        files[file_id] = {
            'id': file_id,
            'mimeType': content_type,
            'dataURL': f'data:{content_type};base64,{encoded}',
            'created': int(asset.created_at.timestamp() * 1000) if asset.created_at else 0,
        }
    response = jsonify(
        elements=document.get('elements', []),
        appState=document.get('appState', {}),
        files=files,
    )
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@diagrams_bp.post('/api/diagramas')
@authenticated
def api_create_diagram(user):
    data = _payload()
    title = str(data.get('title', '')).strip()
    if not title:
        return jsonify(error='title é obrigatório.'), 400
    if len(title) > 200:
        return jsonify(error='title deve ter no máximo 200 caracteres.'), 400
    diagram = create_diagram(user, title, data.get('document'), celula_id=data.get('celula_id'))
    return jsonify({**_serialize(diagram), **_metadata_payload(diagram, user)}), 201


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
    metadata = _metadata_payload(diagram, user)
    return jsonify({
        **_serialize(diagram),
        'preview_state': metadata['preview_state'],
        'preview_url': metadata['preview_url'],
        'preview_token': metadata['cache_token'],
    })


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/copiar')
@authenticated
def api_copy_diagram(user, diagram_id):
    diagram = copy_template(user, db.get_or_404(Diagram, diagram_id), title=_payload().get('title'))
    return jsonify({**_serialize(diagram), **_metadata_payload(diagram, user)}), 201


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/restaurar/<int:version_number>')
@authenticated
def api_restore_diagram(user, diagram_id, version_number):
    diagram = db.get_or_404(Diagram, diagram_id)
    version = DiagramVersion.query.filter_by(diagram_id=diagram.id, number=version_number).first_or_404()
    return jsonify(_serialize(restore_diagram(user, diagram, version)))


@diagrams_bp.post('/api/diagramas/<uuid:diagram_id>/arquivar')
@diagrams_bp.delete('/api/diagramas/<uuid:diagram_id>')
@authenticated
def api_archive_diagram(user, diagram_id):
    diagram = db.get_or_404(Diagram, diagram_id)
    consumers = _consumer_payload(diagram, user)
    # Obriga clientes a exibirem o impacto antes da operação destrutiva.
    confirmation = request.values.get('confirm_consumers')
    if request.is_json:
        confirmation = str((request.get_json(silent=True) or {}).get('confirm_consumers')).lower()
    if consumers['total'] and confirmation != 'true':
        return jsonify(error='Confirme os artigos consumidores antes de arquivar.',
                       used_in=consumers), 409
    return jsonify(_serialize(archive_diagram(user, diagram)))


@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/usado-em')
@authenticated
def api_diagram_used_in(user, diagram_id):
    diagram = require_view(user, db.get_or_404(Diagram, diagram_id))
    return jsonify(_consumer_payload(diagram, user))


@diagrams_bp.delete('/api/diagramas/<uuid:diagram_id>/excluir-definitivo')
@authenticated
def api_delete_diagram(user, diagram_id):
    """Hard delete excepcional; referências e retenção sempre prevalecem."""
    if not user.has_permissao('admin'):
        raise DiagramAccessDenied('A exclusão definitiva exige administração.')
    diagram = db.get_or_404(Diagram, diagram_id)
    consumers = _consumer_payload(diagram, user)
    if consumers['total']:
        return jsonify(
            error='O diagrama é referenciado por artigos e não pode ser excluído.',
            used_in=consumers,
        ), 409
    retained_versions = DiagramVersion.query.filter_by(diagram_id=diagram.id).count()
    retained_assets = DiagramAsset.query.filter_by(diagram_id=diagram.id).count()
    if retained_versions or retained_assets:
        return jsonify(
            error='Versões ou assets ainda estão sujeitos à política de retenção.',
            retained_versions=retained_versions,
            retained_assets=retained_assets,
        ), 409
    db.session.delete(diagram)
    db.session.commit()
    return '', 204


def _preview_response(diagram, user, version=None):
    content, content_type = get_preview(diagram, user, version=version)
    preview_available = content is not None
    if not preview_available:
        state = (getattr(version, 'preview_state', 'failed') if version is not None
                 else preview_state(diagram))
        label = 'Preview indisponivel' if state == 'failed' else 'Gerando preview...'
        content = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" '
            b'viewBox="0 0 640 360"><rect width="640" height="360" fill="#f1f3f5"/>'
            b'<text x="320" y="180" text-anchor="middle" fill="#6c757d" '
            b'font-family="sans-serif" font-size="20">' + label.encode('ascii') + b'</text></svg>'
        )
        content_type = 'image/svg+xml; charset=utf-8'
    response = make_response(content)
    response.headers['Content-Type'] = content_type or 'image/png'
    # A ausência do preview é transitória (por exemplo, antes do primeiro
    # salvamento no editor) e não pode ficar presa no cache do navegador.
    # A URL da versão corrente é estável, embora seu conteúdo mude a cada
    # salvamento. Exija revalidação para não exibir por até cinco minutos o
    # preview anterior; versões históricas, por outro lado, são imutáveis.
    response.headers['Cache-Control'] = (
        ('private, max-age=300' if version is not None else 'private, no-cache')
        if preview_available else 'private, no-store'
    )
    response.set_etag(hashlib.sha256(content).hexdigest())
    return response.make_conditional(request)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>/preview')
@diagrams_bp.get('/api/diagramas/<uuid:diagram_id>/preview')
@authenticated
def api_diagram_preview(user, diagram_id):
    return _preview_response(db.get_or_404(Diagram, diagram_id), user)


@diagrams_bp.get('/artigos/<int:article_id>/diagramas/<uuid:diagram_id>/preview')
@authenticated
def embedded_diagram_preview(user, article_id, diagram_id):
    """Entrega somente a imagem vinculada ao artigo, nunca a cena editável."""
    article = db.get_or_404(Article, article_id)
    diagram = db.get_or_404(Diagram, diagram_id)
    if not can_render_diagram_in_article(user, diagram, article):
        raise DiagramAccessDenied('Incorporação indisponível para este usuário.')
    version = diagram.current_version_record
    if not version:
        abort(404)
    preview = next((asset for asset in version.assets if asset.kind == 'preview'), None)
    if not preview:
        abort(404)
    content = get_storage().read(preview.storage_key)
    response = make_response(content)
    response.headers['Content-Type'] = preview.content_type or 'image/png'
    # Este endpoint representa sempre a versão corrente do diagrama.
    response.headers['Cache-Control'] = 'private, no-cache'
    response.set_etag(hashlib.sha256(content).hexdigest())
    return response.make_conditional(request)


@diagrams_bp.get('/diagramas/<uuid:diagram_id>/versoes/<int:version_number>/preview')
@authenticated
def diagram_version_preview(user, diagram_id, version_number):
    diagram = db.get_or_404(Diagram, diagram_id)
    version = DiagramVersion.query.filter_by(
        diagram_id=diagram.id, version_number=version_number
    ).first_or_404()
    return _preview_response(diagram, user, version)
