import pytest

from utils import sanitize_html, extract_text
import types


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

    class DummyPage:
        def extract_text(self):
            return None

    class DummyReader:
        def __init__(self, path):
            pass

        @property
        def pages(self):
            return [DummyPage(), DummyPage()]

    monkeypatch.setattr("utils.PdfReader", DummyReader)
    monkeypatch.setattr("utils.convert_from_path", lambda path: ["img1", "img2"])

    calls = []

    def fake_ocr(img):
        calls.append(img)
        return "Texto1" if img == "img1" else "Texto2"

    monkeypatch.setattr("utils.pytesseract.image_to_string", fake_ocr)

    text = extract_text(str(pdf_file))

    assert "Texto1" in text
    assert "Texto2" in text
    assert calls == ["img1", "img2"]
