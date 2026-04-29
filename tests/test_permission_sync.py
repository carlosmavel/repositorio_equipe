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


def _assert_catalog_matches_database():
    assert Funcao.query.filter_by(managed_by_system=True).count() >= len(CATALOG)

    for item in CATALOG:
        row = Funcao.query.filter_by(codigo=item.codigo).one_or_none()
        assert row is not None
        assert row.nome == item.nome
        assert row.managed_by_system is True


def test_sync_permission_catalog_base_vazia_cria_catalogo_completo(app_ctx):
    result = sync_permission_catalog(db.session)
    db.session.commit()

    assert result.created == len(CATALOG)
    assert result.updated == 0
    assert result.unchanged == 0
    _assert_catalog_matches_database()


def test_sync_permission_catalog_base_parcial_completa_sem_duplicar(app_ctx):
    parciais = [
        Funcao(codigo=CATALOG[0].codigo, nome=CATALOG[0].nome, managed_by_system=True),
        Funcao(codigo=CATALOG[1].codigo, nome=CATALOG[1].nome, managed_by_system=True),
    ]
    db.session.add_all(parciais)
    db.session.commit()

    result = sync_permission_catalog(db.session)
    db.session.commit()

    assert result.created == len(CATALOG) - len(parciais)
    assert result.updated == 0
    assert result.unchanged == len(parciais)
    assert Funcao.query.filter_by(codigo=CATALOG[0].codigo).count() == 1
    assert Funcao.query.filter_by(codigo=CATALOG[1].codigo).count() == 1
    _assert_catalog_matches_database()


def test_sync_permission_catalog_atualiza_nomes_desatualizados(app_ctx):
    item = CATALOG[0]
    db.session.add(Funcao(codigo=item.codigo, nome="Nome divergente", managed_by_system=True))
    db.session.commit()

    result = sync_permission_catalog(db.session)
    db.session.commit()

    assert result.created == len(CATALOG) - 1
    assert result.updated == 1
    assert result.unchanged == 0

    atualizada = Funcao.query.filter_by(codigo=item.codigo).one()
    assert atualizada.nome == item.nome
    assert atualizada.managed_by_system is True


def test_sync_permission_catalog_idempotencia_duas_execucoes_estado_final_igual(app_ctx):
    primeiro = sync_permission_catalog(db.session)
    db.session.commit()
    snapshot_1 = {(row.codigo, row.nome, row.managed_by_system) for row in Funcao.query.order_by(Funcao.codigo).all()}

    segundo = sync_permission_catalog(db.session)
    db.session.commit()
    snapshot_2 = {(row.codigo, row.nome, row.managed_by_system) for row in Funcao.query.order_by(Funcao.codigo).all()}

    assert primeiro.created == len(CATALOG)
    assert segundo.created == 0
    assert segundo.updated == 0
    assert segundo.unchanged == len(CATALOG)
    assert snapshot_1 == snapshot_2
    _assert_catalog_matches_database()


def test_sync_permission_catalog_with_lock_falls_back_for_non_postgres(app_ctx):
    result = sync_permission_catalog_with_lock(db.session)
    db.session.commit()

    assert result is not None
    assert result.created == len(CATALOG)


def test_sync_permission_catalog_preserva_permissao_custom_fora_catalogo(app_ctx):
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


def test_sync_permission_catalog_contains_artigo_excluir_definitivo(app_ctx):
    result = sync_permission_catalog(db.session)
    db.session.commit()

    assert result.created == len(CATALOG)
    perm = Funcao.query.filter_by(codigo="artigo_excluir_definitivo").one_or_none()
    assert perm is not None
    assert perm.managed_by_system is True


def test_sync_permission_catalog_contains_boletim_permissions(app_ctx):
    result = sync_permission_catalog(db.session)
    db.session.commit()

    assert result.created == len(CATALOG)

    expected = {
        "boletim_visualizar": "Boletim visualizar",
        "boletim_buscar": "Boletim buscar",
        "boletim_gerenciar": "Boletim gerenciar",
    }

    for codigo, nome in expected.items():
        perm = Funcao.query.filter_by(codigo=codigo).one_or_none()
        assert perm is not None
        assert perm.nome == nome
        assert perm.managed_by_system is True
