import io
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import db
from core.models import User
from core.utils import sanitize_html

VIDEO_UPLOAD_URL = '/artigos/editor-video-upload'


@pytest.fixture
def video_app(app_ctx, tmp_path):
    app_ctx.config['UPLOAD_FOLDER'] = str(tmp_path)
    app_ctx.config['EDITOR_VIDEO_MAX_BYTES'] = 1024
    yield app_ctx


@pytest.fixture
def logged_video_client(video_app, client):
    user = User(username='video_editor', email='video@example.com', password_hash='x')
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as session:
        session['user_id'] = user.id
    return client


def upload(client, filename='clip.mp4', mime='video/mp4', content=b'video-data'):
    return client.post(
        VIDEO_UPLOAD_URL,
        data={'file': (io.BytesIO(content), filename, mime)},
        content_type='multipart/form-data',
    )


def successful_probe(*args, **kwargs):
    return SimpleNamespace(returncode=0, stdout='video\n', stderr='')


def test_mp4_is_validated_and_stored_separately(video_app, logged_video_client):
    with patch('blueprints.articles.shutil.which', return_value='/usr/bin/ffprobe'), \
         patch('blueprints.articles.subprocess.run', side_effect=successful_probe):
        response = upload(logged_video_client)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['url'].startswith('/uploads/editor-videos/')
    assert payload['url'].endswith('.mp4')
    assert payload['mime_type'] == 'video/mp4'
    assert payload['converted'] is False
    saved = os.path.join(video_app.config['UPLOAD_FOLDER'], payload['url'].removeprefix('/uploads/'))
    assert open(saved, 'rb').read() == b'video-data'


def test_avi_is_converted_before_url_is_returned(video_app, logged_video_client):
    def run(command, **kwargs):
        if command[0].endswith('ffmpeg'):
            with open(command[-1], 'wb') as converted:
                converted.write(b'converted-mp4')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        return successful_probe()

    with patch('blueprints.articles.shutil.which', side_effect=lambda name: f'/usr/bin/{name}'), \
         patch('blueprints.articles.subprocess.run', side_effect=run):
        response = upload(logged_video_client, 'legacy.avi', 'video/x-msvideo')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['converted'] is True
    assert payload['url'].endswith('.mp4')
    saved = os.path.join(video_app.config['UPLOAD_FOLDER'], payload['url'].removeprefix('/uploads/'))
    assert open(saved, 'rb').read() == b'converted-mp4'
    assert not any(name.endswith('.avi') for _, _, files in os.walk(video_app.config['UPLOAD_FOLDER']) for name in files)


def test_video_rejects_mime_extension_mismatch_without_publishing(video_app, logged_video_client):
    response = upload(logged_video_client, 'clip.avi', 'video/mp4')
    assert response.status_code == 415
    assert 'inválido' in response.get_json()['error'].lower()


def test_video_rejects_oversized_file(video_app, logged_video_client):
    video_app.config['EDITOR_VIDEO_MAX_BYTES'] = 4
    response = upload(logged_video_client, content=b'12345')
    assert response.status_code == 413
    assert 'limite' in response.get_json()['error'].lower()
    video_dir = os.path.join(video_app.config['UPLOAD_FOLDER'], 'editor-videos')
    assert not [name for name in os.listdir(video_dir) if not name.startswith('.')]


def test_invalid_video_content_is_not_published(video_app, logged_video_client):
    failed_probe = SimpleNamespace(returncode=1, stdout='', stderr='invalid')
    with patch('blueprints.articles.shutil.which', return_value='/usr/bin/ffprobe'), \
         patch('blueprints.articles.subprocess.run', return_value=failed_probe):
        response = upload(logged_video_client)
    assert response.status_code == 415
    video_dir = os.path.join(video_app.config['UPLOAD_FOLDER'], 'editor-videos')
    assert not [name for name in os.listdir(video_dir) if not name.startswith('.')]


def test_video_upload_requires_authentication(video_app, client):
    response = upload(client)
    assert response.status_code == 401


def test_sanitizer_only_allows_internal_uploaded_video_reference():
    safe = '<p>Antes</p><video src="/uploads/editor-videos/0123456789abcdef0123456789abcdef.mp4" controls preload="metadata" playsinline="true" data-article-video="true"></video><p>Depois</p>'
    assert sanitize_html(safe) == safe

    unsafe = '<video src="https://evil.example/video.mp4" autoplay onerror="alert(1)"></video><script>alert(1)</script>'
    cleaned = sanitize_html(unsafe)
    assert '<video></video>' in cleaned
    assert 'src=' not in cleaned
    assert 'autoplay' not in cleaned
    assert '<script' not in cleaned
