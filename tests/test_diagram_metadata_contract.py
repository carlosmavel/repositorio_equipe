"""Contrato HTTP único de metadados e capacidades."""

from datetime import datetime, timezone
import uuid

from core.database import db
from core.enums import DiagramType
from core.models import Article, ArticleDiagram, Diagram, Funcao, User


def _user(name, *permissions):
    user = User(username=name, email=f'{name}@example.test', password_hash='x')
    user.permissoes_personalizadas.extend(
        Funcao(codigo=code, nome=code) for code in permissions
    )
    return user


def _login(client, user):
    with client.session_transaction() as session:
        session['user_id'] = user.id


def test_owner_and_shared_reader_receive_only_their_capabilities(client):
    owner = _user('metadata-owner', 'diagrama_visualizar', 'diagrama_editar')
    reader = _user('metadata-shared')
    reader.permissoes_personalizadas.append(owner.permissoes_personalizadas[0])
    administrator = _user('metadata-admin', 'admin')
    diagram = Diagram(title='Contrato', document={}, owner=owner, current_version=7)
    diagram.shared_users.append(reader)
    db.session.add_all([owner, reader, administrator, diagram])
    db.session.commit()

    _login(client, owner)
    owner_data = client.get(f'/api/diagramas/{diagram.id}/metadados').get_json()
    assert owner_data['current_version'] == 7
    assert owner_data['preview_state'] == 'missing'
    assert owner_data['can_edit'] and owner_data['can_open_scene']
    assert 'editor_url' in owner_data and 'scene_url' in owner_data
    assert 'mode=edit' in owner_data['scene_url']
    assert '?v=7' in owner_data['preview_url']

    editable_scene_url = owner_data['scene_url']
    for permission in owner.permissoes_personalizadas.all():
        owner.permissoes_personalizadas.remove(permission)
    db.session.commit()
    assert client.get(editable_scene_url).status_code == 403

    _login(client, reader)
    reader_data = client.get(f'/api/diagramas/{diagram.id}/metadados').get_json()
    assert reader_data['can_view'] and reader_data['can_open_scene']
    assert not reader_data['can_edit']
    assert 'mode=edit' not in reader_data['scene_url']
    assert 'editor_url' not in reader_data
    assert 'view_url' in reader_data

    _login(client, administrator)
    admin_data = client.get(f'/api/diagramas/{diagram.id}/metadados').get_json()
    assert admin_data['can_view'] and admin_data['can_edit']
    assert admin_data['can_open_scene'] and 'editor_url' in admin_data


def test_article_reader_gets_raster_only_with_materialized_link(client):
    owner = _user('context-owner')
    reader = _user('context-reader', 'diagrama_renderizar_artigo')
    diagram = Diagram(title='Contextual', document={'secret': True}, owner=owner)
    article = Article(titulo='Artigo', texto='', author=reader)
    db.session.add_all([owner, reader, diagram, article])
    db.session.flush()
    db.session.add(ArticleDiagram(article_id=article.id, diagram_id=diagram.id))
    db.session.commit()
    _login(client, reader)

    response = client.get(
        f'/api/artigos/{article.id}/diagramas/{diagram.id}/metadados'
    )
    data = response.get_json()
    assert response.status_code == 200
    assert data['can_view'] is True
    assert data['can_edit'] is False and data['can_open_scene'] is False
    assert '/artigos/' in data['preview_url']
    assert not {'editor_url', 'view_url', 'scene_url'} & data.keys()
    assert client.get(f'/api/diagramas/{diagram.id}/metadados').status_code == 404
    assert client.get(f'/api/diagramas/{diagram.id}/cena').status_code == 403


def test_context_requires_link_and_archived_diagrams_are_unavailable(client):
    owner = _user('archive-owner')
    reader = _user('archive-reader', 'diagrama_renderizar_artigo')
    diagram = Diagram(title='Arquivado', document={}, owner=owner)
    article = Article(titulo='Artigo', texto='', author=reader)
    db.session.add_all([owner, reader, diagram, article])
    db.session.commit()
    _login(client, reader)
    url = f'/api/artigos/{article.id}/diagramas/{diagram.id}/metadados'
    assert client.get(url).status_code == 404

    db.session.add(ArticleDiagram(article_id=article.id, diagram_id=diagram.id))
    diagram.archived_at = datetime.now(timezone.utc)
    db.session.commit()
    assert client.get(url).status_code == 404


def test_listing_filters_searches_paginates_and_never_leaks_scope(client):
    user = _user('listing-user', 'diagrama_visualizar')
    visible = Diagram(title='Fluxo Alfa', document={}, owner=user)
    template = Diagram(title='Modelo Alfa', document={}, owner=user,
                       diagram_type=DiagramType.TEMPLATE)
    outsider = _user('listing-outsider')
    hidden = Diagram(title='Alfa Secreto', document={}, owner=outsider)
    db.session.add_all([user, outsider, visible, template, hidden])
    db.session.commit()
    _login(client, user)

    response = client.get('/api/diagramas/metadados?tipo=diagrama&q=Alfa&page=1&per_page=1')
    data = response.get_json()
    assert response.status_code == 200
    assert data['total'] == 1 and data['per_page'] == 1
    assert [item['id'] for item in data['items']] == [str(visible.id)]
    templates = client.get('/api/diagramas/metadados?tipo=modelo&q=Alfa').get_json()
    assert [item['id'] for item in templates['items']] == [str(template.id)]
    assert str(hidden.id) not in str(data) + str(templates)


def test_missing_and_out_of_scope_metadata_are_indistinguishable(client):
    user = _user('nonleak-user', 'diagrama_visualizar')
    outsider = _user('nonleak-owner')
    hidden = Diagram(title='Título ultrassecreto', document={}, owner=outsider)
    db.session.add_all([user, outsider, hidden])
    db.session.commit()
    _login(client, user)

    hidden_response = client.get(f'/api/diagramas/{hidden.id}/metadados')
    missing_response = client.get(f'/api/diagramas/{uuid.uuid4()}/metadados')
    assert hidden_response.status_code == missing_response.status_code == 404
    assert hidden_response.get_data() == missing_response.get_data()
    assert b'ultrassecreto' not in hidden_response.get_data().lower()
