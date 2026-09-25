"""Políticas de acesso de diagramas, inclusive incorporações em artigos."""

from core.database import db
from core.models import Article, ArticleDiagram, Diagram, Funcao, User
from core.services.diagrams.access import (
    can_archive_diagram, can_create_diagram, can_edit_diagram,
    can_render_diagram_in_article, can_view_diagram, scoped_diagrams,
)


def _user(name, *permissions):
    user = User(username=name, email=f'{name}@example.test', password_hash='x')
    user.permissoes_personalizadas.extend(
        Funcao(codigo=code, nome=code) for code in permissions
    )
    return user


def test_action_permissions_are_independent(app_ctx):
    owner = _user('action-owner', 'diagrama_visualizar', 'diagrama_editar')
    diagram = Diagram(title='Privado', document={}, owner=owner)
    db.session.add_all([owner, diagram])
    db.session.commit()

    assert can_view_diagram(owner, diagram)
    assert can_edit_diagram(owner, diagram)
    assert not can_create_diagram(owner)
    assert not can_archive_diagram(owner, diagram)


def test_embedded_view_only_releases_linked_preview_policy(app_ctx):
    owner = _user('embedded-owner')
    reader = _user('embedded-reader', 'diagrama_renderizar_artigo')
    diagram = Diagram(title='Segredo', document={'editable': True}, owner=owner)
    article = Article(titulo='Visível', texto='', author=reader)
    db.session.add_all([owner, reader, diagram, article])
    db.session.flush()
    db.session.add(ArticleDiagram(article_id=article.id, diagram_id=diagram.id))
    db.session.commit()

    assert can_render_diagram_in_article(reader, diagram, article)
    assert not can_view_diagram(reader, diagram)
    assert scoped_diagrams(Diagram.query, reader).all() == []
    assert not can_edit_diagram(reader, diagram)


def test_embedded_view_requires_materialized_link(app_ctx):
    owner = _user('unlinked-owner')
    reader = _user('unlinked-reader', 'diagrama_renderizar_artigo')
    diagram = Diagram(title='Não vinculado', document={}, owner=owner)
    article = Article(titulo='Visível', texto='', author=reader)
    db.session.add_all([owner, reader, diagram, article])
    db.session.commit()

    assert not can_render_diagram_in_article(reader, diagram, article)
