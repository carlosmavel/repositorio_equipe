"""Tests for the versioned, content-addressed diagram save contract."""

import hashlib
from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from core.database import db
from core.models import Diagram, DiagramAsset, DiagramVersion, Funcao, User
from core.services.diagrams.commands import save_diagram_payload
from core.services.diagrams.schema import DiagramSchemaError, validate_save_payload


def _payload(**changes):
    value = {
        'schemaVersion': 1,
        'elements': [{'id': 'box', 'type': 'rectangle'}],
        'appState': {'viewBackgroundColor': '#fff', 'selectedElementIds': {'box': True}},
        'metadata': {'excalidrawVersion': '1.0'},
        'files': {},
        'lockVersion': 0,
    }
    value.update(changes)
    return value


def test_payload_is_canonical_and_removes_ephemeral_state():
    first = validate_save_payload(_payload())
    second = validate_save_payload({
        'files': {}, 'metadata': {'excalidrawVersion': '1.0'},
        'appState': {'selectedElementIds': {}, 'viewBackgroundColor': '#fff'},
        'elements': [{'type': 'rectangle', 'id': 'box'}],
        'schemaVersion': 1, 'lockVersion': 0,
    })

    assert 'selectedElementIds' not in first.document['appState']
    assert first.content_hash == second.content_hash
    assert first.content_hash == hashlib.sha256(first.canonical_json.encode()).hexdigest()


def test_payload_requires_files_outside_json():
    with pytest.raises(DiagramSchemaError, match='corresponder'):
        validate_save_payload(_payload(files={'image': {'mimeType': 'image/png'}}))


def test_save_creates_version_and_content_addressed_asset(app_ctx, tmp_path):
    class Storage:
        def put_sha256(self, content):
            digest = hashlib.sha256(content).hexdigest()
            (tmp_path / digest).write_bytes(content)
            return f'assets/sha256/{digest}'

    user = User(username='diagram-save', email='diagram-save@example.test', password_hash='x')
    user.permissoes_personalizadas.append(
        Funcao(codigo='diagrama_editar', nome='Editar diagramas')
    )
    diagram = Diagram(title='Fluxo', document={}, owner=user)
    db.session.add_all([user, diagram])
    db.session.commit()
    upload = FileStorage(stream=BytesIO(b'png-content'), content_type='image/png')
    payload = validate_save_payload(
        _payload(files={'image': {'mimeType': 'image/png'}}), {'image': upload}
    )

    save_diagram_payload(user, diagram, payload, session=db.session, storage=Storage())

    version = db.session.get(DiagramVersion, diagram.current_version_id)
    asset = DiagramAsset.query.one()
    assert diagram.lock_version == 1
    assert version.content_hash == payload.content_hash
    assert version.schema_version == 1
    assert version.assets == [asset]
    assert asset.sha256 == hashlib.sha256(b'png-content').hexdigest()


def test_save_rejects_stale_lock(app_ctx):
    user = User(username='diagram-lock', email='diagram-lock@example.test', password_hash='x')
    user.permissoes_personalizadas.append(
        Funcao(codigo='diagrama_editar', nome='Editar diagramas')
    )
    diagram = Diagram(title='Fluxo', document={}, owner=user, lock_version=2)
    db.session.add_all([user, diagram])
    db.session.commit()

    with pytest.raises(ValueError, match='outra sessão'):
        save_diagram_payload(user, diagram, validate_save_payload(_payload()), session=db.session)
    assert DiagramVersion.query.count() == 0
