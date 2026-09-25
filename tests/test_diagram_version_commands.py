"""Regressões dos comandos transacionais de versionamento de diagramas."""

import pytest

from core.database import db
from core.models import Diagram, DiagramAsset, DiagramVersion, Funcao, User
from core.services.diagrams.commands import (
    DiagramVersionConflict, get_diagram_version_history,
    restore_diagram_version, save_diagram_version,
)
from core.services.diagrams.schema import validate_save_payload


def _scene(element_id):
    return validate_save_payload({
        'schemaVersion': 1, 'elements': [{'id': element_id}],
        'appState': {}, 'metadata': {}, 'files': {},
    })


def _diagram():
    actor = User(username='version-owner', email='versions@example.test', password_hash='x')
    actor.permissoes_personalizadas.extend([
        Funcao(codigo='diagrama_visualizar', nome='Visualizar diagramas'),
        Funcao(codigo='diagrama_editar', nome='Editar diagramas'),
    ])
    first_scene = _scene('one')
    diagram = Diagram(title='Fluxo', document=first_scene.document, owner=actor)
    first = DiagramVersion(diagram=diagram, number=1, title=diagram.title,
                           document=first_scene.document, author=actor,
                           content_hash=first_scene.content_hash)
    db.session.add_all([actor, diagram, first])
    db.session.flush()
    diagram.current_version_id = first.id
    db.session.commit()
    return actor, diagram, first


def test_numbering_noop_conflict_and_history_pagination(app_ctx):
    actor, diagram, first = _diagram()
    second = save_diagram_version(diagram.id, first.id, _scene('two'), None,
                                  actor, 'edição')
    assert second.number == 2
    assert save_diagram_version(diagram.id, second.id, _scene('two'), None,
                                actor, 'repetição').id == second.id
    assert DiagramVersion.query.filter_by(diagram_id=diagram.id).count() == 2

    with pytest.raises(DiagramVersionConflict):
        save_diagram_version(diagram.id, first.id, _scene('three'), None,
                             actor, 'base obsoleta')

    page = get_diagram_version_history(diagram.id, actor, page=1, per_page=1)
    assert page.total == 2
    assert [item.number for item in page.items] == [2]


def test_restore_creates_new_version_and_retains_historical_assets(app_ctx):
    actor, diagram, first = _diagram()
    asset = DiagramAsset(diagram=diagram, storage_key='assets/original',
                         sha256='a' * 64, byte_size=3)
    db.session.add(asset)
    first.assets.append(asset)
    db.session.commit()
    second = save_diagram_version(diagram.id, first.id, _scene('two'), None,
                                  actor, 'edição')

    restored = restore_diagram_version(diagram.id, first.id, second.id, actor,
                                       'restaurar versão inicial')
    assert restored.id not in (first.id, second.id)
    assert restored.number == 3
    assert restored.source_version_id == first.id
    assert restored.document == first.document
    assert restored.assets == [asset]
    assert first.assets == [asset]
    assert diagram.current_version_id == restored.id
    assert diagram.updated_by_user_id == actor.id
    assert diagram.lock_version == 2


def test_failed_save_rolls_back_version_and_current_pointer(app_ctx, monkeypatch):
    actor, diagram, first = _diagram()
    payload = _scene('two')
    # Simula falha depois do INSERT/flush da nova versão.
    monkeypatch.setattr(db.session, 'flush', lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError('falha de persistência')))
    with pytest.raises(RuntimeError):
        save_diagram_version(diagram.id, first.id, payload, None, actor, 'falhar')
    db.session.expire_all()
    assert DiagramVersion.query.filter_by(diagram_id=diagram.id).count() == 1
    persisted = db.session.get(Diagram, diagram.id)
    assert persisted.current_version_id == first.id
    assert persisted.current_version == 1
