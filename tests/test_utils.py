import pytest
import types
from core.utils import (
    sanitize_html,
    extract_text,
    extract_text_from_image,
    extract_text_from_pdf,
)


def test_sanitize_html_removes_disallowed_tags():
    html = (
        "<p>Hello <strong>World</strong> <script>alert('x')</script> "
        "<span style='color:red'>color</span> <a href='https://example.com'>link</a> "
        "<div>divcontent</div></p>"
    )
    cleaned = sanitize_html(html)
    assert "<strong>World</strong>" in cleaned
    assert "<a href" in cleaned
    assert "<script" not in cleaned
    assert "<span" not in cleaned
    assert "<div" not in cleaned


def test_extract_text_image_pdf(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    img1 = Image.new("RGB", (10, 10), color="white")
    img2 = Image.new("RGB", (10, 10), color="black")
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: [img1, img2])

    calls = []

    def dummy_image_to_string(img, **kwargs):
        calls.append(img)
        return "Texto1" if len(calls) == 1 else "Texto2"

    monkeypatch.setattr("core.utils.pytesseract", types.SimpleNamespace(image_to_string=dummy_image_to_string))
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    text = extract_text(str(pdf_file))

    assert "Texto1" in text
    assert "Texto2" in text
    assert len(calls) == 2


def test_extract_text_from_image_custom_config(monkeypatch):
    from PIL import Image

    img = Image.new("RGB", (10, 10), color="white")
    captured = {}

    def dummy_image_to_string(img, lang, config):
        captured["config"] = config
        return ""

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=dummy_image_to_string),
    )

    extract_text_from_image(img, oem="1", psm="4")
    assert captured["config"] == "--oem 1 --psm 4"


def test_extract_text_from_pdf_uses_env(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    img = Image.new("RGB", (10, 10), color="white")
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: [img])

    captured = {}

    def dummy_image_to_string(img, lang, config):
        captured["config"] = config
        return "texto"

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=dummy_image_to_string),
    )
    monkeypatch.setenv("OCR_OEM", "1")
    monkeypatch.setenv("OCR_PSM", "4")

    extract_text_from_pdf(str(pdf_file))
    assert captured["config"] == "--oem 1 --psm 4"
