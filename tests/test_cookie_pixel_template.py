from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = ROOT / "templates" / "base.html"


def test_meta_pixel_loader_uses_safe_fbq_guard():
    source = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert "ensureSafeFacebookPixelStub" in source
    assert "typeof window.fbq === \"function\"" in source
    assert "ensureSafeFacebookPixelStub(placeholderScript.dataset.src);" in source
    assert 'data-src="https://connect.facebook.net/en_US/fbevents.js"' in source
