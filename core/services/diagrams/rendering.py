"""Leitura de previews e expansão de referências em artigos."""

import re
from uuid import UUID

from markupsafe import Markup, escape

from ...models import Diagram, DiagramAsset
from .access import can_view
from .storage import get_storage


def get_preview(diagram, user, *, storage=None):
    if not can_view(user, diagram):
        raise PermissionError('Preview fora do escopo do usuário.')
    preview = next((asset for asset in reversed(diagram.assets) if asset.kind == 'preview'), None)
    if not preview:
        return None, None
    return (storage or get_storage()).read(preview.storage_key), preview.content_type


def expand_article_references(content, user, *, url_builder=None):
    """Troca marcadores HTML por figuras; referências invisíveis não vazam dados."""
    def replacement(match):
        diagram = Diagram.query.get(UUID(match.group('id')))
        if not can_view(user, diagram):
            return ''
        url = url_builder(diagram) if url_builder else f'/api/diagramas/{diagram.id}/preview'
        return str(Markup('<figure class="article-diagram"><img src="{}" alt="{}"></figure>').format(
            escape(url), escape(diagram.title)))

    pattern = re.compile(r'<(?:div|span)[^>]*data-diagram-id=["\'](?P<id>[0-9a-fA-F-]{36})["\'][^>]*>.*?</(?:div|span)>', re.I | re.S)
    return pattern.sub(replacement, content or '')
