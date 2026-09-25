"""Criação de diagramas independentes a partir de Meus Diagramas."""

from uuid import UUID

from core.database import db
from core.enums import DiagramScope, DiagramType
from core.models import ArticleDiagram, Diagram, DiagramVersion, Funcao, User


def _user(name, *permissions):
    user = User(username=name, email=f'{name}@example.test', password_hash='x')
    user.permissoes_personalizadas.extend(
        Funcao(codigo=code, nome=f'{name}-{code}') for code in permissions
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, user):
    with client.session_transaction() as session:
        session['user_id'] = user.id


def test_authorized_user_creates_private_unlinked_diagram_and_can_discover_it(client):
    user = _user(
        'diagram-owner', 'diagrama_criar', 'diagrama_visualizar', 'diagrama_editar',
    )
    _login(client, user)

    response = client.post('/api/diagramas', json={'title': '  Fluxo independente  '})

    assert response.status_code == 201
    payload = response.get_json()
    diagram = db.session.get(Diagram, UUID(payload['id']))
    assert diagram.name == 'Fluxo independente'
    assert diagram.owner_id == user.id
    assert diagram.scope == DiagramScope.PRIVATE
    assert diagram.diagram_type == DiagramType.DIAGRAM
    assert diagram.current_version == 1
    assert diagram.current_version_id is not None
    assert DiagramVersion.query.filter_by(diagram_id=diagram.id).count() == 1
    assert ArticleDiagram.query.filter_by(diagram_id=diagram.id).count() == 0
    assert payload['editor_url'].endswith(f'/diagramas/{diagram.id}')
    assert payload['can_edit'] is True

    page = client.get('/diagramas/meus-diagramas')
    assert page.status_code == 200
    assert 'Fluxo independente' in page.get_data(as_text=True)

    selector = client.get('/api/diagramas/metadados?tipo=diagrama')
    assert selector.status_code == 200
    assert any(item['id'] == str(diagram.id) for item in selector.get_json()['items'])


def test_create_permission_controls_page_actions_and_api(client):
    user = _user('diagram-reader', 'diagrama_visualizar')
    _login(client, user)

    page = client.get('/diagramas/meus-diagramas')
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'data-create-diagram' not in html
    assert 'create-diagram-dialog' not in html

    response = client.post('/api/diagramas', json={'title': 'Não autorizado'})
    assert response.status_code == 403
    assert Diagram.query.count() == 0


def test_empty_state_offers_creation_and_invalid_titles_are_reported(client):
    user = _user('empty-owner', 'diagrama_criar', 'diagrama_visualizar')
    _login(client, user)

    html = client.get('/diagramas/meus-diagramas').get_data(as_text=True)
    assert 'Nenhum diagrama encontrado' in html
    assert html.count('data-create-diagram') == 2
    assert 'O diagrama será privado' not in html  # texto é inserido pelo componente JS
    assert 'frontend/diagram-library/create.js' not in html  # o manifest gera URL versionada
    assert '/static/dist/' in html and 'diagram-library' in html

    empty = client.post('/api/diagramas', json={'title': '   '})
    too_long = client.post('/api/diagramas', json={'title': 'x' * 201})
    assert empty.status_code == 400
    assert empty.get_json()['error'] == 'title é obrigatório.'
    assert too_long.status_code == 400
    assert '200' in too_long.get_json()['error']
    assert Diagram.query.count() == 0


def test_standalone_form_reuses_accessible_title_component():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    component = (root / 'frontend/diagram-ui/title-form.js').read_text()
    standalone = (root / 'frontend/diagram-library/create.js').read_text()
    article_dialog = (root / 'frontend/article-editor/diagram-dialog.js').read_text()

    assert "import { diagramTitleForm, titleFromForm }" in standalone
    assert "import { diagramTitleForm, titleFromForm }" in article_dialog
    assert 'required autocomplete="off"' in component
    assert "input.reportValidity()" in component
    assert 'flex-column-reverse flex-sm-row' in component
    assert "dialog.addEventListener('cancel'" in standalone
    assert "form.onsubmit" in standalone
