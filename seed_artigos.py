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

        for idx, visibility in enumerate(visibilities):
            user = users[idx % len(users)]
            title = f"Artigo {visibility.value.title()}"
            article = Article.query.filter_by(titulo=title, user_id=user.id).first()
            if article:
                print(f"{title} por {user.username} já existe.")
                continue

            data = {
                "titulo": title,
                "texto": f"Conteúdo visível por {visibility.label}.",
                "user_id": user.id,
                "celula_id": user.celula_id,
                "visibility": visibility,
                "status": ArticleStatus.APROVADO,
            }

            if visibility is ArticleVisibility.INSTITUICAO:
                data["instituicao_id"] = user.estabelecimento.instituicao_id
            elif visibility is ArticleVisibility.ESTABELECIMENTO:
                data["estabelecimento_id"] = user.estabelecimento_id
            elif visibility is ArticleVisibility.SETOR:
                data["setor_id"] = user.setor_id
            elif visibility is ArticleVisibility.CELULA:
                data["vis_celula_id"] = user.celula_id

            article = Article(**data)
            db.session.add(article)
            print(f"{title} criado para {user.username}.")

        db.session.commit()
        print("🚀 Seed de artigos concluído.")


if __name__ == "__main__":
    run()
