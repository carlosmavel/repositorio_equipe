import os
import types
import pytest
from core.utils import (
    sanitize_html,
    extract_text,
    extract_text_from_image,
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
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    def dummy_to_string(img, lang, config):
        return "Texto1" if img is img1 else "Texto2"

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=dummy_to_string),
    )

    text = extract_text(str(pdf_file))
    assert "Texto1" in text
    assert "Texto2" in text


def test_extract_text_from_image_simple(monkeypatch):
    from PIL import Image

    img = Image.new("RGB", (10, 10), color="white")
    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=lambda img, lang, config: "Hello"),
    )
    assert extract_text_from_image(img) == "Hello"


@pytest.mark.skipif(not os.getenv("OCR_TEST_FILE"), reason="OCR_TEST_FILE not set")
def test_extract_text_integration(tmp_path):
    path = os.getenv("OCR_TEST_FILE")
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        text = extract_text(path)
        assert text.strip()

        from pdf2image import convert_from_path

        images = convert_from_path(path, dpi=300)
        rotated = images[0].rotate(90, expand=True)
        text_rot = extract_text_from_image(rotated)
        assert text_rot.strip()
    else:
        from PIL import Image

        img = Image.open(path)
        text = extract_text_from_image(img)
        assert text.strip()

        rotated = img.rotate(90, expand=True)
        text_rot = extract_text_from_image(rotated)
        assert text_rot.strip()
