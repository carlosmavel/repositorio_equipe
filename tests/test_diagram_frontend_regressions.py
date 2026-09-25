from pathlib import Path

from blueprints import diagrams as diagrams_blueprint


ROOT = Path(__file__).resolve().parents[1]


def test_article_diagram_node_view_distinguishes_editing_from_viewing():
    source = (ROOT / 'frontend/article-editor/extensions/article-diagram.js').read_text()

    assert "metadata.can_edit ? metadata.editor_url : metadata.view_url" in source
    assert "metadata.can_edit ? 'Editar diagrama' : 'Visualizar diagrama'" in source
    assert "stopEvent:" in source
    assert 'scene' not in source.lower()


def test_tiptap_starter_kit_does_not_duplicate_link_and_underline():
    source = (ROOT / 'frontend/article-editor/index.js').read_text()

    assert 'StarterKit.configure({ link: false, underline: false })' in source
    assert "Link.configure({ openOnClick: false, defaultProtocol: 'https' })" in source
    assert 'Underline,' in source


def test_vite_assets_use_flask_static_dist_base():
    source = (ROOT / 'vite.config.js').read_text()

    assert "base: '/static/dist/'" in source


def test_transient_missing_preview_is_not_cached(app_ctx, monkeypatch):
    monkeypatch.setattr(diagrams_blueprint, 'get_preview', lambda *_args, **_kwargs: (None, None))

    with app_ctx.test_request_context('/api/diagramas/example/preview'):
        response = diagrams_blueprint._preview_response(object(), object())

    assert response.content_type == 'image/svg+xml; charset=utf-8'
    assert response.cache_control.no_store is True
    assert response.cache_control.max_age is None


def test_current_preview_is_revalidated_after_save(app_ctx, monkeypatch):
    monkeypatch.setattr(diagrams_blueprint, 'get_preview', lambda *_args, **_kwargs: (b'png', 'image/png'))

    with app_ctx.test_request_context('/api/diagramas/example/preview'):
        response = diagrams_blueprint._preview_response(object(), object())

    assert response.cache_control.private is True
    assert response.cache_control.no_cache is True
    assert response.cache_control.max_age is None


def test_versioned_preview_can_be_cached(app_ctx, monkeypatch):
    monkeypatch.setattr(diagrams_blueprint, 'get_preview', lambda *_args, **_kwargs: (b'png', 'image/png'))

    with app_ctx.test_request_context('/diagramas/example/versoes/1/preview'):
        response = diagrams_blueprint._preview_response(object(), object(), version=object())

    assert response.cache_control.private is True
    assert response.cache_control.max_age == 300


def test_diagram_editor_tracks_confirmed_save_without_onchange_race():
    source = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()

    assert "setStatus('Salvando...')" in source
    assert "savedFingerprintRef.current = savedFingerprint" in source
    assert "latestFingerprintRef.current === savedFingerprint" in source
    assert "disabled={isSaving}" in source
    assert "savingRef.current" in source
    assert "import diagramTransport from './transport.js'" in source
    assert 'transport = diagramTransport' in source


def test_diagram_workspace_is_reusable_and_has_explicit_modes_and_callbacks():
    source = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()

    assert 'export function DiagramWorkspace({' in source
    assert "mode = 'edit'" in source
    assert "const editable = mode === 'edit' && canEdit" in source
    assert 'onChange={editable ? onChange : undefined}' in source
    assert 'viewModeEnabled={!editable}' in source
    assert 'callbacksRef.current.onSaved?.(saved)' in source
    assert 'callbacksRef.current.onDirtyChange?.(dirty)' in source
    assert 'callbacksRef.current.onStatusChange?.(value)' in source
    assert 'callbacksRef.current.onReady?.(api)' in source
    assert 'onClick={onRequestClose}' in source


def test_diagram_workspace_reports_load_conflicts_and_preview_identity():
    source = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()

    assert 'Falha ao carregar:' in source
    assert "result.error || 'Não foi possível salvar o diagrama.'" in source
    assert 'uuid: result.uuid || result.id' in source
    assert 'current_version: result.current_version' in source
    assert 'lock_version: result.lock_version' in source
    assert 'preview_url: result.preview_url || versionedPreviewUrl' in source


def test_standalone_bootstrap_is_separate_from_workspace_bundle():
    component = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()
    bootstrap = (ROOT / 'frontend/diagram-editor/standalone.jsx').read_text()
    template = (ROOT / 'templates/diagrams/editor.html').read_text()
    vite = (ROOT / 'vite.config.js').read_text()

    assert "getElementById('diagram-editor')" not in component
    assert "getElementById('diagram-editor')" in bootstrap
    assert '<DiagramWorkspace {...config} />' in bootstrap
    assert "'mode': 'edit' if can_edit_diagram else 'view'" in template
    assert "'previewUrl': url_for('diagrams_bp.api_diagram_preview'" in template
    assert "'diagram-editor': 'frontend/diagram-editor/standalone.jsx'" in vite


def test_article_diagram_opens_accessible_in_page_overlay():
    overlay = (ROOT / 'frontend/diagram-ui/overlay.jsx').read_text()
    extension = (ROOT / 'frontend/article-editor/extensions/article-diagram.js').read_text()
    css = (ROOT / 'static/css/diagram-preview.css').read_text()

    assert 'role="dialog" aria-modal="true"' in overlay
    assert "document.addEventListener('keydown', onKeyDown, true)" in overlay
    assert "window.scrollTo(scrollX, scrollY)" in overlay
    assert 'root.unmount()' in overlay
    assert 'Descartar alterações?' in overlay
    assert 'onOpenDiagram(metadata, action)' in extension
    assert "action.target = '_blank'" not in extension
    assert 'z-index: 2147483647' in css


def test_progressive_viewer_supports_zoom_pan_fit_and_raster_fallback():
    overlay = (ROOT / 'frontend/diagram-ui/overlay.jsx').read_text()
    bootstrap = (ROOT / 'frontend/article-diagram-viewer/index.js').read_text()

    assert 'viewModeEnabled={!editable}' in (ROOT / 'frontend/diagram-editor/index.jsx').read_text()
    assert 'metadata.can_open_scene' in overlay
    assert 'RasterDiagramViewer' in overlay
    assert 'onWheel=' in overlay
    assert 'onPointerMove=' in overlay
    assert "event.key === '+'" in overlay
    assert 'Ajustar à tela' in overlay
    assert 'naturalWidth' in overlay and 'naturalHeight' in overlay
    assert 'SceneErrorBoundary' in overlay
    assert 'can_open_scene: false' in bootstrap


def test_readonly_article_phases_load_contextual_viewer_bundle():
    for template_name in ('aprovacao_detail.html', 'artigo.html', 'visualizar_versao.html'):
        template = (ROOT / 'templates/artigos' / template_name).read_text()
        assert "vite_asset('frontend/article-diagram-viewer/index.js')" in template
        assert "filename='css/diagram-preview.css'" in template

    rendering = (ROOT / 'core/services/diagrams/rendering.py').read_text()
    assert 'data-diagram-metadata-url' in rendering
    assert 'Visualizar diagrama' in rendering
