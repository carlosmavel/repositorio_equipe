"""Leitura de previews e resolução segura de referências em artigos."""

import re
from uuid import UUID

from markupsafe import Markup, escape

from ...models import Diagram
from .access import can_render_diagram_in_article, can_view_diagram, require_view
from .metadata import serialize_diagram_metadata
from .storage import get_storage


ARTICLE_DIAGRAM_PATTERN = re.compile(
    r'<figure(?=[^>]*\bdata-article-diagram=["\']true["\'])'
    r'(?=[^>]*\bdata-diagram-id=["\'](?P<id>[0-9a-fA-F-]{36})["\'])'
    r'[^>]*>\s*</figure>',
    re.IGNORECASE,
)


def get_preview(diagram, user, *, version=None, storage=None):
    require_view(user, diagram)
    version = version or diagram.current_version_record
    if not version or version.diagram_id != diagram.id:
        return None, None
    preview = next((asset for asset in version.assets if asset.kind == 'preview'), None)
    if not preview:
        return None, None
    return (storage or get_storage()).read(preview.storage_key), preview.content_type


def resolve_article_diagrams(contents, user, *, article=None, url_builder=None):
    """Resolve vários HTMLs com uma única busca, sem alterar o texto persistido.

    Referências inexistentes ou fora do escopo viram uma mensagem neutra, sem
    expor título, identificador ou qualquer outro metadado do diagrama.
    """
    is_single = isinstance(contents, str) or contents is None
    source_items = [contents or ''] if is_single else [content or '' for content in contents]
    ids = set()
    for content in source_items:
        for match in ARTICLE_DIAGRAM_PATTERN.finditer(content):
            try:
                ids.add(UUID(match.group('id')))
            except ValueError:
                continue

    diagrams = Diagram.query.filter(Diagram.id.in_(ids)).all() if ids else []
    if article is None:
        visible = {diagram.id: diagram for diagram in diagrams if can_view_diagram(user, diagram)}
    else:
        visible = {
            diagram.id: diagram for diagram in diagrams
            if can_render_diagram_in_article(user, diagram, article)
        }

    def resolve_content(content):
        def replacement(match):
            try:
                diagram = visible.get(UUID(match.group('id')))
            except ValueError:
                diagram = None
            if not diagram:
                return '<p class="article-diagram-unavailable">Diagrama indisponível</p>'
            url = url_builder(diagram) if url_builder else f'/api/diagramas/{diagram.id}/preview'
            metadata = serialize_diagram_metadata(
                diagram, user, article=article, preview_url=url,
            )
            return str(Markup(
                '<figure class="article-diagram"><img src="{}" alt="{}" loading="lazy"></figure>'
            ).format(escape(metadata['preview_url']), escape(metadata['title'])))

        return ARTICLE_DIAGRAM_PATTERN.sub(replacement, content)

    resolved = [resolve_content(content) for content in source_items]
    return resolved[0] if is_single else resolved


def expand_article_references(content, user, *, article=None, url_builder=None):
    """Compatibilidade: resolve uma única saída de artigo."""
    return resolve_article_diagrams(content, user, article=article, url_builder=url_builder)
