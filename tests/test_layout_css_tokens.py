from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = ROOT / "templates" / "base.html"
CUSTOM_CSS = ROOT / "static" / "css" / "custom.css"
FUTURISTIC_CSS = ROOT / "static" / "css" / "futuristic.css"
MAIN_JS = ROOT / "static" / "js" / "main.js"


def _source(path):
    return path.read_text(encoding="utf-8")


def test_saved_dark_theme_is_restored_in_head_before_stylesheets_load():
    template = _source(BASE_TEMPLATE)
    head = template.split("<head>", 1)[1].split("</head>", 1)[0]
    theme_restore = "localStorage.getItem('theme') === 'dark'"

    assert theme_restore in head
    assert "document.documentElement.setAttribute('data-bs-theme', 'dark')" in head
    assert head.index(theme_restore) < head.index('<link href="https://cdn.jsdelivr.net/npm/bootstrap')


def test_native_color_scheme_tracks_the_selected_theme():
    css = _source(FUTURISTIC_CSS)

    root = css.split(":root {", 1)[1].split("}", 1)[0]
    dark = css.split('[data-bs-theme="dark"] {', 1)[1].split("}", 1)[0]

    assert "color-scheme: light" in root
    assert "color-scheme: dark" in dark


def test_scrollbars_have_theme_tokens_and_cross_browser_rules():
    css = _source(FUTURISTIC_CSS)
    root = css.split(":root {", 1)[1].split("}", 1)[0]
    dark = css.split('[data-bs-theme="dark"] {', 1)[1].split("}", 1)[0]

    for token in ("--oq-scrollbar-track", "--oq-scrollbar-thumb"):
        assert token in root
        assert token in dark

    assert "@media (hover: hover) and (pointer: fine)" in css
    shared_selector = ":where(.app-scrollbar, #osNotificationMenu, .editor-container)"
    assert shared_selector in css
    assert f"{shared_selector}::-webkit-scrollbar" in css
    assert "scrollbar-width: auto" in css
    assert "scrollbar-color:" in css
    assert "::-webkit-scrollbar {" in css
    assert "::-webkit-scrollbar-track {" in css
    assert "::-webkit-scrollbar-thumb {" in css
    assert "width: 12px" in css
    assert "height: 12px" in css
    assert "min-height: 44px" in css
    assert "border: 3px solid transparent" in css
    assert "border-radius: 999px" in css


def test_scrollbar_indicator_color_is_constant_during_interaction():
    css = _source(FUTURISTIC_CSS)
    root = css.split(":root {", 1)[1].split("}", 1)[0]
    dark = css.split('[data-bs-theme="dark"] {', 1)[1].split("}", 1)[0]
    scrollbar_rules = css.split("@media (hover: hover) and (pointer: fine) {", 1)[1].split("\n}", 1)[0]

    # A single indicator token per theme keeps its color identical in the
    # normal, hover and focus states whenever an overlay scrollbar is visible.
    assert root.count("--oq-scrollbar-thumb:") == 1
    assert dark.count("--oq-scrollbar-thumb:") == 1
    assert "--oq-scrollbar-thumb-hover" not in css
    assert "--oq-scrollbar-thumb-focus" not in css
    assert "scrollbar-color: var(--oq-scrollbar-thumb) var(--oq-scrollbar-track)" in scrollbar_rules
    assert "background: var(--oq-scrollbar-thumb) padding-box" in scrollbar_rules

    for state in (":hover", ":focus-visible", ":focus-within"):
        assert f"{state} {{\n    scrollbar-color:" not in scrollbar_rules
        assert f"{state}::-webkit-scrollbar-thumb" not in scrollbar_rules


def test_all_scrollable_application_containers_use_shared_scrollbar_utility():
    templates = {
        "base": _source(BASE_TEMPLATE),
        "new_article": _source(ROOT / "templates" / "artigos" / "novo_artigo.html"),
        "edit_article": _source(ROOT / "templates" / "artigos" / "editar_artigo.html"),
        "bulletin": _source(ROOT / "templates" / "boletins" / "visualizar.html"),
    }

    assert '<html lang="pt-br" class="app-scrollbar' in templates["base"]
    assert 'class="offcanvas offcanvas-start app-scrollbar"' in templates["base"]
    assert 'class="dropdown-menu dropdown-menu-end app-scrollbar" id="notificationMenu"' in templates["base"]
    assert 'class="modal-body app-scrollbar"' in templates["base"]

    all_templates = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "templates").rglob("*.html"))
    assert all_templates.count('class="modal-body') == all_templates.count('class="modal-body app-scrollbar')

    for name in ("new_article", "edit_article"):
        assert 'class="processing-messages app-scrollbar ' in templates[name]
        assert 'class="tiptap-toolbar app-scrollbar ' in templates[name]
        assert 'class="tiptap-editor app-scrollbar ' in templates[name]

    assert 'class="border rounded boletim-ocr-text app-scrollbar p-3"' in templates["bulletin"]
    assert "overflow-y: auto" not in templates["bulletin"]

    custom_css = _source(CUSTOM_CSS)
    ocr_rule = custom_css.split(".boletim-ocr-text {", 1)[1].split("}", 1)[0]
    assert "max-height: 380px" in ocr_rule
    assert "overflow-y: auto" in ocr_rule
    assert "white-space: pre-wrap" in ocr_rule

    # These legacy containers currently have no dedicated template markup, but
    # remain aliases of the utility and therefore receive the same theme tokens.
    css = _source(FUTURISTIC_CSS)
    assert "#osNotificationMenu" in css
    assert ".editor-container" in css


