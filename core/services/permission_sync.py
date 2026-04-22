"""Sincronização idempotente do catálogo de permissões."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from ..models import Funcao
    from ..permission_catalog import CATALOG
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.models import Funcao
    from core.permission_catalog import CATALOG

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PermissionSyncResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0


def sync_permission_catalog(session: Session) -> PermissionSyncResult:
    """Sincroniza permissões por ``codigo`` com upsert idempotente.

    - Cria o registro quando ``codigo`` não existe.
    - Atualiza somente campos gerenciados pelo catálogo (atualmente ``nome``).
    - Não remove registros extras já existentes no banco.
    """

    created = 0
    updated = 0
    unchanged = 0

    for item in CATALOG:
        existing = session.query(Funcao).filter_by(codigo=item.codigo).one_or_none()

        if existing is None:
            session.add(Funcao(codigo=item.codigo, nome=item.nome))
            created += 1
            continue

        if existing.nome != item.nome:
            existing.nome = item.nome
            updated += 1
        else:
            unchanged += 1

    result = PermissionSyncResult(created=created, updated=updated, unchanged=unchanged)
    logger.info(
        "permission_catalog_sync",
        extra={
            "event": "permission_catalog_sync",
            "created_count": result.created,
            "updated_count": result.updated,
            "unchanged_count": result.unchanged,
            "catalog_size": len(CATALOG),
        },
    )
    return result


def sync_permission_catalog_with_lock(session: Session) -> PermissionSyncResult | None:
    """Executa sincronização sob lock advisory quando disponível.

    Retorna ``None`` quando não for possível obter lock (outra instância já está sincronizando).
    """

    bind = session.get_bind()
    if bind is None:
        return sync_permission_catalog(session)

    dialect = bind.dialect.name
    if dialect != "postgresql":
        return sync_permission_catalog(session)

    lock_key = 918273645
    lock_acquired = session.execute(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": lock_key},
    ).scalar()

    if not lock_acquired:
        logger.info(
            "permission_catalog_sync_skipped",
            extra={"event": "permission_catalog_sync_skipped", "reason": "lock_not_acquired"},
        )
        return None

    try:
        return sync_permission_catalog(session)
    finally:
        session.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": lock_key},
        )
