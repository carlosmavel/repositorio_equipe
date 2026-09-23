"""Comandos transacionais do domínio de diagramas."""

from datetime import datetime, timezone
import hashlib
import json

from ...database import db
from ...models import Diagram, DiagramAsset, DiagramVersion
from ...enums import DiagramStatus
from .access import require_edit, require_view
from .schema import ORQUETASK_DIAGRAM_SCHEMA_VERSION, DiagramSavePayload
from .storage import get_storage


def _snapshot(diagram, author_id, session):
    canonical = json.dumps(diagram.document, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False)
    version = DiagramVersion(
        diagram=diagram, number=diagram.current_version, title=diagram.title,
        document=diagram.document, author_id=author_id,
        schema_version=(diagram.document.get('schemaVersion', ORQUETASK_DIAGRAM_SCHEMA_VERSION)
                        if isinstance(diagram.document, dict) else ORQUETASK_DIAGRAM_SCHEMA_VERSION),
        content_hash=hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
    )
    session.add(version)
    session.flush()
    diagram.current_version_id = version.id
    return version


def _atomic(operation, session):
    """Executa todas as escritas da operação em uma única transação/commit."""
    try:
        result = operation()
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def create_diagram(user, title, document=None, *, celula_id=None,
                   source_diagram_id=None, assets=(), session=None):
    session = session or db.session
    def operation():
        diagram = Diagram(title=title.strip(), document=document or {}, owner_id=user.id,
                          celula_id=celula_id or user.celula_id,
                          source_diagram_id=source_diagram_id)
        session.add(diagram)
        session.flush()
        _snapshot(diagram, user.id, session)
        for asset in assets:
            session.add(DiagramAsset(diagram=diagram, **asset))
        return diagram
    return _atomic(operation, session)


def save_diagram(user, diagram, *, title=None, document=None, assets=(), session=None):
    session = session or db.session
    require_edit(user, diagram)
    def operation():
        if title is not None:
            diagram.title = title.strip()
        if document is not None:
            diagram.document = document
        diagram.current_version += 1
        _snapshot(diagram, user.id, session)
        for asset in assets:
            session.add(DiagramAsset(diagram=diagram, **asset))
        return diagram
    return _atomic(operation, session)


def save_diagram_payload(user, diagram, payload: DiagramSavePayload, *, title=None,
                         session=None, storage=None):
    """Persiste snapshot, blobs e ponteiros correntes em uma transação lógica.

    Os blobs são content-addressed e idempotentes; caso o banco falhe, um blob
    órfão é seguro e pode ser coletado posteriormente sem expor uma versão
    parcial. Todas as mutações relacionais são confirmadas em um único commit.
    """
    session = session or db.session
    storage = storage or get_storage()
    require_edit(user, diagram)
    normalized_title = str(title).strip() if title is not None else None

    def operation():
        if payload.lock_version is not None and payload.lock_version != diagram.lock_version:
            raise ValueError('O diagrama foi alterado por outra sessão.')
        if normalized_title is not None:
            if not normalized_title or len(normalized_title) > 200:
                raise ValueError('title inválido.')
            diagram.title = normalized_title
        diagram.document = payload.document
        diagram.current_version += 1
        diagram.lock_version += 1
        version = DiagramVersion(
            diagram=diagram, number=diagram.current_version, title=diagram.title,
            document=payload.document, author_id=user.id,
            schema_version=ORQUETASK_DIAGRAM_SCHEMA_VERSION,
            content_hash=payload.content_hash,
        )
        session.add(version)
        session.flush()
        diagram.current_version_id = version.id
        for uploaded in payload.files:
            asset = session.query(DiagramAsset).filter_by(
                diagram_id=diagram.id, sha256=uploaded.sha256
            ).first()
            if asset is None:
                asset = DiagramAsset(
                    diagram=diagram, storage_key=storage.put_sha256(uploaded.content),
                    sha256=uploaded.sha256, byte_size=len(uploaded.content),
                    content_type=uploaded.content_type,
                )
                session.add(asset)
            version.assets.append(asset)
        return diagram

    return _atomic(operation, session)


def copy_template(user, template, *, title=None, session=None):
    require_view(user, template)
    return create_diagram(
        user, title or f'Cópia de {template.title}', template.document,
        celula_id=user.celula_id, source_diagram_id=template.id, session=session,
    )


def restore_diagram(user, diagram, version, *, session=None):
    session = session or db.session
    require_edit(user, diagram)
    if version.diagram_id != diagram.id:
        raise ValueError('A versão não pertence ao diagrama.')
    return save_diagram(user, diagram, title=version.title, document=version.document, session=session)


def archive_diagram(user, diagram, *, session=None):
    session = session or db.session
    require_edit(user, diagram)
    def operation():
        diagram.archived_at = datetime.now(timezone.utc)
        diagram.status = DiagramStatus.ARCHIVED
        diagram.current_version += 1
        _snapshot(diagram, user.id, session)
        return diagram
    return _atomic(operation, session)
