import pytest

import types
from core.utils import sanitize_html, extract_text, select_best_psm


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

    def dummy_extract(img, lang="por"):
        calls.append(img)
        return ("Texto1" if len(calls) == 1 else "Texto2", {"best_psm": 6, "candidates": []})

    monkeypatch.setattr("core.utils.extract_text_from_image", dummy_extract)
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)
    monkeypatch.setattr("core.utils.pytesseract", object())

    text = extract_text(str(pdf_file))

    assert "Texto1" in text
    assert "Texto2" in text
    assert len(calls) == 2

def test_extract_text_mixed_pdf(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy2.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    class DummyPage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class DummyReader:
        def __init__(self, path):
            self.pages = [DummyPage("Native"), DummyPage("")]

    monkeypatch.setattr("core.utils.PdfReader", DummyReader)
    images = [Image.new("RGB", (10, 10), color="white"), Image.new("RGB", (10, 10), color="white")]
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: images)
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)
    monkeypatch.setattr(
        "core.utils.extract_text_from_image",
        lambda img, lang="por": ("OCR", {"best_psm": 6, "candidates": []}),
    )
    monkeypatch.setattr("core.utils.pytesseract", object())

    text = extract_text(str(pdf_file))
    assert text.splitlines() == ["Native", "OCR"]


def test_select_best_psm(monkeypatch):
    data = {
        3: {"conf": ["10", "20", "-1"], "text": ["a", "b", ""]},
        6: {"conf": ["30", "30"], "text": ["c", ""]},
    }

    def fake_image_to_data(image, lang, config, output_type):
        psm = int(config.split()[-1])
        return data[psm]

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(
            image_to_data=fake_image_to_data,
            Output=types.SimpleNamespace(DICT=None),
        ),
    )

    best_psm, stats = select_best_psm(None, "por", [3, 6])
    assert best_psm == 6
    assert stats == [(3, 15.0, 2), (6, 30.0, 1)]

