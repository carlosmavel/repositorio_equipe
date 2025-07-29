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

    img1 = object()
    img2 = object()
    monkeypatch.setattr("utils.convert_from_path", lambda p, dpi=200: [img1, img2])

    calls = []

    class DummyOCR:
        def ocr(self, img, **kwargs):
            calls.append(img)
            return [[None, ("Texto1" if len(calls) == 1 else "Texto2", 1.0)]]

    monkeypatch.setattr("utils.get_ocr_engine", lambda: DummyOCR())
    monkeypatch.setattr("utils.np", types.SimpleNamespace(array=lambda x: x))
    monkeypatch.setattr("utils.Image", object())

    text = extract_text(str(pdf_file))

    assert "Texto1" in text
    assert "Texto2" in text
    assert len(calls) == 2