def test_app_chrome_dimensions_have_one_source_of_truth():
    css = _source(FUTURISTIC_CSS)

    assert css.count("--oq-topbar-height: 72px") == 1
    assert css.count("--oq-sidebar-width: 268px") == 1
    assert "padding-top: var(--oq-topbar-height)" in css
    assert "height: var(--oq-topbar-height)" in css
    assert "top: var(--oq-topbar-height)" in css
    assert "height: calc(100dvh - var(--oq-topbar-height))" in css
    assert "padding-left: var(--oq-sidebar-width)" in css
    assert "width: var(--oq-sidebar-width)" in css


def test_desktop_offsets_are_scoped_to_bootstrap_lg_breakpoint():
    css = _source(FUTURISTIC_CSS)
    breakpoint = "@media (min-width: 992px) {"
    desktop_start = css.index(breakpoint)
    desktop_end = css.index("#globalSidebarOffcanvas .offcanvas-header {", desktop_start)
    desktop = css[desktop_start:desktop_end]

    assert "padding-left: var(--oq-sidebar-width)" in desktop
    assert "top: var(--oq-topbar-height)" in desktop
    assert "padding-left" not in css[:desktop_start]


def test_legacy_inline_and_theme_chrome_rules_are_removed():
    template = _source(BASE_TEMPLATE)
    inline_style = template.split("<style>", 1)[1].split("</style>", 1)[0]
    custom_css = _source(CUSTOM_CSS)

    assert "#globalSidebarOffcanvas" not in inline_style
    assert "has-sidebar-layout" not in inline_style
    assert "Navbar and sidebar colors" not in custom_css
    assert "#globalSidebarOffcanvas" not in custom_css


def test_topbar_controls_and_account_menu_are_accessible():
    template = _source(BASE_TEMPLATE)
    css = _source(FUTURISTIC_CSS)

    assert '<button class="nav-link position-relative" type="button" id="notificationDropdown"' in template
    assert 'aria-label="Abrir notificações"' in template
    assert 'id="notificationBadge"' in template
    assert 'aria-live="polite"' in template
    assert 'id="accountDropdown"' in template
    assert 'aria-label="Abrir menu da conta de {{ current_user.username }}"' in template
    assert '>Meu perfil</a>' in template
    assert '>Sair</a>' in template
    assert 'aria-label="Fechar"' in template

    assert ".app-topbar .account-menu-toggle { min-width: 44px; min-height: 44px; }" in css
    assert ".app-topbar .dropdown-item:focus-visible" in css
    assert "#notificationMenu {" in css
    assert "overflow-y: auto" in css
    assert "overflow-wrap: anywhere" in css


def test_sidebar_has_labeled_groups_and_nested_admin_semantics():
    template = _source(BASE_TEMPLATE)

    for label in ("Visão geral", "Conteúdo", "Operações", "Administração"):
        assert f'<span class="sidebar-section-label">{label}</span>' in template

    assert 'data-bs-parent="#sidebarNavigation"' in template
    assert 'aria-current="page"' in template
    assert 'id="collapseCadastros"' in template
    assert 'id="collapseCadastrosArtigos"' in template
    assert 'id="collapseSeguranca"' in template
    assert '<hr class="my-2">' not in template
    assert "sidebar-nested-toggle" in template


def test_sidebar_compact_mode_is_desktop_only_persistent_and_accessible():
    template = _source(BASE_TEMPLATE)
    css = _source(FUTURISTIC_CSS)

    assert "orquetask_sidebar_compact" in template
    assert 'id="sidebarCompactToggle"' in template
    assert 'aria-pressed="false"' in template
    assert "new bootstrap.Tooltip" in template
    assert "html.sidebar-compact #globalSidebarOffcanvas" in css
    assert "@media (max-width: 991.98px)" in css
    assert ".sidebar-compact-toggle { display: none; }" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".sidebar-compact-toggle:focus-visible" in css


def test_sidebar_scroll_is_saved_restored_and_keeps_the_active_link_visible():
    template = _source(BASE_TEMPLATE)
    javascript = _source(MAIN_JS)

    assert 'data-current-user="{{ session.get(\'username\', \'\') }}"' in template
    assert 'data-sidebar-logout="true"' in template
    assert "orquetask_sidebar_scroll_${currentUser}_${viewportMode}" in javascript
    assert "sessionStorage.setItem(scrollKey, String(sidebar.scrollTop))" in javascript
    assert "sessionStorage.getItem(scrollKey)" in javascript
    assert "requestAnimationFrame(() => requestAnimationFrame(restoreSidebarScroll))" in javascript
    assert "sidebar.scrollTop = scrollTop" in javascript
    assert "sidebar.querySelector('[aria-current=\"page\"]')" in javascript
    assert 'scrollIntoView({ block: "nearest", inline: "nearest" })' in javascript
