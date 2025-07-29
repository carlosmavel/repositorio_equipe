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

    calls = []
    def fake_convert(path, **kwargs):
        calls.append(("convert", kwargs))
        return ["img1", "img2"]

    monkeypatch.setattr("utils.convert_from_path", fake_convert)

    class FakeOCR:
        def ocr(self, img, **kwargs):
            calls.append(img)
            if img == "img1":
                return [[(None, ("", "Texto1"))]]
            return [[(None, ("", "Texto2"))]]

    monkeypatch.setattr("utils.paddle_ocr", FakeOCR())
    monkeypatch.setattr("utils.np", types.SimpleNamespace(array=lambda x: x))

    text = extract_text(str(pdf_file))

    assert "Texto1" in text
    assert "Texto2" in text
    assert calls == [("convert", {"poppler_path": None}), "img1", "img2"]
