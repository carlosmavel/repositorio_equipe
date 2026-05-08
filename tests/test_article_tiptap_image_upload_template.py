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
        assert "headers: { Accept: 'application/json' }" in source, name
        assert "const pendingEditorImageUploads = new Set();" in source, name
        assert "await waitForEditorImageUploads();" in source, name
        assert "Image.configure({ allowBase64: false })" in source, name
        assert "readAsDataURL" not in source, name
        assert "Image.configure({ allowBase64: true })" not in source, name


def test_tiptap_mimes_do_cliente_refletem_endpoint_de_upload():
    for name, source in _template_sources().items():
        assert "EDITOR_IMAGE_ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']" in source, name
        assert "allowedMimeTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp']" in source, name
        assert "image/gif" in source, name


def test_tiptap_upload_de_imagem_tem_diagnostico_e_timeout():
    for name, source in _template_sources().items():
        assert "const EDITOR_IMAGE_UPLOAD_TIMEOUT_MS = 30000;" in source, name
        assert "const EDITOR_IMAGE_MAX_BYTES = Number" in source, name
        assert "const controller = new AbortController();" in source, name
        assert "signal: controller.signal" in source, name
        assert "[editor-image-upload:start]" in source, name
        assert "[editor-image-upload:end]" in source, name
        assert "Tempo esgotado ao enviar a imagem colada" in source, name
        assert "Reduza o print ou envie como anexo" in source, name


def test_progresso_de_upload_so_consulta_endpoint_quando_ha_anexos():
    for name, source in _template_sources().items():
        assert "const hasPendingAttachmentFiles = () => Boolean(document.getElementById('files')?.files?.length);" in source, name
        assert "if (hasPendingAttachmentFiles()) {" in source, name
        assert "startProgressPolling(progressId);" in source, name


def test_tiptap_evita_upload_duplicado_e_inicializacao_repetida():
    for name, source in _template_sources().items():
        assert "dataset.tiptapInitialized" in source, name
        assert "const activeEditorImageUploadKeys = new Set();" in source, name
        assert "activeEditorImageUploadKeys.has(uploadKey)" in source, name
        assert ".finally(() => activeEditorImageUploadKeys.delete(uploadKey))" in source, name
        assert "setSubmitButtonsDisabled(true);" in source, name


def test_novo_artigo_preserva_acao_apos_uploads_do_tiptap():
    source = (ROOT / "templates" / "artigos" / "novo_artigo.html").read_text(encoding="utf-8")
    submit_listener = source[source.index("form.addEventListener('submit'"):]

    assert 'id="submit-action"' in source
    assert 'name="acao" id="submit-action"' not in source
    assert "let lastSubmitter = null;" in source
    assert "const submitter = event.submitter || lastSubmitter;" in submit_listener
    assert "submitActionInput.name = 'acao';" in submit_listener
    assert "submitActionInput.value = submitter?.name === 'acao' ? submitter.value : 'rascunho';" in submit_listener
    assert submit_listener.index("submitActionInput.value") < submit_listener.index("setSubmitButtonsDisabled(true);")
    assert "form.requestSubmit(submitter);" not in submit_listener
    assert "form.submit();" in submit_listener


def test_tiptap_toolbar_expande_formatacoes_gratuitas_e_tabelas():
    for name, source in _template_sources().items():
        for import_name in [
            "@tiptap/extension-link@3",
            "@tiptap/extension-subscript@3",
            "@tiptap/extension-superscript@3",
            "@tiptap/extension-text-style@3",
            "@tiptap/extension-underline@3",
        ]:
            assert import_name in source, name

        for command in [
            'data-editor-command="underline"',
            'data-editor-command="code"',
            'data-editor-command="subscript"',
            'data-editor-command="superscript"',
            'data-editor-command="horizontalRule"',
            'data-editor-command="setLink"',
            'data-editor-command="addColumnBefore"',
            'data-editor-command="addColumnAfter"',
            'data-editor-command="deleteColumn"',
            'data-editor-command="addRowBefore"',
            'data-editor-command="addRowAfter"',
            'data-editor-command="deleteRow"',
            'data-editor-command="mergeCells"',
            'data-editor-command="splitCell"',
            'data-editor-command="deleteTable"',
        ]:
            assert command in source, name

        assert "insertConfiguredTable" in source, name
        assert "Quantas colunas a tabela deve ter?" in source, name
        assert "chain.addColumnAfter().run()" in source, name
        assert "chain.deleteColumn().run()" in source, name
