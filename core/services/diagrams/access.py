"""Políticas de autorização e escopo de diagramas."""

from dataclasses import dataclass

from ...models import Diagram


class DiagramAccessDenied(PermissionError):
    pass


def _is_admin(user):
    return bool(user and user.has_permissao('admin'))


def scoped_diagrams(query, user, *, include_archived=False):
    """Aplica o mesmo escopo a listagens HTML e API."""
    if not user:
        return query.filter(False)
    if not _is_admin(user):
        cells = {user.celula_id} if user.celula_id else set()
        cells.update(cell.id for cell in user.extra_celulas.all())
        query = query.filter(
            (Diagram.owner_id == user.id) | (Diagram.celula_id.in_(cells))
        )
    if not include_archived:
        query = query.filter(Diagram.archived_at.is_(None))
    return query


def can_view(user, diagram):
    if not user or not diagram:
        return False
    return (_is_admin(user) or diagram.owner_id == user.id or
            bool(diagram.celula_id and diagram.celula_id in {
                user.celula_id, *(cell.id for cell in user.extra_celulas.all())
            }))


def can_edit(user, diagram):
    return bool(user and diagram and (_is_admin(user) or diagram.owner_id == user.id))


def require_view(user, diagram):
    if not can_view(user, diagram):
        raise DiagramAccessDenied('Diagrama fora do escopo do usuário.')
    return diagram


def require_edit(user, diagram):
    if not can_edit(user, diagram):
        raise DiagramAccessDenied('Usuário sem permissão para alterar o diagrama.')
    return diagram
