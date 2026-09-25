from pathlib import Path

from blueprints import diagrams as diagrams_blueprint


ROOT = Path(__file__).resolve().parents[1]


def test_article_diagram_node_view_distinguishes_editing_from_viewing():
    source = (ROOT / 'frontend/article-editor/extensions/article-diagram.js').read_text()

    assert "makeAction('Visualizar diagrama', 'btn-outline-primary', 'view')" in source
    assert "if (metadata.can_edit)" in source
    assert "makeAction('Editar', 'btn-primary', 'edit')" in source
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

    assert "setSaveState('saving')" in source
    assert "savedFingerprintRef.current = savedFingerprint" in source
    assert "latestFingerprintRef.current === savedFingerprint" in source
    assert "setSaveState(dirty ? 'dirty' : 'saved')" in source
    assert 'disabled={savePresentation.disabled}' in source
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
    assert 'callbacksRef.current.onSaveStateChange?.(value)' in source
    assert 'callbacksRef.current.onReady?.(api)' in source
    assert 'onClick={onRequestClose}' in source


def test_diagram_workspace_follows_global_theme_without_new_storage_key():
    source = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()

    assert "document.documentElement.dataset.bsTheme === 'dark'" in source
    assert "window.addEventListener('themeChange', syncTheme)" in source
    assert "window.removeEventListener('themeChange', syncTheme)" in source
    assert 'theme={theme}' in source
    assert 'localStorage' not in source


def test_diagram_save_state_is_explicit_accessible_and_retryable():
    source = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()
    css = (ROOT / 'static/css/diagram-preview.css').read_text()

    for state in ('clean', 'dirty', 'saving', 'saved', 'error'):
        assert f'{state}:' in source
        assert f'data-save-state="{state}"' in css
    for label in ('Salvar alterações', 'Salvando...', 'Salvo',
                  'Falha ao salvar — tentar novamente'):
        assert label in source
    assert 'aria-live="polite"' in source
    assert 'aria-atomic="true"' in source
    assert "saveState === 'clean' || saveState === 'saved'" in source
    assert "setSaveState('error')" in source


def test_diagram_workspace_reports_load_conflicts_and_preview_identity():
    source = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()

    assert 'Falha ao carregar:' in source
    assert "result.error || 'Não foi possível salvar o diagrama.'" in source
    assert 'uuid: result.uuid || result.id' in source
    assert 'current_version: result.current_version' in source
    assert 'lock_version: result.lock_version' in source
    assert 'preview_url: result.preview_url || versionDiagramPreviewUrl' in source


def test_successful_save_announces_versioned_domain_event():
    workspace = (ROOT / 'frontend/diagram-editor/index.jsx').read_text()
    overlay = (ROOT / 'frontend/diagram-ui/overlay.jsx').read_text()
    events = (ROOT / 'frontend/diagram-ui/events.js').read_text()

    assert "DIAGRAM_SAVED_EVENT = 'orquetask:diagram-saved'" in events
    assert 'window.dispatchEvent(new CustomEvent(DIAGRAM_SAVED_EVENT' in events
    assert 'uuid,' in events
    for field in ('current_version', 'lock_version', 'preview_state',
                  'preview_url', 'preview_token', 'title'):
        assert f'{field}:' in events
    assert 'announceDiagramSaved(saved)' in overlay
    assert 'onSaved={handleSaved}' in overlay
    assert 'callbacksRef.current.onSaved?.(saved)' in workspace


def test_node_views_filter_saved_events_and_only_refresh_their_image():
    source = (ROOT / 'frontend/article-editor/extensions/article-diagram.js').read_text()

    assert 'if (saved.uuid !== node.attrs.diagramId) return' in source
    assert 'previewImage.src = versionDiagramPreviewUrl(' in source
    assert "window.addEventListener(DIAGRAM_SAVED_EVENT, onDiagramSaved)" in source
    # Every occurrence creates and registers its own NodeView closure. Thus two
    # occurrences of one UUID both update, while a second UUID is filtered out.
    assert 'const onDiagramSaved = event =>' in source
    assert 'window.location.reload' not in source


def test_node_view_preserves_contextual_url_and_cleans_up_listener():
    source = (ROOT / 'frontend/article-editor/extensions/article-diagram.js').read_text()
    events = (ROOT / 'frontend/diagram-ui/events.js').read_text()

    assert 'metadata?.preview_url || previewImage.src' in source
    assert "parsed.searchParams.set('v', String(version))" in events
    assert 'Date.now' not in events and 'Math.random' not in events
    assert "saved.preview_state !== 'ready' || !previewImage" in source
    assert 'destroy: () => window.removeEventListener(DIAGRAM_SAVED_EVENT, onDiagramSaved)' in source
    assert 'if (saved.title) updateTitle(saved.title)' in source


def test_save_response_includes_complete_preview_contract():
    source = (ROOT / 'blueprints/diagrams.py').read_text()

    assert "'preview_state': metadata['preview_state']" in source
    assert "'preview_url': metadata['preview_url']" in source
    assert "'preview_token': metadata['cache_token']" in source


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
    assert 'onOpenDiagram?.(node.attrs.diagramId, trigger, { mode })' in extension
    assert "action.target = '_blank'" not in extension
    assert 'editor.commands.setNodeSelection(position)' in extension
    assert "cache: 'no-store'" in overlay
    assert 'onSavingChange={setSaving}' in overlay
    assert 'Salvamento em andamento' in overlay
    assert "window.addEventListener('beforeunload', warnBeforeUnload)" in overlay
    assert 'z-index: 2147483647' in css


def test_progressive_viewer_supports_zoom_pan_fit_and_raster_fallback():
    overlay = (ROOT / 'frontend/diagram-ui/overlay.jsx').read_text()
    bootstrap = (ROOT / 'frontend/article-diagram-viewer/index.js').read_text()

    assert 'viewModeEnabled={!editable}' in (ROOT / 'frontend/diagram-editor/index.jsx').read_text()
    assert 'payload.can_open_scene' in overlay
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
