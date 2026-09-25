"""Extração, validação e materialização de ``articleDiagram``."""

import json
from uuid import UUID

from ...database import db
from ...models import ArticleDiagram, Diagram
from .access import scoped_diagrams
from .rendering import ARTICLE_DIAGRAM_PATTERN


class DiagramReferenceError(ValueError):
    """Uma ou mais referências não podem ser vinculadas ao artigo."""


def _uuid(value):
    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return None


def extract_diagram_ids(content):
    """Extrai IDs somente de placeholders ``articleDiagram`` válidos.

    Aceita o HTML persistido pelo editor, JSON serializado ou a árvore JSON do
    Tiptap. IDs repetidos são naturalmente eliminados.
    """
    found = set()
    if isinstance(content, str):
        for match in ARTICLE_DIAGRAM_PATTERN.finditer(content):
            diagram_id = _uuid(match.group('id'))
            if diagram_id is not None:
                found.add(diagram_id)
        try:
            content = json.loads(content)
        except (TypeError, ValueError):
            return found
    if isinstance(content, dict):
        if content.get('type') == 'articleDiagram':
            diagram_id = _uuid((content.get('attrs') or {}).get('diagramId'))
            if diagram_id is not None:
                found.add(diagram_id)
        for value in content.values():
            found.update(extract_diagram_ids(value))
    elif isinstance(content, list):
        for value in content:
            found.update(extract_diagram_ids(value))
    return found


def validate_diagram_references(diagram_ids, user, *, session=None):
    """Valida existência e autorização de todos os IDs em uma só consulta.

    A mensagem é deliberadamente indistinguível para IDs inexistentes e fora
    do escopo, evitando revelar a existência de diagramas privados.
    """
    session = session or db.session
    wanted = set(diagram_ids)
    if not wanted:
        return {}
    query = scoped_diagrams(session.query(Diagram), user)
    diagrams = query.filter(Diagram.id.in_(wanted)).all()
    allowed = {diagram.id: diagram for diagram in diagrams}
    if set(allowed) != wanted:
        raise DiagramReferenceError(
            'Um ou mais diagramas estão indisponíveis ou fora do seu escopo.'
        )
    return allowed


def sync_article_diagrams(article, content=None, *, user, session=None):
    """Valida e sincroniza vínculos sem commit; o chamador controla a transação."""
    session = session or db.session
    wanted = extract_diagram_ids(article.texto if content is None else content)
    validate_diagram_references(wanted, user, session=session)
    current = {link.diagram_id: link for link in article_diagram_links(article.id, session)}
    for removed in set(current) - wanted:
        session.delete(current[removed])
    for added in wanted - set(current):
        session.add(ArticleDiagram(article_id=article.id, diagram_id=added))
    return wanted


def article_diagram_links(article_id, session=None):
    session = session or db.session
    return session.query(ArticleDiagram).filter_by(article_id=article_id).all()
