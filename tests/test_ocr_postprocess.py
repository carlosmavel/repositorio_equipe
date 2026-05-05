import types
from PIL import Image
from core.utils import extract_text_from_pdf


def create_dummy_pdf(path):
    path.write_bytes(b"%PDF-1.4")


def test_reorder_and_clean(monkeypatch, tmp_path):
    pdf = tmp_path / "Ser_Unimed_04_08_2025.pdf"
    create_dummy_pdf(pdf)

    img = Image.new("RGB", (800, 800), "white")
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: [img])
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    dummy_data = {
        "level": [5] * 7,
        "page_num": [1] * 7,
        "block_num": [1] * 7,
        "par_num": [1] * 7,
        "line_num": list(range(1, 8)),
        "word_num": [1] * 7,
        "left": [50, 200, 50, 50, 500, 510, 520],
        "top": [50, 50, 100, 150, 50, 90, 130],
        "width": [100] * 7,
        "height": [20] * 7,
        "conf": [90] * 7,
        "text": [
            "Ser",
            "Unimed",
            "TREINAMENTO DA BRIGADA DE INCÊNDIO",
            "contato@unimed.com",
            "º",
            "|",
            "Segunda do SESMT",
        ],
    }

    class DummyOutput:
        DICT = "DICT"

    def dummy_image_to_data(img, lang, config, output_type):
        return dummy_data

    def dummy_image_to_string(img, lang, config):
        # chamado apenas em detect_sparse quando aplicável
        return "aux"

    pytess = types.SimpleNamespace(
        image_to_data=dummy_image_to_data,
        image_to_string=dummy_image_to_string,
        Output=DummyOutput,
    )
    monkeypatch.setattr("core.utils.pytesseract", pytess)

    text = extract_text_from_pdf(str(pdf), reorder=True, clean=True)
    lines = [l for l in text.splitlines() if l.strip()]
    assert lines[0].startswith("Ser Unimed")
    assert "TREINAMENTO" in text
    assert lines[-1] == "Segunda do SESMT"
    assert "º" not in text and "|" not in text


def test_detect_sparse(monkeypatch, tmp_path):
    pdf = tmp_path / "Ser_Unimed_04_08_2025.pdf"
    create_dummy_pdf(pdf)

    img = Image.new("RGB", (800, 800), "white")
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: [img])
    monkeypatch.setattr("core.utils.preprocess_image", lambda img, **k: img)

    # poucos caracteres para disparar detecção de layout esparso
    dummy_data = {
        "level": [5],
        "page_num": [1],
        "block_num": [1],
        "par_num": [1],
        "line_num": [1],
        "word_num": [1],
        "left": [50],
        "top": [50],
        "width": [20],
        "height": [20],
        "conf": [90],
        "text": ["Teste"],
    }

    class DummyOutput:
        DICT = "DICT"

    def dummy_image_to_data(img, lang, config, output_type):
        return dummy_data

    calls = {"count": 0}

    def dummy_image_to_string(img, lang, config):
        calls["count"] += 1
        return "texto complementar"

    pytess = types.SimpleNamespace(
        image_to_data=dummy_image_to_data,
        image_to_string=dummy_image_to_string,
        Output=DummyOutput,
    )
    monkeypatch.setattr("core.utils.pytesseract", pytess)

    text = extract_text_from_pdf(str(pdf), reorder=True, clean=True, detect_sparse=True)
    assert "texto complementar" in text
    assert calls["count"] == 1

    calls["count"] = 0
    text2 = extract_text_from_pdf(str(pdf), reorder=True, clean=True, detect_sparse=False)
    assert calls["count"] == 0


def test_pdf_direct_text_sufficient_skips_convert_from_path(monkeypatch, tmp_path):
    pdf = tmp_path / "sample.pdf"
    create_dummy_pdf(pdf)

    monkeypatch.setattr("core.utils._get_pdf_total_pages", lambda p: 2)
    monkeypatch.setattr("core.utils._extract_pdf_text_without_ocr", lambda p: "A" * 220)
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: (_ for _ in ()).throw(AssertionError("não deveria chamar OCR por página")))

    result = extract_text_from_pdf(str(pdf), return_metadata=True)
    assert result["method"] == "pdf_direct_text"
    assert result["total_pages"] == 2


def test_pdf_direct_text_low_yield_fallbacks_to_page_ocr(monkeypatch, tmp_path):
    pdf = tmp_path / "scan.pdf"
    create_dummy_pdf(pdf)
    img = Image.new("RGB", (800, 800), "white")
    calls = {"preprocess": 0, "extract": 0}

    monkeypatch.setattr("core.utils._get_pdf_total_pages", lambda p: 4)
    monkeypatch.setattr("core.utils._extract_pdf_text_without_ocr", lambda p: "abc")
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: [img, img, img, img])

    def fake_preprocess(image, **kwargs):
        calls["preprocess"] += 1
        return image

    def fake_extract(image, **kwargs):
        calls["extract"] += 1
        return "texto ocr"

    monkeypatch.setattr("core.utils.preprocess_image", fake_preprocess)
    monkeypatch.setattr("core.utils.extract_text_from_image", fake_extract)

    result = extract_text_from_pdf(str(pdf), return_metadata=True)
    assert result["method"] == "pdf_ocr_page_by_page"
    assert result["total_pages"] == 4
    assert calls["preprocess"] == 4
    assert calls["extract"] == 4


def test_total_pages_comes_from_pdf_counter_not_newlines(monkeypatch, tmp_path):
    pdf = tmp_path / "lines.pdf"
    create_dummy_pdf(pdf)
    monkeypatch.setattr("core.utils._get_pdf_total_pages", lambda p: 4)
    monkeypatch.setattr("core.utils._extract_pdf_text_without_ocr", lambda p: "linha1\nlinha2\nlinha3\nlinha4\nlinha5\n" + ("x" * 250))
    monkeypatch.setattr("core.utils.convert_from_path", lambda p, dpi=300: (_ for _ in ()).throw(AssertionError("não deveria chamar OCR por página")))

    result = extract_text_from_pdf(str(pdf), return_metadata=True)
    assert result["total_pages"] == 4
