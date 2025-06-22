try:
    from .database import db  # pragma: no cover
except ImportError:
    from database import db
try:
    from .models import Funcao
except ImportError:  # pragma: no cover - fallback for direct execution
    from models import Funcao
from app import app

FUNCOES = [
    ("admin", "Administrador"),
    ("colaborador", "Colaborador"),
    ("artigo_criar", "Criar artigo"),
    ("artigo_editar", "Editar artigo"),
    ("artigo_editar_celula", "Editar artigo na célula"),
    ("artigo_editar_setor", "Editar artigo no setor"),
    ("artigo_editar_estabelecimento", "Editar artigo no estabelecimento"),
    ("artigo_editar_instituicao", "Editar artigo na instituição"),
    ("artigo_editar_todas", "Editar todos os artigos"),
    ("artigo_aprovar", "Aprovar artigo"),
    ("artigo_aprovar_celula", "Aprovar artigo na célula"),
    ("artigo_aprovar_setor", "Aprovar artigo no setor"),
    ("artigo_aprovar_estabelecimento", "Aprovar artigo no estabelecimento"),
    ("artigo_aprovar_instituicao", "Aprovar artigo na instituição"),
    ("artigo_aprovar_todas", "Aprovar todos os artigos"),
    ("artigo_revisar", "Revisar artigo"),
    ("artigo_assumir_revisao", "Assumir revisão"),
]

def run():
    with app.app_context():
        for codigo, nome in FUNCOES:
            if not Funcao.query.filter_by(codigo=codigo).first():
                db.session.add(Funcao(codigo=codigo, nome=nome))
        db.session.commit()
        print("Funções criadas/atualizadas.")

if __name__ == "__main__":
    run()
