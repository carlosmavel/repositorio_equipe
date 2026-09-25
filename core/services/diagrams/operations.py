"""Rotinas operacionais conservadoras do armazenamento de diagramas."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ...models import DiagramAsset
from .storage import LocalDiagramStorage, get_storage


@dataclass(frozen=True)
class AssetCollectionReport:
    scanned: int
    candidates: int
    deleted: int
    reclaimed_bytes: int


def collect_orphan_blobs(*, older_than_days=30, execute=False, storage=None, now=None):
    """Coleta apenas blobs sem linha no banco e antigos o bastante.

    O modo padrão é simulação. Assets registrados nunca são removidos aqui,
    ainda que não estejam na versão corrente, pois podem integrar o histórico.
    """
    if older_than_days < 1:
        raise ValueError('older_than_days deve ser pelo menos 1.')
    storage = storage or get_storage()
    if not isinstance(storage, LocalDiagramStorage):
        raise TypeError('O coletor local exige LocalDiagramStorage.')
    root = storage.root.resolve()
    if not root.exists():
        return AssetCollectionReport(0, 0, 0, 0)
    referenced = {row[0] for row in DiagramAsset.query.with_entities(DiagramAsset.storage_key)}
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=older_than_days)
    scanned = candidates = deleted = reclaimed = 0
    for path in root.glob('assets/sha256/*/*'):
        if not path.is_file():
            continue
        scanned += 1
        key = path.relative_to(root).as_posix()
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if key in referenced or modified > cutoff:
            continue
        candidates += 1
        reclaimed += path.stat().st_size
        if execute:
            path.unlink()
            deleted += 1
    return AssetCollectionReport(scanned, candidates, deleted, reclaimed)
