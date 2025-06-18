import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import app, db
from models import Instituicao, Estabelecimento, Setor, Celula, User, Article, ArticleVisibility

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        inst = Instituicao(nome='Inst 1')
        est = Estabelecimento(codigo='EST1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='Setor 1', estabelecimento=est)
        cel = Celula(nome='Celula 1', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.commit()
        user = User(username='u1', email='u1@test', password_hash='x', celula=cel)
        db.session.add(user)
        db.session.commit()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()


def test_article_visibility_fields(client):
    with app.app_context():
        user = User.query.first()
        cel = Celula.query.first()
        art = Article(
            titulo='T',
            texto='C',
            user_id=user.id,
            celula_id=cel.id,
            visibility=ArticleVisibility.CELULA,
        )
        db.session.add(art)
        db.session.commit()
        fetched = Article.query.first()
        assert fetched.visibility is ArticleVisibility.CELULA
        assert fetched.celula_id == cel.id

