"""Contrato único de metadados e capacidades de diagramas."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .access import can_edit_diagram, can_render_diagram_in_article, can_view_diagram


def _versioned_url(url, token):
    if not url or not token:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query['v'] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def preview_state(diagram):
    """Descreve o preview corrente sem consultar ou entregar seu conteúdo."""
    version = getattr(diagram, 'current_version_record', None)
    if not version:
        return 'pending'
    # Um registro nunca pode declarar ``ready`` sem o asset confirmado.
    if any(asset.kind == 'preview' for asset in version.assets):
        return 'ready'
    state = getattr(version, 'preview_state', None)
    return state if state in {'pending', 'generating', 'failed'} else 'failed'


def serialize_diagram_metadata(diagram, user, *, article=None, preview_url=None,
                               view_url=None, editor_url=None, scene_url=None,
                               save_url=None):
    """Serializa o contrato sem promover acesso contextual a acesso direto."""
    # O contexto do artigo pode conceder somente o raster. Uma permissão direta
    # que o usuário já possua, porém, não deve ser descartada nesse contexto.
    direct_view = can_view_diagram(user, diagram)
    contextual_view = (
        can_render_diagram_in_article(user, diagram, article)
        if article is not None else False
    )
    can_view = direct_view or contextual_view
    can_edit = direct_view and can_edit_diagram(user, diagram)
    can_open_scene = direct_view
    token = str(diagram.current_version_id or diagram.current_version)
    payload = {
        'id': str(diagram.id), 'title': diagram.title,
        'diagram_type': diagram.diagram_type.value,
        'current_version': diagram.current_version,
        'lock_version': diagram.lock_version,
        'current_version_id': str(diagram.current_version_id) if diagram.current_version_id else None,
        'cache_token': token,
        'preview_state': preview_state(diagram),
        'preview_message': (
            'Preview indisponível.' if preview_state(diagram) == 'failed' else None
        ),
        'preview_url': _versioned_url(preview_url, token) if can_view else None,
        'can_view': can_view, 'can_edit': can_edit, 'can_open_scene': can_open_scene,
        'capabilities': {
            'can_view': can_view, 'can_edit': can_edit,
            'can_open_scene': can_open_scene,
        },
    }
    if direct_view and view_url:
        payload['view_url'] = view_url
    if can_edit and editor_url:
        payload['editor_url'] = editor_url
    if can_open_scene and scene_url:
        payload['scene_url'] = _versioned_url(scene_url, token)
    if can_edit and save_url:
        payload['save_url'] = save_url
    return payload
