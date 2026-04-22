try:
    from core.database import db
    from core.models import Funcao
    from core.permission_catalog import CATALOG
    from core import permission_catalog
    from core.services.permission_sync import sync_permission_catalog, sync_permission_catalog_with_lock
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.database import db
    from ..core.models import Funcao
    from ..core.permission_catalog import CATALOG
    from ..core import permission_catalog
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
    assert updated.managed_by_system is True


def test_sync_permission_catalog_with_lock_falls_back_for_non_postgres(app_ctx):
    result = sync_permission_catalog_with_lock(db.session)
    db.session.commit()

    assert result is not None
    assert result.created == len(CATALOG)


def test_sync_permission_catalog_does_not_change_custom_permissions(app_ctx):
    custom = Funcao(codigo="custom_exportar", nome="Exportar customizado", managed_by_system=False)
    db.session.add(custom)
    db.session.commit()

    result = sync_permission_catalog(db.session)
    db.session.commit()

    assert result.created == len(CATALOG)

    preserved = Funcao.query.filter_by(codigo="custom_exportar").one()
    assert preserved.nome == "Exportar customizado"
    assert preserved.managed_by_system is False


def test_sync_permission_catalog_raises_for_implicit_code_changes(app_ctx):
    orphan_managed = Funcao(codigo="codigo_antigo_sem_regra", nome="Legado", managed_by_system=True)
    db.session.add(orphan_managed)
    db.session.commit()

    try:
        sync_permission_catalog(db.session)
    except RuntimeError as exc:
        assert "sem regra explícita" in str(exc)
    else:
        raise AssertionError("Era esperado erro para código gerenciado sem alias/deprecated")


def test_sync_permission_catalog_applies_alias_renaming(app_ctx):
    item = CATALOG[0]
    alias_code = f"legacy_{item.codigo}"
    permission_catalog.CODE_ALIASES[alias_code] = item.codigo

    try:
        db.session.add(Funcao(codigo=alias_code, nome="Nome legado", managed_by_system=True))
        db.session.commit()

        result = sync_permission_catalog(db.session)
        db.session.commit()

        assert result.updated >= 1
        migrated = Funcao.query.filter_by(codigo=item.codigo).one_or_none()
        assert migrated is not None
        assert migrated.nome == item.nome
    finally:
        permission_catalog.CODE_ALIASES.pop(alias_code, None)
