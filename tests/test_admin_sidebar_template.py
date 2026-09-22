from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")


def _collapse_fragment(collapse_id):
    marker = f'id="{collapse_id}"'
    start = BASE_TEMPLATE.index(marker)
    return BASE_TEMPLATE[start : start + 7000]


def test_admin_sidebar_has_nested_groups_and_unique_accessible_toggles():
    for collapse_id in (
        "collapseAdministracao",
        "collapseCadastros",
        "collapseCadastrosArtigos",
        "collapseSeguranca",
    ):
        assert BASE_TEMPLATE.count(f'id="{collapse_id}"') == 1
        assert f'data-bs-target="#{collapse_id}"' in BASE_TEMPLATE
        assert f'aria-controls="{collapse_id}"' in BASE_TEMPLATE

    assert '<button class="nav-link sidebar-group-toggle sidebar-nested-toggle' in BASE_TEMPLATE
    assert 'id="collapseCadastros" data-bs-parent=' not in BASE_TEMPLATE
    assert 'id="collapseCadastrosArtigos" data-bs-parent=' not in BASE_TEMPLATE
    assert 'id="collapseSeguranca" data-bs-parent=' not in BASE_TEMPLATE


def test_admin_sidebar_groups_destinations_under_the_expected_ancestors():
    administration = _collapse_fragment("collapseAdministracao")
    cadastros = _collapse_fragment("collapseCadastros")
    artigos = _collapse_fragment("collapseCadastrosArtigos")
    seguranca = _collapse_fragment("collapseSeguranca")

    assert administration.index("Dashboard Admin") < administration.index("Cadastros")
    for label in ("Instituições", "Estabelecimentos", "Setores", "Células", "Cargos"):
        assert label in cadastros[: cadastros.index('id="collapseCadastrosArtigos"')]
    for label in ("Tipos de Artigo", "Áreas", "Sistemas"):
        assert label in artigos
    assert "Gerenciar Usuários" in seguranca


def test_active_article_route_expands_every_ancestor_and_marks_only_destination():
    assert "{% set cadastros_artigos_active = current_endpoint in" in BASE_TEMPLATE
    assert "'admin_artigo_tipos', 'admin_artigo_areas', 'admin_artigo_sistemas'" in BASE_TEMPLATE
    assert "{% set cadastros_active = current_endpoint in" in BASE_TEMPLATE

    for active_name, collapse_id in (
        ("admin_menu_active", "collapseAdministracao"),
        ("cadastros_active", "collapseCadastros"),
        ("cadastros_artigos_active", "collapseCadastrosArtigos"),
        ("seguranca_active", "collapseSeguranca"),
    ):
        assert f"collapse {{{{ 'show' if {active_name} }}}}\" id=\"{collapse_id}" in BASE_TEMPLATE
        assert f"aria-expanded=\"{{{{ 'true' if {active_name} else 'false' }}}}\"" in BASE_TEMPLATE

    admin_start = BASE_TEMPLATE.index("{# Bloco ADMINISTRAÇÃO")
    admin_end = BASE_TEMPLATE.index("{# Fim do if admin permission")
    admin_fragment = BASE_TEMPLATE[admin_start:admin_end]
    assert admin_fragment.count('aria-current="page"') == 10
    assert 'aria-current="page"' not in BASE_TEMPLATE[BASE_TEMPLATE.index('title="Cadastros"') : BASE_TEMPLATE.index('id="collapseCadastros"')]
