from core.enums import Permissao
from core.permission_catalog import CATALOG_BY_CODE, PERMISSION_CATEGORY_BY_CODE


def test_permission_catalog_includes_artigo_restaurar_versao_in_article_category():
    codigo = Permissao.ARTIGO_RESTAURAR_VERSAO.value

    assert codigo == "artigo_restaurar_versao"
    assert CATALOG_BY_CODE[codigo].nome == "Restaurar versão de artigo"
    assert PERMISSION_CATEGORY_BY_CODE[codigo] == "Permissões de Artigos"
