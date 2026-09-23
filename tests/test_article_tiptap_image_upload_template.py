from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = [
    ROOT / "templates" / "artigos" / "novo_artigo.html",
    ROOT / "templates" / "artigos" / "editar_artigo.html",
]
EDITOR_SOURCE = ROOT / "frontend" / "article-editor" / "index.js"
BUNDLE = ROOT / "static" / "js" / "article-editor.js"


def _editor_source():
    return EDITOR_SOURCE.read_text(encoding="utf-8")


def test_criacao_e_edicao_carregam_o_mesmo_bundle_e_registro_de_nodes():
    for template in TEMPLATES:
        source = template.read_text(encoding="utf-8")
        assert 'id="article-editor-config"' in source, template.name
        assert "filename='js/article-editor.js'" in source, template.name
        assert "new Editor(" not in source, template.name
        assert "Node.create(" not in source, template.name

    source = _editor_source()
    for node in [
        "StarterKit", "Image.configure", "VideoNode", "Link.configure",
        "Subscript", "Superscript", "TextStyle", "Color", "Underline",
        "Table.configure", "TableRow", "TableCell", "TableHeader",
        "TaskList", "TaskItem.configure", "Placeholder.configure",
        "TextAlign.configure", "Highlight.configure", "FileHandler.configure",
    ]:
        assert node in source


def test_bundle_compilado_corresponde_ao_modulo_fonte():
    assert BUNDLE.read_text(encoding="utf-8") == _editor_source()


def test_tiptap_cola_imagens_via_upload_em_vez_de_base64():
    source = _editor_source()
    assert "fetch('/artigos/editor-image-upload'" in source
    assert "formData.append('file', file, editorImageFilename(file))" in source
    assert "headers: { Accept: 'application/json' }" in source
    assert "const pendingEditorImageUploads = new Set();" in source
    assert "await waitForEditorImageUploads();" in source
    assert "Image.configure({ allowBase64: false })" in source
    assert "readAsDataURL" not in source


def test_tiptap_upload_tem_validacao_diagnostico_e_timeout():
    source = _editor_source()
    assert "EDITOR_IMAGE_ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']" in source
    assert "const EDITOR_IMAGE_UPLOAD_TIMEOUT_MS = 30000;" in source
    assert "const controller = new AbortController();" in source
    assert "signal: controller.signal" in source
    assert "[editor-image-upload:start]" in source
    assert "[editor-image-upload:end]" in source
    assert "Tempo esgotado ao enviar a imagem colada" in source


def test_uploads_toolbar_tabelas_e_sincronizacao_ficam_no_modulo():
    source = _editor_source()
    assert "const hasPendingAttachmentFiles" in source
    assert "activeEditorImageUploadKeys.has(uploadKey)" in source
    assert "insertConfiguredTable" in source
    assert "chain.addColumnAfter().run()" in source
    assert "chain.deleteColumn().run()" in source
    assert "hiddenTexto.value = editor.getHTML()" in source
    assert "config.mode === 'create'" in source
    assert "config.mode === 'edit'" in source
