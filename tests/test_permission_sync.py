try:
    from core.database import db
    from core.models import Funcao
    from core.permission_catalog import CATALOG
    from core.services.permission_sync import sync_permission_catalog, sync_permission_catalog_with_lock
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.database import db
    from ..core.models import Funcao
    from ..core.permission_catalog import CATALOG
    from ..core.services.permission_sync import sync_permission_catalog, sync_permission_catalog_with_lock


def test_sync_permission_catalog_is_idempotent_and_updates_managed_fields(app_ctx):
    result_first = sync_permission_catalog(db.session)
    db.session.commit()

    assert result_first.created == len(CATALOG)
    assert result_first.updated == 0
    assert result_first.unchanged == 0

    item = CATALOG[0]
    func = Funcao.query.filter_by(codigo=item.codigo).first()
    assert func is not None

    func.nome = "Nome divergente"
    db.session.commit()

    result_second = sync_permission_catalog(db.session)
    db.session.commit()

    assert result_second.created == 0
    assert result_second.updated == 1
    assert result_second.unchanged == len(CATALOG) - 1

    updated = Funcao.query.filter_by(codigo=item.codigo).first()
    assert updated is not None
    assert updated.nome == item.nome


def test_sync_permission_catalog_with_lock_falls_back_for_non_postgres(app_ctx):
    result = sync_permission_catalog_with_lock(db.session)
    db.session.commit()

    assert result is not None
    assert result.created == len(CATALOG)
