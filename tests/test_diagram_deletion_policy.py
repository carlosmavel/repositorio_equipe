"""Matriz de integridade das operações destrutivas de diagramas."""

from sqlalchemy.exc import IntegrityError
import pytest

from core.database import db
from core.enums import DiagramStatus, DiagramType
from core.models import Article, ArticleDiagram, Diagram, DiagramAsset, DiagramVersion, Funcao, User
from core.services.diagrams.commands import archive_diagram


def _user(name, *permissions):
    user = User(username=name, email=f'{name}@example.test', password_hash='x')
    user.permissoes_personalizadas.extend(Funcao(codigo=p, nome=p) for p in permissions)
    return user


def _enable_foreign_keys():
    db.session.execute(db.text('PRAGMA foreign_keys=ON'))


@pytest.fixture(autouse=True)
def _restore_sqlite_fk_setting(app_ctx):
    yield
    db.session.rollback()
    db.session.execute(db.text('PRAGMA foreign_keys=OFF'))


def test_archive_is_normal_delete_and_records_actor(app_ctx):
    owner = _user('archive-owner', 'diagrama_arquivar')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    db.session.add_all([owner, diagram])
    db.session.commit()

    archive_diagram(owner, diagram)

    assert diagram.status is DiagramStatus.ARCHIVED
    assert diagram.archived_at is not None
    assert diagram.archived_by_user_id == owner.id


def test_deleted_article_removes_only_link(app_ctx):
    owner = _user('article-owner')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    article = Article(titulo='Consumidor', texto='', author=owner)
    db.session.add_all([owner, diagram, article])
    db.session.flush()
    db.session.add(ArticleDiagram(article_id=article.id, diagram_id=diagram.id))
    db.session.commit()
    _enable_foreign_keys()

    db.session.delete(article)
    db.session.commit()

    assert db.session.get(Diagram, diagram.id) is not None
    assert ArticleDiagram.query.count() == 0


def test_referenced_diagram_cannot_be_hard_deleted(app_ctx):
    owner = _user('referenced-owner')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    article = Article(titulo='Consumidor', texto='', author=owner)
    db.session.add_all([owner, diagram, article])
    db.session.flush()
    db.session.add(ArticleDiagram(article_id=article.id, diagram_id=diagram.id))
    db.session.commit()
    _enable_foreign_keys()

    db.session.delete(diagram)
    try:
        db.session.commit()
        assert False, 'a FK deveria impedir a exclusão'
    except IntegrityError:
        db.session.rollback()


def test_deleted_template_does_not_delete_copy(app_ctx):
    owner = _user('template-owner')
    template = Diagram(title='Modelo', document={}, owner=owner, diagram_type=DiagramType.TEMPLATE)
    copy = Diagram(title='Cópia', document={}, owner=owner, source_template=template)
    db.session.add_all([owner, template, copy])
    db.session.commit()
    _enable_foreign_keys()
    copy_id = copy.id

    db.session.delete(template)
    db.session.commit()

    assert db.session.get(Diagram, copy_id) is not None
    assert db.session.get(Diagram, copy_id).source_template_id is None


def test_user_delete_cannot_delete_owned_diagrams(app_ctx):
    owner = _user('retained-owner')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    db.session.add_all([owner, diagram])
    db.session.commit()
    _enable_foreign_keys()

    db.session.delete(owner)
    try:
        db.session.commit()
        assert False, 'a FK deveria impedir a exclusão'
    except IntegrityError:
        db.session.rollback()
    assert db.session.get(Diagram, diagram.id) is not None


def test_versions_and_assets_block_hard_delete_during_retention(app_ctx):
    owner = _user('history-owner')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    version = DiagramVersion(diagram=diagram, number=1, title='Fluxo', document={}, author=owner)
    asset = DiagramAsset(diagram=diagram, storage_key='sha256/retained')
    db.session.add_all([owner, diagram, version, asset])
    db.session.commit()
    _enable_foreign_keys()

    db.session.delete(diagram)
    try:
        db.session.commit()
        assert False, 'a retenção deveria impedir a exclusão'
    except IntegrityError:
        db.session.rollback()
    assert db.session.get(DiagramVersion, version.id) is not None
    assert db.session.get(DiagramAsset, asset.id) is not None


def test_used_in_only_returns_articles_visible_to_user(client):
    owner = _user('visible-owner', 'diagrama_visualizar', 'diagrama_arquivar')
    outsider = _user('hidden-owner')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    visible = Article(titulo='Artigo visível', texto='', author=owner)
    hidden = Article(titulo='Artigo sigiloso', texto='', author=outsider)
    db.session.add_all([owner, outsider, diagram, visible, hidden])
    db.session.flush()
    db.session.add_all([
        ArticleDiagram(article_id=visible.id, diagram_id=diagram.id),
        ArticleDiagram(article_id=hidden.id, diagram_id=diagram.id),
    ])
    db.session.commit()
    with client.session_transaction() as session:
        session['user_id'] = owner.id

    response = client.get(f'/api/diagramas/{diagram.id}/usado-em')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['total'] == 2
    assert payload['hidden_count'] == 1
    assert [item['title'] for item in payload['articles']] == ['Artigo visível']


def test_archive_requires_consumer_confirmation(client):
    owner = _user('confirm-owner', 'diagrama_visualizar', 'diagrama_arquivar')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    article = Article(titulo='Consumidor', texto='', author=owner)
    db.session.add_all([owner, diagram, article])
    db.session.flush()
    db.session.add(ArticleDiagram(article_id=article.id, diagram_id=diagram.id))
    db.session.commit()
    with client.session_transaction() as session:
        session['user_id'] = owner.id

    warning = client.post(f'/api/diagramas/{diagram.id}/arquivar')
    confirmed = client.post(
        f'/api/diagramas/{diagram.id}/arquivar', data={'confirm_consumers': 'true'},
    )

    assert warning.status_code == 409
    assert warning.get_json()['used_in']['total'] == 1
    assert confirmed.status_code == 200
    assert confirmed.get_json()['archived_by_user_id'] == owner.id


def test_normal_delete_archives_instead_of_removing(client):
    owner = _user('delete-owner', 'diagrama_visualizar', 'diagrama_arquivar')
    diagram = Diagram(title='Fluxo', document={}, owner=owner)
    db.session.add_all([owner, diagram])
    db.session.commit()
    diagram_id = diagram.id
    with client.session_transaction() as session:
        session['user_id'] = owner.id

    response = client.delete(f'/api/diagramas/{diagram_id}')

    assert response.status_code == 200
    assert response.get_json()['archived'] is True
    assert db.session.get(Diagram, diagram_id) is not None
