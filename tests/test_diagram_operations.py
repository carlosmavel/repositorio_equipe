import os
from datetime import datetime, timedelta, timezone

from core.services.diagrams.operations import collect_orphan_blobs
from core.services.diagrams.storage import LocalDiagramStorage


def test_orphan_collection_is_dry_run_by_default(app_ctx, tmp_path):
    storage = LocalDiagramStorage(tmp_path)
    orphan = tmp_path / 'assets/sha256/aa/orphan'
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b'orphan')
    old = (datetime.now(timezone.utc) - timedelta(days=40)).timestamp()
    os.utime(orphan, (old, old))

    report = collect_orphan_blobs(storage=storage, older_than_days=30)

    assert report.candidates == 1
    assert report.deleted == 0
    assert orphan.exists()


def test_orphan_collection_deletes_old_but_preserves_recent_blobs(app_ctx, tmp_path):
    storage = LocalDiagramStorage(tmp_path)
    orphan = tmp_path / 'assets/sha256/aa/orphan'
    recent = tmp_path / 'assets/sha256/bb/recent'
    orphan.parent.mkdir(parents=True)
    recent.parent.mkdir(parents=True)
    orphan.write_bytes(b'orphan')
    recent.write_bytes(b'recent')
    old = (datetime.now(timezone.utc) - timedelta(days=40)).timestamp()
    os.utime(orphan, (old, old))
    report = collect_orphan_blobs(storage=storage, older_than_days=30, execute=True)

    assert report.candidates == report.deleted == 1
    assert not orphan.exists()
    assert recent.exists()
