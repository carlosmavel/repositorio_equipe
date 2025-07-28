try:
    from .database import db
except ImportError:
    from database import db

try:
    from .models import User, Article
except ImportError:
    from models import User, Article

try:
    from .enums import ArticleVisibility, ArticleStatus
except ImportError:
    from enums import ArticleVisibility, ArticleStatus

from app import app
from datetime import datetime, timezone


def run():
    """Popula a base com artigos de exemplo para cada tipo de visibilidade."""
    with app.app_context():
        print("Verificando e criando artigos de exemplo...")
        users = User.query.all()
        if not users:
            print("Nenhum usuário encontrado. Execute os seeds de usuários antes.")
            return

        visibilities = [
            ArticleVisibility.INSTITUICAO,
            ArticleVisibility.ESTABELECIMENTO,
            ArticleVisibility.SETOR,
            ArticleVisibility.CELULA,
        ]

        for user in users:
            if not user.celula_id:
                print(f"Usuário {user.username} sem célula associada. Pulando.")
                continue

            for visibility in visibilities:
                title = f"Artigo {visibility.value.title()} - {user.username}"
                article = Article.query.filter_by(titulo=title, user_id=user.id).first()
                if article:
                    print(f"{title} já existe.")
                    continue

                data = {
                    "titulo": title,
                    "texto": f"Conteúdo visível por {visibility.label}.",
                    "user_id": user.id,
                    "celula_id": user.celula_id,
                    "visibility": visibility,
                    "status": ArticleStatus.APROVADO,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }

                if visibility is ArticleVisibility.INSTITUICAO:
                    inst_id = getattr(getattr(user, "estabelecimento", None), "instituicao_id", None)
                    if not inst_id:
                        print(f"Usuário {user.username} sem instituição. Pulando artigo de instituição.")
                        continue
                    data["instituicao_id"] = inst_id
                elif visibility is ArticleVisibility.ESTABELECIMENTO:
                    if not user.estabelecimento_id:
                        print(f"Usuário {user.username} sem estabelecimento. Pulando artigo de estabelecimento.")
                        continue
                    data["estabelecimento_id"] = user.estabelecimento_id
                elif visibility is ArticleVisibility.SETOR:
                    if not user.setor_id:
                        print(f"Usuário {user.username} sem setor. Pulando artigo de setor.")
                        continue
                    data["setor_id"] = user.setor_id
                elif visibility is ArticleVisibility.CELULA:
                    data["vis_celula_id"] = user.celula_id

                article = Article(**data)
                db.session.add(article)
                print(f"{title} criado.")

        db.session.commit()
        print("🚀 Seed de artigos concluído.")


if __name__ == "__main__":
    run()
