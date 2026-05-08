import io
import os

import pytest

from app import db
from core.models import User


EDITOR_UPLOAD_URL = '/artigos/editor-image-upload'


@pytest.fixture
def upload_app(app_ctx, tmp_path):
    original_upload_folder = app_ctx.config.get('UPLOAD_FOLDER')
    original_editor_limit = app_ctx.config.get('EDITOR_IMAGE_MAX_BYTES')
    original_editor_content_limit = app_ctx.config.get('EDITOR_IMAGE_MAX_CONTENT_LENGTH')
    app_ctx.config['UPLOAD_FOLDER'] = str(tmp_path)
    app_ctx.config['EDITOR_IMAGE_MAX_BYTES'] = 1024
    app_ctx.config.pop('EDITOR_IMAGE_MAX_CONTENT_LENGTH', None)
    yield app_ctx
    app_ctx.config['UPLOAD_FOLDER'] = original_upload_folder
    if original_editor_limit is None:
        app_ctx.config.pop('EDITOR_IMAGE_MAX_BYTES', None)
    else:
        app_ctx.config['EDITOR_IMAGE_MAX_BYTES'] = original_editor_limit
    if original_editor_content_limit is None:
        app_ctx.config.pop('EDITOR_IMAGE_MAX_CONTENT_LENGTH', None)
    else:
        app_ctx.config['EDITOR_IMAGE_MAX_CONTENT_LENGTH'] = original_editor_content_limit


@pytest.fixture
def logged_client(upload_app, client):
    user = User(username='editor_upload', email='editor-upload@example.com', password_hash='x')
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = user.username
    return client


def _upload(client, filename, content, content_type):
    return client.post(
        EDITOR_UPLOAD_URL,
        data={'file': (io.BytesIO(content), filename, content_type)},
        content_type='multipart/form-data',
    )


def _saved_path(upload_app, url):
    return os.path.join(upload_app.config['UPLOAD_FOLDER'], url.removeprefix('/uploads/'))


def test_valid_editor_image_upload_saves_file_and_returns_json_url(upload_app, logged_client):
    response = _upload(logged_client, 'foto.png', b'valid png content', 'image/png')

    assert response.status_code == 200
    assert response.is_json
    payload = response.get_json()
    assert set(payload) == {'url'}
    assert payload['url'].startswith('/uploads/editor/')
    assert payload['url'].endswith('.png')
    assert os.path.exists(_saved_path(upload_app, payload['url']))


def test_editor_image_upload_blocks_svg_even_with_image_mime(upload_app, logged_client):
    response = _upload(
        logged_client,
        'icone.svg',
        b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
        'image/svg+xml',
    )

    assert response.status_code == 415
    assert response.is_json
    assert 'inválido' in response.get_json()['error'].lower()
    assert not os.path.exists(os.path.join(upload_app.config['UPLOAD_FOLDER'], 'editor'))


def test_editor_image_upload_blocks_file_above_limit(upload_app, logged_client):
    upload_app.config['EDITOR_IMAGE_MAX_BYTES'] = 10

    response = _upload(logged_client, 'foto.jpg', b'x' * 11, 'image/jpeg')

    assert response.status_code == 413
    assert response.is_json
    assert 'limite' in response.get_json()['error'].lower()
    assert not os.path.exists(os.path.join(upload_app.config['UPLOAD_FOLDER'], 'editor'))


def test_editor_image_upload_blocks_anonymous_user(client, upload_app):
    response = _upload(client, 'foto.webp', b'webp content', 'image/webp')

    assert response.status_code == 401
    assert response.is_json
    assert 'login' in response.get_json()['error'].lower()


def test_editor_image_upload_generates_unique_names(upload_app, logged_client):
    first_response = _upload(logged_client, 'foto.jpeg', b'first image', 'image/jpeg')
    second_response = _upload(logged_client, 'foto.jpeg', b'second image', 'image/jpeg')

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_url = first_response.get_json()['url']
    second_url = second_response.get_json()['url']
    assert first_url != second_url
    assert first_url.startswith('/uploads/editor/')
    assert second_url.startswith('/uploads/editor/')
    assert os.path.exists(_saved_path(upload_app, first_url))
    assert os.path.exists(_saved_path(upload_app, second_url))


def test_editor_image_upload_handles_missing_file(logged_client):
    response = logged_client.post(EDITOR_UPLOAD_URL, data={}, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.is_json
    assert 'nenhum arquivo' in response.get_json()['error'].lower()


def test_uploaded_editor_file_serves_logged_user_from_editor_folder(upload_app, logged_client):
    editor_folder = os.path.join(upload_app.config['UPLOAD_FOLDER'], 'editor')
    os.makedirs(editor_folder, exist_ok=True)
    image_path = os.path.join(editor_folder, 'inline.png')
    with open(image_path, 'wb') as image_file:
        image_file.write(b'inline image')

    response = logged_client.get('/uploads/editor/inline.png')

    assert response.status_code == 200
    assert response.data == b'inline image'


def test_uploaded_editor_file_serves_nested_legacy_inline_images(upload_app, logged_client):
    legacy_folder = os.path.join(upload_app.config['UPLOAD_FOLDER'], 'editor', 'artigo-1')
    os.makedirs(legacy_folder, exist_ok=True)
    image_path = os.path.join(legacy_folder, 'imagem.png')
    with open(image_path, 'wb') as image_file:
        image_file.write(b'legacy inline image')

    response = logged_client.get('/uploads/editor/artigo-1/imagem.png')

    assert response.status_code == 200
    assert response.data == b'legacy inline image'


def test_uploaded_editor_file_blocks_anonymous_user(client, upload_app):
    response = client.get('/uploads/editor/inline.png')

    assert response.status_code == 401


def test_uploaded_editor_file_blocks_path_traversal(upload_app, logged_client):
    editor_folder = os.path.join(upload_app.config['UPLOAD_FOLDER'], 'editor')
    os.makedirs(editor_folder, exist_ok=True)
    secret_path = os.path.join(upload_app.config['UPLOAD_FOLDER'], 'secret.png')
    with open(secret_path, 'wb') as secret_file:
        secret_file.write(b'secret image')

    response = logged_client.get('/uploads/editor/%2e%2e/secret.png')

    assert response.status_code == 404
    assert response.data != b'secret image'
