import re
import subprocess
import textwrap
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "artigos" / "editar_artigo.html"


def _template_source():
    return TEMPLATE.read_text(encoding="utf-8")


def test_editar_artigo_usa_chave_autosave_esperada():
    source = _template_source()

    assert "const STORAGE_KEY = 'artigo_edicao_autosave_{{ artigo.id }}';" in source
    assert "draft_editar_artigo_{{ artigo.id }}" not in source


def test_editar_artigo_nao_remove_autosave_antes_do_fetch():
    source = _template_source()
    submit_listener = source[source.index("form.addEventListener('submit'"):]
    before_fetch, after_fetch = submit_listener.split("const response = await fetch", 1)

    assert "localStorage.removeItem(STORAGE_KEY)" not in before_fetch
    assert "if (submitResult.shouldClearAutosave)" in after_fetch
    assert after_fetch.index("if (submitResult.shouldClearAutosave)") < after_fetch.index(
        "localStorage.removeItem(STORAGE_KEY)"
    )


def test_editar_artigo_resposta_validacao_nao_limpa_autosave():
    source = _template_source()
    helpers = re.search(
        r"function isArticleViewUrl[\s\S]+?\n  // Sincroniza conteúdo no hidden antes de submeter",
        source,
    ).group(0).replace("\n  // Sincroniza conteúdo no hidden antes de submeter", "")
    helpers = helpers.replace("expectedPath = ARTICLE_VIEW_PATH", "expectedPath = '/artigo/123'")
    node_script = textwrap.dedent(
        f"""
        global.window = {{ location: {{ origin: 'https://example.test' }} }};
        {helpers}

        const storage = {{ artigo_edicao_autosave_123: 'rascunho preservado' }};
        const validationResponse = {{
          redirected: false,
          ok: true,
          headers: {{ get: () => 'text/html; charset=utf-8' }},
          text: async () => '<html><body>Erro de validação: título e conteúdo textual são obrigatórios.</body></html>'
        }};

        resolveEditSubmitResult(validationResponse, '/artigo/123').then((result) => {{
          if (result.shouldClearAutosave) {{
            delete storage.artigo_edicao_autosave_123;
          }}
          if (result.shouldClearAutosave !== false) {{
            throw new Error('resposta de validação foi tratada como sucesso');
          }}
          if (storage.artigo_edicao_autosave_123 !== 'rascunho preservado') {{
            throw new Error('draft apagado em erro de validação');
          }}
          if (!result.html.includes('Erro de validação')) {{
            throw new Error('HTML de validação não foi preservado para renderização');
          }}
        }}).catch((error) => {{
          console.error(error);
          process.exit(1);
        }});
        """
    )

    completed = subprocess.run(
        ["node", "-e", node_script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
