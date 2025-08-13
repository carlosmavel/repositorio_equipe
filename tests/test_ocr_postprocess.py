import types
import os
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
