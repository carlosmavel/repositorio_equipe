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
    INSTITUICAO     = "instituicao"
    ESTABELECIMENTO = "estabelecimento"
    SETOR           = "setor"
    CELULA          = "celula"
