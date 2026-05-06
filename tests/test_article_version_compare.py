import pytest

from core.models import ArticleVersion
from core.services.article_versions import compare_article_versions


def test_compare_article_versions_text_and_metadata_only():
    from_version = ArticleVersion(
        article_id=10,
        version_number=1,
        revision_number=0,
        titulo="Título antigo",
        texto="Olá mundo antigo",
        status="rascunho",
        visibility="celula",
        change_action="create_initial",
    )
    to_version = ArticleVersion(
        article_id=10,
        version_number=1,
        revision_number=1,
        titulo="Título novo",
        texto="Olá mundo novo mundo",
        status="aprovado",
        visibility="setor",
        change_action="approve",
    )

    comparison = compare_article_versions(from_version, to_version)

    assert comparison["text_char_delta"] == len(to_version.texto) - len(from_version.texto)
    assert comparison["title_char_delta"] == len(to_version.titulo) - len(from_version.titulo)
    assert comparison["words_added_count"] == 2
    assert comparison["words_removed_count"] == 1
    assert {item["word"]: item for item in comparison["word_deltas"]} == {
        "antigo": {"word": "antigo", "removed": 1, "added": 0},
        "mundo": {"word": "mundo", "removed": 0, "added": 1},
        "novo": {"word": "novo", "removed": 0, "added": 1},
    }
    assert {
        change["field"] for change in comparison["metadata_changes"]
    } >= {"status", "visibility"}


def test_compare_article_versions_rejects_different_articles():
    from_version = ArticleVersion(
        article_id=1,
        titulo="A",
        texto="um",
        status="rascunho",
        visibility="celula",
        change_action="create_initial",
    )
    to_version = ArticleVersion(
        article_id=2,
        titulo="A",
        texto="dois",
        status="rascunho",
        visibility="celula",
        change_action="create_initial",
    )

    with pytest.raises(ValueError, match="mesmo artigo"):
        compare_article_versions(from_version, to_version)
