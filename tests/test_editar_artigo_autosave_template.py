import re
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "artigos" / "editar_artigo.html"
EDITOR = ROOT / "frontend" / "article-editor" / "index.js"


def test_editar_artigo_serializa_chave_autosave_esperada():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert "'autosaveKey': 'artigo_edicao_autosave_' ~ artigo.id" in source
    assert 'id="article-editor-config"' in source


def test_editar_artigo_nao_remove_autosave_antes_do_fetch():
    source = EDITOR.read_text(encoding="utf-8")
    submit_listener = source[source.index("form.addEventListener('submit'"):]
    before_fetch, after_fetch = submit_listener.split("const response = await fetch", 1)
    assert before_fetch.count("localStorage.removeItem(STORAGE_KEY)") == 1
    assert before_fetch.index("config.mode === 'create'") < before_fetch.index("localStorage.removeItem(STORAGE_KEY)")
    assert "if (submitResult.shouldClearAutosave)" in after_fetch
    assert after_fetch.index("if (submitResult.shouldClearAutosave)") < after_fetch.index("localStorage.removeItem(STORAGE_KEY)")


def test_editar_artigo_resposta_validacao_nao_limpa_autosave():
    source = EDITOR.read_text(encoding="utf-8")
    helpers = re.search(
        r"function isArticleViewUrl[\s\S]+?\n  // Sincroniza conteúdo no hidden antes de submeter",
        source,
    ).group(0).replace("\n  // Sincroniza conteúdo no hidden antes de submeter", "")
    helpers = helpers.replace("expectedPath = ARTICLE_VIEW_PATH", "expectedPath = '/artigo/123'")
    script = textwrap.dedent(f"""
        global.window = {{ location: {{ origin: 'https://example.test' }} }};
        {helpers}
        const response = {{ redirected: false, ok: true,
          headers: {{ get: () => 'text/html; charset=utf-8' }},
          text: async () => '<html>Erro de validação</html>' }};
        resolveEditSubmitResult(response, '/artigo/123').then((result) => {{
          if (result.shouldClearAutosave) process.exit(1);
          if (!result.html.includes('Erro de validação')) process.exit(2);
        }}).catch(() => process.exit(3));
    """)
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
