try:
    from .database import db  # pragma: no cover
except ImportError:
    from database import db
try:
    from .models import Funcao
except ImportError:  # pragma: no cover - fallback for direct execution
    from models import Funcao
from app import app
try:
    from .enums import Permissao  # pragma: no cover
except ImportError:  # pragma: no cover - fallback for direct execution
    from enums import Permissao

# Permissões que não fazem parte do Enum Permissao
EXTRA_FUNCOES = [
    ("admin", "Administrador"),
    ("artigo_criar", "Criar artigo"),
    ("artigo_revisar", "Revisar artigo"),
    ("artigo_assumir_revisao", "Assumir revisão"),
]

def run():
    funcoes = [(p.value, p.value.replace("_", " ").capitalize()) for p in Permissao]
    funcoes.extend(EXTRA_FUNCOES)
    with app.app_context():
        for codigo, nome in funcoes:
            if not Funcao.query.filter_by(codigo=codigo).first():
                db.session.add(Funcao(codigo=codigo, nome=nome))
        db.session.commit()
        print("Funções criadas/atualizadas.")

if __name__ == "__main__":
    run()
