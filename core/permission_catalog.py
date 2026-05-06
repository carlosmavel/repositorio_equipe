"""Catálogo centralizado de permissões da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict

try:
    from .enums import Permissao
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.enums import Permissao


@dataclass(frozen=True)
class PermissionCatalogItem:
    """Entrada do catálogo de permissões."""

    codigo: str
    nome: str


FRIENDLY_NAMES: dict[str, str] = {
    Permissao.ARTIGO_RESTAURAR_VERSAO.value: "Restaurar versão de artigo",
    Permissao.BOLETIM_VISUALIZAR.value: "Boletim visualizar",
    Permissao.BOLETIM_BUSCAR.value: "Boletim buscar",
    Permissao.BOLETIM_GERENCIAR.value: "Boletim gerenciar",
}


CATALOG: tuple[PermissionCatalogItem, ...] = (
    *(
        PermissionCatalogItem(
            codigo=permission.value,
            nome=FRIENDLY_NAMES.get(permission.value, permission.value.replace("_", " ").capitalize()),
        )
        for permission in Permissao
    ),
    PermissionCatalogItem(codigo="admin", nome="Administrador"),
    PermissionCatalogItem(codigo="artigo_criar", nome="Criar artigo"),
    PermissionCatalogItem(codigo="artigo_revisar", nome="Revisar artigo"),
    PermissionCatalogItem(codigo="artigo_assumir_revisao", nome="Assumir revisão"),
)

CATALOG_BY_CODE: dict[str, PermissionCatalogItem] = {item.codigo: item for item in CATALOG}

# Migrações lógicas de código (de -> para) permitidas no sincronizador.
CODE_ALIASES: dict[str, str] = {}

# Códigos descontinuados do catálogo nativo que podem permanecer no banco
# sem atualização automática até remoção por migração explícita.
DEPRECATED_CODES: set[str] = set()


PERMISSION_CATEGORIES_ORDER: tuple[str, ...] = (
    "Permissões de Artigos",
    "Permissões de Boletins",
    "Permissões Administrativas",
    "Outras Permissões",
)

PERMISSION_CATEGORY_BY_CODE: dict[str, str] = {
    item.codigo: (
        "Permissões de Artigos" if item.codigo.startswith("artigo_")
        else "Permissões de Boletins" if item.codigo.startswith("boletim_")
        else "Permissões Administrativas" if item.codigo.startswith("admin")
        else "Outras Permissões"
    )
    for item in CATALOG
}


def agrupar_funcoes_por_categoria(funcoes):
    categorias = OrderedDict((categoria, []) for categoria in PERMISSION_CATEGORIES_ORDER)
    for funcao in funcoes:
        categoria = PERMISSION_CATEGORY_BY_CODE.get(funcao.codigo, "Outras Permissões")
        categorias[categoria].append(funcao)
    return categorias
