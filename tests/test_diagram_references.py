"""Integração entre placeholders de artigos e diagramas versionados."""

from uuid import uuid4

import pytest

from core.database import db
from core.models import Article, ArticleDiagram, Diagram, Funcao, User
from core.services.diagrams.commands import save_diagram
from core.services.diagrams.references import (
    DiagramReferenceError,
    extract_diagram_ids,
    sync_article_diagrams,
)


def _placeholder(diagram_id):
    return (
        '<p>Processo</p><figure data-article-diagram="true" '
        f'data-diagram-id="{diagram_id}"></figure>'
    )


def test_parser_only_accepts_article_diagram_placeholders():
    valid_id = uuid4()
    unrelated_id = uuid4()
    content = (
        _placeholder(valid_id)
        + f'<div data-diagram-id="{unrelated_id}"></div>'
        + '<figure data-article-diagram="true" data-diagram-id="inválido"></figure>'
    )

    assert extract_diagram_ids(content) == {valid_id}
    assert extract_diagram_ids({
        'type': 'doc',
        'content': [{'type': 'articleDiagram', 'attrs': {'diagramId': str(valid_id)}}],
    }) == {valid_id}


def test_sync_batch_validates_access_before_changing_links(app_ctx):
    owner = User(username='diagram-private', email='private@example.test', password_hash='x')
    outsider = User(username='diagram-outsider', email='outsider@example.test', password_hash='x')
    diagram = Diagram(title='Privado', document={}, owner=owner)
    article = Article(titulo='Artigo', texto='<p>Original</p>', author=outsider)
    db.session.add_all([owner, outsider, diagram, article])
    db.session.commit()

    with pytest.raises(DiagramReferenceError, match='indisponíveis'):
        sync_article_diagrams(article, _placeholder(diagram.id), user=outsider)

    assert ArticleDiagram.query.count() == 0


def test_new_diagram_version_is_shared_by_all_linked_articles_without_article_changes(app_ctx):
    owner = User(username='diagram-shared', email='shared@example.test', password_hash='x')
    owner.permissoes_personalizadas.extend([
        Funcao(codigo='diagrama_visualizar', nome='Visualizar diagramas'),
        Funcao(codigo='diagrama_editar', nome='Editar diagramas'),
    ])
    diagram = Diagram(title='Fluxo', document={'step': 1}, owner=owner)
    first = Article(titulo='Primeiro', texto='<p>temporário</p>', author=owner)
    second = Article(titulo='Segundo', texto='<p>temporário</p>', author=owner)
    db.session.add_all([owner, diagram, first, second])
    db.session.flush()
    first.texto = _placeholder(diagram.id)
    second.texto = _placeholder(diagram.id)
    sync_article_diagrams(first, user=owner)
    sync_article_diagrams(second, user=owner)
    db.session.commit()

    original_articles = {
        article.id: (article.texto, article.updated_at)
        for article in (first, second)
    }
    save_diagram(owner, diagram, document={'step': 2})

    assert diagram.current_version == 2
    assert {
        link.article_id for link in ArticleDiagram.query.filter_by(diagram_id=diagram.id)
    } == {first.id, second.id}
    db.session.expire_all()
    for article_id, original in original_articles.items():
        article = db.session.get(Article, article_id)
        assert (article.texto, article.updated_at) == original
        assert article.diagram_links[0].diagram.current_version == 2
