"""Regressões do caso de uso de instanciação de modelos."""

from copy import deepcopy
import hashlib

import pytest

from core.database import db
from core.enums import DiagramScope, DiagramType
from core.models import Diagram, DiagramAsset, DiagramVersion, Funcao, User
from core.services.diagrams.access import DiagramAccessDenied
from core.services.diagrams.commands import (
    create_diagram_from_template, save_diagram_payload,
)
from core.services.diagrams.rendering import get_preview
from core.services.diagrams.schema import validate_save_payload


class MemoryStorage:
    def __init__(self, blobs):
        self.blobs = blobs

    def read(self, key):
        return self.blobs[key]

    def put_sha256(self, content):
        key = hashlib.sha256(content).hexdigest()
        self.blobs[key] = content
        return key


def _actor(*permissions):
    user = User(username='template-user', email='template@example.test', password_hash='x')
    user.permissoes_personalizadas.extend([
        Funcao(codigo=code, nome=code) for code in permissions
    ])
    return user


def test_create_from_template_is_deep_independent_and_keeps_source_preview(app_ctx):
    actor = _actor('diagrama_visualizar', 'diagrama_criar', 'diagrama_editar')
    original = {'schemaVersion': 1, 'elements': [{'id': 'original'}], 'appState': {},
                'metadata': {}, 'files': {}}
    template = Diagram(title='Modelo', document=deepcopy(original), owner=actor,
                       diagram_type=DiagramType.TEMPLATE)
    source = DiagramVersion(diagram=template, number=1, title='Modelo',
                            document=deepcopy(original), author=actor,
                            schema_version=1, content_hash='source')
    preview = DiagramAsset(diagram=template, storage_key='preview-key', sha256='p' * 64,
                           byte_size=7, kind='preview', content_type='image/png')
    source.assets.append(preview)
    db.session.add_all([actor, template, source])
    db.session.flush()
    template.current_version_id = source.id
    db.session.commit()

    diagram_id = create_diagram_from_template(
        template.id, actor, DiagramScope.PRIVATE, session=db.session,
    )
    copied = db.session.get(Diagram, diagram_id)
    copied_version = copied.current_version_record

    assert copied.diagram_type == DiagramType.DIAGRAM
    assert copied.owner_id == actor.id
    assert copied.scope == DiagramScope.PRIVATE
    assert copied.source_template_id == template.id
    assert copied_version.source_version_id == source.id
    assert copied_version.assets == [preview]

    changed = deepcopy(copied.document)
    changed['elements'][0]['id'] = 'changed'
    payload = validate_save_payload({**changed, 'lockVersion': copied.lock_version})
    save_diagram_payload(actor, copied, payload, session=db.session,
                         storage=MemoryStorage({'preview-key': b'preview'}))
    db.session.refresh(template)
    db.session.refresh(source)

    assert template.scene_data == original
    assert template.current_version_id == source.id
    assert source.scene_data == original
    assert get_preview(template, actor, storage=MemoryStorage({'preview-key': b'preview'}))[0] == b'preview'


def test_using_template_does_not_require_management_permission(app_ctx):
    actor = _actor('diagrama_visualizar', 'diagrama_criar')
    template = Diagram(title='Modelo', document={}, owner=actor,
                       diagram_type=DiagramType.TEMPLATE)
    version = DiagramVersion(diagram=template, number=1, title='Modelo', document={},
                             author=actor, content_hash='source')
    db.session.add_all([actor, template, version])
    db.session.flush()
    template.current_version_id = version.id
    db.session.commit()

    assert create_diagram_from_template(template.id, actor, 'private')

    with pytest.raises(DiagramAccessDenied, match='diagrama_modelo_gerenciar'):
        save_diagram_payload(
            actor, template,
            validate_save_payload({'schemaVersion': 1, 'elements': [], 'appState': {},
                                   'metadata': {}, 'files': {}, 'lockVersion': 0}),
        )
