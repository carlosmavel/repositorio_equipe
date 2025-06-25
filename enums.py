# enums.py
from enum import Enum

class ArticleStatus(Enum):
    RASCUNHO   = ('rascunho',    'Rascunho',   'primary', 'white')
    PENDENTE   = ('pendente',    'Pendente',   'warning',   'dark')
    EM_REVISAO = ('em_revisao',   'Em Revisão', 'primary',  'white')
    EM_AJUSTE  = ('em_ajuste',   'Em Ajuste',  'primary',   'white')
    APROVADO   = ('aprovado',    'Aprovado',   'success',   'white')
    REJEITADO  = ('rejeitado',   'Rejeitado',  'danger',    'white')

    def __init__(self, value, label, color, text_color):
        self._value_     = value
        self.label       = label
        self.color       = color
        self.text_color  = text_color


class ArticleVisibility(Enum):
    """Controla quem pode visualizar o artigo."""

    def __new__(cls, value: str, label: str):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.label = label
        return obj

    INSTITUICAO     = ("instituicao",     "Instituição")
    ESTABELECIMENTO = ("estabelecimento", "Estabelecimento")
    SETOR           = ("setor",           "Setor")
    CELULA          = ("celula",          "Célula")


class Permissao(Enum):
    """Códigos de permissões relacionados a ações em artigos."""

    # --- edição de artigos ---
    ARTIGO_EDITAR_CELULA = "artigo_editar_celula"
    ARTIGO_EDITAR_SETOR = "artigo_editar_setor"
    ARTIGO_EDITAR_ESTABELECIMENTO = "artigo_editar_estabelecimento"
    ARTIGO_EDITAR_INSTITUICAO = "artigo_editar_instituicao"
    ARTIGO_EDITAR_TODAS = "artigo_editar_todas"

    # --- aprovação de artigos ---
    ARTIGO_APROVAR_CELULA = "artigo_aprovar_celula"
    ARTIGO_APROVAR_SETOR = "artigo_aprovar_setor"
    ARTIGO_APROVAR_ESTABELECIMENTO = "artigo_aprovar_estabelecimento"
    ARTIGO_APROVAR_INSTITUICAO = "artigo_aprovar_instituicao"
    ARTIGO_APROVAR_TODAS = "artigo_aprovar_todas"

    # --- revisão de artigos ---
    ARTIGO_REVISAR_CELULA = "artigo_revisar_celula"
    ARTIGO_REVISAR_SETOR = "artigo_revisar_setor"
    ARTIGO_REVISAR_ESTABELECIMENTO = "artigo_revisar_estabelecimento"
    ARTIGO_REVISAR_INSTITUICAO = "artigo_revisar_instituicao"
    ARTIGO_REVISAR_TODAS = "artigo_revisar_todas"

    # --- assumir revisão ---
    ARTIGO_ASSUMIR_REVISAO_CELULA = "artigo_assumir_revisao_celula"
    ARTIGO_ASSUMIR_REVISAO_SETOR = "artigo_assumir_revisao_setor"
    ARTIGO_ASSUMIR_REVISAO_ESTABELECIMENTO = "artigo_assumir_revisao_estabelecimento"
    ARTIGO_ASSUMIR_REVISAO_INSTITUICAO = "artigo_assumir_revisao_instituicao"
    ARTIGO_ASSUMIR_REVISAO_TODAS = "artigo_assumir_revisao_todas"
