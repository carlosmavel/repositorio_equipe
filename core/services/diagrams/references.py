"""Extração e sincronização de nós ``articleDiagram``."""

import json
import re
from uuid import UUID

from ...database import db
from ...models import ArticleDiagram

_HTML_REFERENCE = re.compile(
    r'(?:data-diagram-id|diagram-id)=["\'](?P<id>[0-9a-fA-F-]{36})["\']', re.I
)


def extract_diagram_ids(content):
    """Aceita HTML, JSON serializado ou a árvore JSON do editor Tiptap."""
    found = set()
    if isinstance(content, str):
        found.update(UUID(match.group('id')) for match in _HTML_REFERENCE.finditer(content))
        try:
            content = json.loads(content)
        except (TypeError, ValueError):
            return found
    if isinstance(content, dict):
        if content.get('type') == 'articleDiagram':
            value = (content.get('attrs') or {}).get('diagramId')
            if value is not None and value:
                try:
                    found.add(UUID(str(value)))
                except (TypeError, ValueError):
                    pass
        for value in content.values():
            found.update(extract_diagram_ids(value))
    elif isinstance(content, list):
        for value in content:
            found.update(extract_diagram_ids(value))
    return found


def sync_article_diagrams(article, content=None, *, session=None):
    """Sincroniza vínculos sem fazer commit; o chamador controla a transação."""
    session = session or db.session
    wanted = extract_diagram_ids(article.texto if content is None else content)
    current = {link.diagram_id: link for link in article_diagram_links(article.id, session)}
    for removed in set(current) - wanted:
        session.delete(current[removed])
    for added in wanted - set(current):
        session.add(ArticleDiagram(article_id=article.id, diagram_id=added))
    return wanted


def article_diagram_links(article_id, session=None):
    session = session or db.session
    return session.query(ArticleDiagram).filter_by(article_id=article_id).all()
