from pathlib import Path

from blueprints import diagrams as diagrams_blueprint


ROOT = Path(__file__).resolve().parents[1]


def test_article_diagram_node_view_opens_authorized_editor_without_embedding_scene():
    source = (ROOT / 'frontend/article-editor/extensions/article-diagram.js').read_text()

    assert "action.href = metadata.editor_url" in source
    assert "metadata.can_edit ? 'Editar diagrama' : 'Abrir diagrama'" in source
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
