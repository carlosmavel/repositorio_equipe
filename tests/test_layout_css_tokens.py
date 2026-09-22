from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = ROOT / "templates" / "base.html"
CUSTOM_CSS = ROOT / "static" / "css" / "custom.css"
FUTURISTIC_CSS = ROOT / "static" / "css" / "futuristic.css"


def _source(path):
    return path.read_text(encoding="utf-8")


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
