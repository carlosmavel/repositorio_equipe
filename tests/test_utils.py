import os
import pytest

import types
from core.utils import (
    sanitize_html,
    extract_text,
    select_best_psm,
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

    calls = []

    def dummy_select(img, lang, psms):
        calls.append(img)
        return 6, [(6, 0.0, 1)]

    monkeypatch.setattr("core.utils.select_best_psm", dummy_select)
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    def dummy_to_string(img, lang, config):
        return "Texto1" if img is img1 else "Texto2"

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=dummy_to_string),
    )

    text, meta = extract_text(str(pdf_file))

    assert "Texto1" in text
    assert "Texto2" in text
    assert len(calls) == 2
    assert meta[0]["best_psm"] == 6
    assert meta[1]["page"] == 2

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
    monkeypatch.setattr("core.utils.select_best_psm", lambda img, lang, psms: (6, [(6, 0.0, 1)]))
    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=lambda img, lang, config: "OCR"),
    )

    text, meta = extract_text(str(pdf_file))
    assert text.splitlines() == ["Native", "OCR"]
    assert meta[1]["best_psm"] == 6


def test_extract_text_pdf_missing_page(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy_missing.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    class DummyPage:
        def extract_text(self):
            return ""

    class DummyReader:
        def __init__(self, path):
            self.pages = [DummyPage(), DummyPage()]

    monkeypatch.setattr("core.utils.PdfReader", DummyReader)
    images = [Image.new("RGB", (10, 10), color="white")]
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: images)
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)
    monkeypatch.setattr(
        "core.utils.select_best_psm", lambda img, lang, psms: (6, [(6, 0.0, 1)])
    )
    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=lambda img, lang, config: "OCR"),
    )

    text, meta = extract_text(str(pdf_file))
    assert text.splitlines() == ["OCR"]
    assert len(meta) == 2
    assert meta[1]["conversion_failed"] is True


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


@pytest.mark.skipif(not os.getenv("OCR_TEST_FILE"), reason="OCR_TEST_FILE not set")
def test_extract_text_integration(tmp_path):
    path = os.getenv("OCR_TEST_FILE")
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        text, meta = extract_text(path)
        assert text.strip()
        assert meta and meta[0]["best_psm"] is not None

        from pdf2image import convert_from_path

        images = convert_from_path(path, dpi=300)
        rotated = images[0].rotate(90, expand=True)
        text_rot, meta_rot = extract_text_from_image(rotated)
        assert text_rot.strip()
        assert meta_rot["best_psm"] is not None
        assert meta_rot["angle"] != 0
    else:
        from PIL import Image

        img = Image.open(path)
        text, meta = extract_text_from_image(img)
        assert text.strip()
        assert meta["best_psm"] is not None

        rotated = img.rotate(90, expand=True)
        text_rot, meta_rot = extract_text_from_image(rotated)
        assert text_rot.strip()
        assert meta_rot["best_psm"] is not None
        assert meta_rot["angle"] != 0

