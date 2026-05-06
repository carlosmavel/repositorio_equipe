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


def test_sanitize_html_allows_quill_headings_lists_and_formatting():
    html = (
        '<h1>Título</h1><h2>Seção</h2><h3>Subseção</h3>'
        '<p class="ql-align-center">Texto <b>negrito</b> '
        '<i>itálico</i> <u>sublinhado</u></p>'
        '<ul><li class="ql-indent-1">Item</li></ul>'
        '<ol><li>Primeiro</li></ol>'
        '<blockquote>Citação</blockquote>'
    )

    cleaned = sanitize_html(html)

    assert '<h1>Título</h1>' in cleaned
    assert '<h2>Seção</h2>' in cleaned
    assert '<h3>Subseção</h3>' in cleaned
    assert (
        '<p class="ql-align-center">Texto <b>negrito</b> '
        '<i>itálico</i> <u>sublinhado</u></p>'
    ) in cleaned
    assert '<ul><li class="ql-indent-1">Item</li></ul>' in cleaned
    assert '<ol><li>Primeiro</li></ol>' in cleaned
    assert '<blockquote>Citação</blockquote>' in cleaned


def test_sanitize_html_allows_safe_links_and_blocks_javascript():
    html = (
        '<a href="https://example.com" title="Site" target="_blank" '
        'rel="noopener noreferrer">seguro</a>'
        '<a href="javascript:alert(1)" title="Ataque">perigoso</a>'
        '<a href="data:text/html;base64,PGgxPkF0YXF1ZTwvaDE+">data</a>'
    )

    cleaned = sanitize_html(html)

    assert (
        '<a href="https://example.com" title="Site" target="_blank" '
        'rel="noopener noreferrer">seguro</a>'
    ) in cleaned
    assert '<a title="Ataque">perigoso</a>' in cleaned
    assert '<a>data</a>' in cleaned
    assert 'javascript:' not in cleaned
    assert 'data:text/html' not in cleaned


def test_sanitize_html_removes_inline_events_and_styles():
    html = (
        '<p onclick="alert(1)" style="color:red">Texto</p>'
        '<img src="https://example.com/image.png" onerror="alert(1)" '
        'style="width:100px" alt="Imagem">'
        '<iframe src="https://example.com"></iframe>'
    )

    cleaned = sanitize_html(html)

    assert '<p>Texto</p>' in cleaned
    assert '<img src="https://example.com/image.png" alt="Imagem">' in cleaned
    assert 'onclick' not in cleaned
    assert 'onerror' not in cleaned
    assert 'style=' not in cleaned
    assert '<iframe' not in cleaned


def test_sanitize_html_allows_safe_png_data_image_only_on_img_src():
    html = (
        '<img src="data:image/png;base64,iVBORw0KGgo=" alt="PNG" '
        'title="Imagem" width="120" height="80">'
        '<a href="data:image/png;base64,iVBORw0KGgo=">link</a>'
        '<img src="data:image/svg+xml;base64,PHN2Zy8+" alt="SVG">'
    )

    cleaned = sanitize_html(html)

    assert (
        '<img src="data:image/png;base64,iVBORw0KGgo=" alt="PNG" '
        'title="Imagem" width="120" height="80">'
    ) in cleaned
    assert '<a>link</a>' in cleaned
    assert '<img alt="SVG">' in cleaned
    assert 'data:image/svg+xml' not in cleaned


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
    assert text == "Texto1\nTexto2"


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
