"""Comandos transacionais do domínio de diagramas."""

from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json

from ...database import db
from ...models import Diagram, DiagramAsset, DiagramVersion
from ...enums import DiagramScope, DiagramStatus, DiagramType
from .access import _organizational_ids, require_edit, require_view
from .schema import ORQUETASK_DIAGRAM_SCHEMA_VERSION, DiagramSavePayload
from .storage import get_storage, sanitize_preview


class DiagramVersionConflict(ValueError):
    """A versão usada como base deixou de ser a versão corrente."""


def _validated_scene(scene):
    """Aceita o resultado do validador ou uma cena já normalizada."""
    if isinstance(scene, DiagramSavePayload):
        return scene.document, scene.content_hash, scene.files
    if not isinstance(scene, dict):
        raise TypeError('scene deve ser uma cena validada ou DiagramSavePayload.')
    canonical = json.dumps(scene, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False)
    return scene, hashlib.sha256(canonical.encode('utf-8')).hexdigest(), ()


def _has_permission(actor, code):
    return bool(actor and (actor.has_permissao('admin') or actor.has_permissao(code)))


def _require_permission(actor, code):
    if not _has_permission(actor, code):
        from .access import DiagramAccessDenied
        raise DiagramAccessDenied(f'Permissão {code} necessária.')


def _require_template_management(actor, diagram=None):
    if diagram is None or diagram.diagram_type == DiagramType.TEMPLATE:
        _require_permission(actor, 'diagrama_modelo_gerenciar')


def _scope_values(actor, target_scope):
    """Normaliza o escopo solicitado e impede IDs organizacionais ambíguos."""
    if isinstance(target_scope, dict):
        raw_scope = target_scope.get('scope', target_scope.get('type'))
        target_id = target_scope.get('id')
    else:
        raw_scope, target_id = target_scope, None
    scope = raw_scope if isinstance(raw_scope, DiagramScope) else DiagramScope(raw_scope)
    fields = {name: None for name in (
        'instituicao_id', 'estabelecimento_id', 'setor_id', 'celula_id'
    )}
    if scope == DiagramScope.PRIVATE:
        return scope, fields
    attributes = {
        DiagramScope.INSTITUTION: 'instituicao_id',
        DiagramScope.ESTABLISHMENT: 'estabelecimento_id',
        DiagramScope.SECTOR: 'setor_id',
        DiagramScope.CELL: 'celula_id',
    }
    field = attributes[scope]
    if target_id is None:
        target_id = getattr(actor, field, None)
        if target_id is None and field == 'instituicao_id' and actor.estabelecimento:
            target_id = actor.estabelecimento.instituicao_id
    if target_id is None:
        raise ValueError('O ator não pertence ao escopo de destino informado.')
    membership_keys = {
        DiagramScope.INSTITUTION: 'institutions',
        DiagramScope.ESTABLISHMENT: 'establishments',
        DiagramScope.SECTOR: 'sectors',
        DiagramScope.CELL: 'cells',
    }
    if not _has_permission(actor, 'admin'):
        allowed_ids = _organizational_ids(actor)[membership_keys[scope]]
        if target_id not in allowed_ids:
            raise ValueError('O ator não pertence ao escopo de destino informado.')
    fields[field] = target_id
    return scope, fields


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
                   source_diagram_id=None, assets=(), session=None,
                   diagram_type=DiagramType.DIAGRAM):
    session = session or db.session
    diagram_type = (diagram_type if isinstance(diagram_type, DiagramType)
                    else DiagramType(diagram_type))
    if diagram_type == DiagramType.TEMPLATE:
        _require_template_management(user)
    else:
        _require_permission(user, 'diagrama_criar')
    def operation():
        diagram = Diagram(title=title.strip(), document=document or {}, owner_id=user.id,
                          celula_id=celula_id or user.celula_id,
                          source_template_id=source_diagram_id,
                          diagram_type=diagram_type)
        session.add(diagram)
        session.flush()
        _snapshot(diagram, user.id, session)
        for asset in assets:
            session.add(DiagramAsset(diagram=diagram, **asset))
        return diagram
    return _atomic(operation, session)


def save_diagram(user, diagram, *, title=None, document=None, assets=(), session=None):
    session = session or db.session
    _require_template_management(user, diagram)
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
    _require_template_management(user, diagram)
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
        if payload.preview is not None:
            content, content_type, _, _ = sanitize_preview(payload.preview)
            digest = hashlib.sha256(content).hexdigest()
            preview = DiagramAsset(
                diagram=diagram, storage_key=storage.put_sha256(content),
                sha256=digest, byte_size=len(content), kind='preview',
                content_type=content_type,
            )
            session.add(preview)
            version.assets.append(preview)
        return diagram

    return _atomic(operation, session)


