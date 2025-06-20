try:
    from .database import db  # pragma: no cover
except ImportError:
    from database import db
from models import Funcao
from app import app

FUNCOES = [
    ("admin", "Administrador"),
    ("colaborador", "Colaborador"),
    ("editor", "Editor"),
    ("artigo_criar", "Criar artigo"),
    ("artigo_editar", "Editar artigo"),
    ("artigo_aprovar", "Aprovar artigo"),
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
