"""Políticas de autorização e escopo de diagramas.

O predicado SQL deste módulo é a fonte única de verdade para descoberta,
consulta individual e entrega de previews.  Assim, um diagrama que não aparece
em uma listagem também não pode ser obtido alterando manualmente a URL.
"""

from sqlalchemy import false, or_

from ...database import db
from ...enums import DiagramScope, DiagramStatus, DiagramType, Permissao
from ...models import (
    ArticleDiagram, Celula, Diagram, Estabelecimento, Instituicao, Setor, User,
)


class DiagramAccessDenied(PermissionError):
    pass


def _is_admin(user):
    return bool(user and user.has_permissao('admin'))


def _has_permission(user, permission):
    code = permission.value if isinstance(permission, Permissao) else permission
    return bool(user and (_is_admin(user) or user.has_permissao(code)))


def _organizational_ids(user):
    """Retorna todos os nós organizacionais aos quais o usuário pertence."""
    cells = list(user.extra_celulas.all())
    if user.celula:
        cells.append(user.celula)
    sectors = list(user.extra_setores.all())
    if user.setor:
        sectors.append(user.setor)
    sectors.extend(cell.setor for cell in cells if cell.setor)

    establishments = [user.estabelecimento] if user.estabelecimento else []
    establishments.extend(cell.estabelecimento for cell in cells if cell.estabelecimento)
    establishments.extend(sector.estabelecimento for sector in sectors if sector.estabelecimento)
    institutions = [item.instituicao for item in establishments if item.instituicao]

    return {
        'cells': {item.id for item in cells},
        'sectors': {item.id for item in sectors},
        'establishments': {item.id for item in establishments},
        'institutions': {item.id for item in institutions},
    }


def visibility_predicate(user):
    """Constrói o predicado SQL completo que concede leitura de diagramas."""
    if not user:
        return false()
    if _is_admin(user):
        return true_predicate()

    ids = _organizational_ids(user)
    rules = [
        Diagram.owner_id == user.id,
        Diagram.shared_users.any(User.id == user.id),
    ]
    if ids['institutions']:
        rules.extend((
            (Diagram.scope == DiagramScope.INSTITUTION) &
            Diagram.instituicao_id.in_(ids['institutions']),
            Diagram.shared_instituicoes.any(Instituicao.id.in_(ids['institutions'])),
        ))
    if ids['establishments']:
        rules.extend((
            (Diagram.scope == DiagramScope.ESTABLISHMENT) &
            Diagram.estabelecimento_id.in_(ids['establishments']),
            Diagram.shared_estabelecimentos.any(Estabelecimento.id.in_(ids['establishments'])),
        ))
    if ids['sectors']:
        rules.extend((
            (Diagram.scope == DiagramScope.SECTOR) & Diagram.setor_id.in_(ids['sectors']),
            Diagram.shared_setores.any(Setor.id.in_(ids['sectors'])),
        ))
    if ids['cells']:
        rules.extend((
            (Diagram.scope == DiagramScope.CELL) & Diagram.celula_id.in_(ids['cells']),
            Diagram.shared_celulas.any(Celula.id.in_(ids['cells'])),
        ))
    return or_(*rules)


def true_predicate():
    """Expressão SQL portável que não restringe administradores."""
    return Diagram.id == Diagram.id


def scoped_diagrams(query, user, *, include_archived=False):
    """Aplica exatamente o predicado usado por consultas individuais."""
    if not _has_permission(user, Permissao.DIAGRAMA_VISUALIZAR):
        return query.filter(false())
    query = query.filter(visibility_predicate(user))
    if not include_archived:
        query = query.filter(Diagram.archived_at.is_(None))
    return query


def can_view_diagram(user, diagram):
    if not user or not diagram or diagram.id is None:
        return False
    if not _has_permission(user, Permissao.DIAGRAMA_VISUALIZAR):
        return False
    if diagram.status == DiagramStatus.ARCHIVED or diagram.archived_at is not None:
        return False
    return db.session.query(Diagram.id).filter(
        Diagram.id == diagram.id, visibility_predicate(user)
    ).first() is not None


def can_create_diagram(user):
    return _has_permission(user, Permissao.DIAGRAMA_CRIAR)


def can_edit_diagram(user, diagram):
    permission = (
        Permissao.DIAGRAMA_MODELO_GERENCIAR
        if diagram and diagram.diagram_type == DiagramType.TEMPLATE
        else Permissao.DIAGRAMA_EDITAR
    )
    return bool(
        diagram and _has_permission(user, permission)
        and (_is_admin(user) or diagram.owner_id == user.id)
    )


def can_archive_diagram(user, diagram):
    return bool(
        diagram and _has_permission(user, Permissao.DIAGRAMA_ARQUIVAR)
        and (_is_admin(user) or diagram.owner_id == user.id)
    )


def can_manage_template(user, diagram=None):
    return bool(
        _has_permission(user, Permissao.DIAGRAMA_MODELO_GERENCIAR)
        and (diagram is None or diagram.diagram_type == DiagramType.TEMPLATE)
    )


def can_render_diagram_in_article(user, diagram, article):
    """Autoriza somente o preview de uma incorporação materializada.

    Esta política é deliberadamente independente de ``can_view_diagram``:
    visualizar um artigo pode liberar sua imagem incorporada, mas nunca a cena,
    os metadados, o histórico ou o editor do diagrama.
    """
    if not (user and diagram and article):
        return False
    if not _has_permission(user, Permissao.DIAGRAMA_RENDERIZAR_ARTIGO):
        return False
    from ...utils import user_can_view_article
    if not user_can_view_article(user, article):
        return False
    return db.session.query(ArticleDiagram.article_id).filter_by(
        article_id=article.id, diagram_id=diagram.id,
    ).first() is not None


# Compatibilidade interna; novos chamadores devem usar os nomes explícitos.
can_view = can_view_diagram
can_edit = can_edit_diagram


def require_view(user, diagram):
    if not can_view_diagram(user, diagram):
        raise DiagramAccessDenied('Diagrama fora do escopo do usuário.')
    return diagram


def require_edit(user, diagram):
    if not can_edit_diagram(user, diagram):
        raise DiagramAccessDenied('Usuário sem permissão para alterar o diagrama.')
    return diagram
