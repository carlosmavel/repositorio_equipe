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
    assert len(calls) >= 2


def test_extract_text_custom_dpi(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    captured = {}

    def dummy_convert(p, dpi=0):
        captured["dpi"] = dpi
        return [Image.new("RGB", (10, 10))]

    monkeypatch.setattr("core.utils.convert_from_path", dummy_convert)
    monkeypatch.setattr(
        "core.utils.pytesseract", types.SimpleNamespace(image_to_string=lambda *a, **k: "texto")
    )
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    extract_text(str(pdf_file), pdf_dpi=200)

    assert captured["dpi"] == 200


def test_extract_text_env_dpi(monkeypatch, tmp_path):

    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    captured = {}

    def dummy_convert(p, dpi=0):
        captured["dpi"] = dpi
        return [Image.new("RGB", (10, 10))]

    monkeypatch.setattr("core.utils.convert_from_path", dummy_convert)
    monkeypatch.setattr(
        "core.utils.pytesseract", types.SimpleNamespace(image_to_string=lambda *a, **k: "texto")
    )
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)
    monkeypatch.setenv("PDF_OCR_DPI", "250")

    extract_text(str(pdf_file))

    assert captured["dpi"] == 250


def test_extract_text_pdf_preprocess_options(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    from PIL import Image

    monkeypatch.setattr(
        "core.utils.convert_from_path", lambda p, dpi=300: [Image.new("RGB", (10, 10))]
    )
    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=lambda *a, **k: "texto"),
    )

    captured = {}

    def dummy_preprocess(img, **kwargs):
        captured.update(kwargs)
        return img

    monkeypatch.setattr("core.utils.preprocess_image", dummy_preprocess)

    extract_text_from_pdf(
        str(pdf_file), apply_sharpen=False, apply_threshold=False, lang="por"
    )

    assert captured["apply_sharpen"] is False
    assert captured["apply_threshold"] is False


def test_extract_text_image_multiple_passes(monkeypatch):
    from PIL import Image

    calls: list[str] = []

    def dummy_image_to_string(img, lang="por", config=""):
        calls.append(config)
        return "texto"

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=dummy_image_to_string),
    )

    img = Image.new("RGB", (10, 10), color="white")
    cfg = {"multiple_passes": [{"psm": "6"}, {"psm": "11"}]}

    extract_text_from_image(img, config=cfg)

    assert len(calls) == 2
    assert any("--psm 6" in c for c in calls)
    assert any("--psm 11" in c for c in calls)


def test_extract_text_pdf_mixed_native_and_ocr(monkeypatch, tmp_path):
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    class DummyPage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class DummyReader:
        def __init__(self, path):
            self.pages = [DummyPage("Texto nativo"), DummyPage("")]

    monkeypatch.setattr("core.utils.PdfReader", DummyReader)

    from PIL import Image

    convert_calls = []

    def dummy_convert(path, dpi=300, first_page=1, last_page=1):
        convert_calls.append((first_page, last_page))
        assert first_page == last_page == 2
        return [Image.new("RGB", (10, 10), color="white")]

    monkeypatch.setattr("core.utils.convert_from_path", dummy_convert)
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    def dummy_image_to_string(img, **kwargs):
        return "Texto OCR"

    monkeypatch.setattr(
        "core.utils.pytesseract",
        types.SimpleNamespace(image_to_string=dummy_image_to_string),
    )

    text = extract_text_from_pdf(str(pdf_file))

    assert "Texto nativo" in text
    assert "Texto OCR" in text
    assert len(convert_calls) == 1