def save_diagram_version(diagram_id, base_version_id, scene, preview, actor, reason,
                         *, session=None, storage=None, _source_version=None,
                         _force=False):
    """Cria atomicamente um snapshot imutável a partir da versão corrente.

    O bloqueio pessimista serializa a numeração. A comparação do identificador
    da base, feita depois do bloqueio, fornece o conflito otimista esperado pelo
    editor. Cenas com o mesmo hash são um no-op completo.
    """
    session = session or db.session
    storage = storage or get_storage()
    document, content_hash, files = _validated_scene(scene)

    def operation():
        diagram = (session.query(Diagram).filter_by(id=diagram_id)
                   .with_for_update().one())
        _require_template_management(actor, diagram)
        require_edit(actor, diagram)
        if diagram.current_version_id != base_version_id:
            raise DiagramVersionConflict(
                'A versão base não é mais a versão corrente do diagrama.'
            )
        current = session.get(DiagramVersion, diagram.current_version_id)
        if not _force and current is not None and current.content_hash == content_hash:
            return current

        version = DiagramVersion(
            diagram=diagram, number=diagram.current_version + 1,
            title=diagram.title, document=deepcopy(document), author_id=actor.id,
            schema_version=document.get('schemaVersion', ORQUETASK_DIAGRAM_SCHEMA_VERSION),
            content_hash=content_hash, reason=(str(reason).strip() or None)
            if reason is not None else None,
            source_version_id=(_source_version.id if _source_version is not None else None),
        )
        session.add(version)
        session.flush()
        for uploaded in files:
            asset = session.query(DiagramAsset).filter_by(
                diagram_id=diagram.id, sha256=uploaded.sha256,
            ).first()
            if asset is None:
                asset = DiagramAsset(
                    diagram=diagram, storage_key=storage.put_sha256(uploaded.content),
                    sha256=uploaded.sha256, byte_size=len(uploaded.content),
                    content_type=uploaded.content_type,
                )
                session.add(asset)
            version.assets.append(asset)
        if preview is not None:
            content, content_type, _, _ = sanitize_preview(preview)
            digest = hashlib.sha256(content).hexdigest()
            asset = session.query(DiagramAsset).filter_by(
                diagram_id=diagram.id, sha256=digest, kind='preview',
            ).first()
            if asset is None:
                asset = DiagramAsset(
                    diagram=diagram, storage_key=storage.put_sha256(content),
                    sha256=digest, byte_size=len(content), kind='preview',
                    content_type=content_type,
                )
                session.add(asset)
            version.assets.append(asset)
        if _source_version is not None:
            version.assets.extend(asset for asset in _source_version.assets
                                  if asset not in version.assets)
        now = datetime.now(timezone.utc)
        diagram.document = deepcopy(document)
        diagram.current_version = version.number
        diagram.current_version_id = version.id
        diagram.updated_by_user_id = actor.id
        diagram.updated_at = now
        diagram.lock_version += 1
        return version

    return _atomic(operation, session)


def restore_diagram_version(diagram_id, version_id, base_version_id, actor, reason,
                            *, session=None):
    """Restaura copiando uma versão histórica para um novo snapshot."""
    session = session or db.session
    source = session.get(DiagramVersion, version_id)
    if source is None or source.diagram_id != diagram_id:
        raise ValueError('A versão não pertence ao diagrama.')
    restored = save_diagram_version(
        diagram_id, base_version_id, deepcopy(source.document), None, actor, reason,
        session=session, _source_version=source, _force=True,
    )
    return restored


def get_diagram_version_history(diagram_id, actor, *, page=1, per_page=20,
                                session=None):
    """Retorna o histórico mais recente primeiro, com paginação limitada."""
    session = session or db.session
    diagram = session.get(Diagram, diagram_id)
    if diagram is None:
        raise ValueError('Diagrama não encontrado.')
    require_view(actor, diagram)
    if page < 1 or per_page < 1 or per_page > 100:
        raise ValueError('Paginação inválida.')
    return (session.query(DiagramVersion).filter_by(diagram_id=diagram_id)
            .order_by(DiagramVersion.number.desc())
            .paginate(page=page, per_page=per_page, error_out=False))


def copy_template(user, template, *, title=None, session=None):
    session = session or db.session
    diagram_id = create_diagram_from_template(
        template.id, user,
        ({'scope': DiagramScope.CELL, 'id': user.celula_id}
         if user.celula_id else DiagramScope.PRIVATE),
        title=title, session=session,
    )
    return session.get(Diagram, diagram_id)


def create_diagram_from_template(template_id, actor, target_scope, *, title=None,
                                 session=None):
    """Cria uma cópia independente da versão corrente de um modelo."""
    session = session or db.session
    _require_permission(actor, 'diagrama_visualizar')
    _require_permission(actor, 'diagrama_criar')

    def operation():
        template = session.query(Diagram).filter_by(id=template_id).with_for_update().one()
        if template.diagram_type != DiagramType.TEMPLATE:
            raise ValueError('O diagrama de origem não é um modelo.')
        require_view(actor, template)
        source_version = session.query(DiagramVersion).filter_by(
            id=template.current_version_id,
        ).with_for_update().one()
        scope, scope_fields = _scope_values(actor, target_scope)
        document = deepcopy(source_version.document)
        diagram = Diagram(
            title=(title or f'Cópia de {template.title}').strip(),
            document=deepcopy(document), owner_id=actor.id, diagram_type=DiagramType.DIAGRAM,
            scope=scope, source_template_id=template.id, **scope_fields,
        )
        session.add(diagram)
        session.flush()
        version = _snapshot(diagram, actor.id, session)
        version.document = document
        version.source_version_id = source_version.id
        version.assets.extend(source_version.assets)
        return diagram.id

    return _atomic(operation, session)


def restore_diagram(user, diagram, version, *, session=None):
    session = session or db.session
    require_edit(user, diagram)
    if version.diagram_id != diagram.id:
        raise ValueError('A versão não pertence ao diagrama.')
    return save_diagram(user, diagram, title=version.title, document=version.document, session=session)


def archive_diagram(user, diagram, *, session=None):
    session = session or db.session
    _require_template_management(user, diagram)
    require_edit(user, diagram)
    def operation():
        diagram.archived_at = datetime.now(timezone.utc)
        diagram.status = DiagramStatus.ARCHIVED
        diagram.current_version += 1
        _snapshot(diagram, user.id, session)
        return diagram
    return _atomic(operation, session)
