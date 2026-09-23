"""Comandos transacionais do domínio de diagramas."""

from datetime import datetime, timezone

from ...database import db
from ...models import Diagram, DiagramAsset, DiagramVersion
from ...enums import DiagramStatus
from .access import require_edit, require_view


def _snapshot(diagram, author_id, session):
    version = DiagramVersion(
        diagram=diagram, number=diagram.current_version, title=diagram.title,
        document=diagram.document, author_id=author_id,
    )
    session.add(version)
    return version


def _atomic(operation, session):
    """Executa todas as escritas da operação em uma única transação/commit."""
    try:
        result = operation()
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def create_diagram(user, title, document=None, *, celula_id=None,
                   source_diagram_id=None, assets=(), session=None):
    session = session or db.session
    def operation():
        diagram = Diagram(title=title.strip(), document=document or {}, owner_id=user.id,
                          celula_id=celula_id or user.celula_id,
                          source_diagram_id=source_diagram_id)
        session.add(diagram)
        session.flush()
        _snapshot(diagram, user.id, session)
        for asset in assets:
            session.add(DiagramAsset(diagram=diagram, **asset))
        return diagram
    return _atomic(operation, session)


def save_diagram(user, diagram, *, title=None, document=None, assets=(), session=None):
    session = session or db.session
    require_edit(user, diagram)
    def operation():
        if title is not None:
            diagram.title = title.strip()
        if document is not None:
            diagram.document = document
        diagram.current_version += 1
        _snapshot(diagram, user.id, session)
        for asset in assets:
            session.add(DiagramAsset(diagram=diagram, **asset))
        return diagram
    return _atomic(operation, session)


def copy_template(user, template, *, title=None, session=None):
    require_view(user, template)
    return create_diagram(
        user, title or f'Cópia de {template.title}', template.document,
        celula_id=user.celula_id, source_diagram_id=template.id, session=session,
    )


def restore_diagram(user, diagram, version, *, session=None):
    session = session or db.session
    require_edit(user, diagram)
    if version.diagram_id != diagram.id:
        raise ValueError('A versão não pertence ao diagrama.')
    return save_diagram(user, diagram, title=version.title, document=version.document, session=session)


def archive_diagram(user, diagram, *, session=None):
    session = session or db.session
    require_edit(user, diagram)
    def operation():
        diagram.archived_at = datetime.now(timezone.utc)
        diagram.status = DiagramStatus.ARCHIVED
        diagram.current_version += 1
        _snapshot(diagram, user.id, session)
        return diagram
    return _atomic(operation, session)
