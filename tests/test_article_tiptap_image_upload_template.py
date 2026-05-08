from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = [
    ROOT / "templates" / "artigos" / "novo_artigo.html",
    ROOT / "templates" / "artigos" / "editar_artigo.html",
]


def _template_sources():
    return {path.name: path.read_text(encoding="utf-8") for path in TEMPLATES}


def test_tiptap_cola_imagens_via_upload_em_vez_de_base64():
    for name, source in _template_sources().items():
        assert "fetch('/artigos/editor-image-upload'" in source, name
        assert "formData.append('file', file, editorImageFilename(file))" in source, name
        assert "const pendingEditorImageUploads = new Set();" in source, name
        assert "await waitForEditorImageUploads();" in source, name
        assert "Image.configure({ allowBase64: false })" in source, name
        assert "readAsDataURL" not in source, name
        assert "Image.configure({ allowBase64: true })" not in source, name


def test_tiptap_mimes_do_cliente_refletem_endpoint_de_upload():
    for name, source in _template_sources().items():
        assert "allowedMimeTypes: ['image/jpeg', 'image/png', 'image/webp']" in source, name
        assert "image/gif" not in source, name
