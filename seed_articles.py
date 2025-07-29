try:
    from .database import db
except ImportError:
    from database import db

from app import app

try:
    from .models import User, Article
except ImportError:
    from models import User, Article

try:
    from .enums import ArticleVisibility
except ImportError:
    from enums import ArticleVisibility


def run():
    """Create a sample article for each user."""
    with app.app_context():
        print("Criando artigos de exemplo...")
        users = User.query.all()
        for user in users:
            title = f"Artigo de {user.username}"
            exists = Article.query.filter_by(titulo=title, user_id=user.id).first()
            if not exists:
                art = Article(
                    titulo=title,
                    texto="Conteúdo de exemplo.",
                    user_id=user.id,
                    celula_id=user.celula_id,
                    setor_id=user.setor_id,
                    estabelecimento_id=user.estabelecimento_id,
                    instituicao_id=user.estabelecimento.instituicao_id if user.estabelecimento else None,
                    visibility=ArticleVisibility.CELULA,
                )
                db.session.add(art)
        db.session.commit()
        print("Artigos criados.")


if __name__ == "__main__":
    run()
