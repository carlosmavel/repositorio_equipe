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
        user = User(
            username='u1',
            email='u1@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor,
            celula=cel,
        )
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


def test_user_can_view_by_celula(client):
    from utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        est = user1.celula.estabelecimento
        setor = user1.celula.setor
        cel2 = Celula(nome='Celula 2', estabelecimento=est, setor=setor)
        db.session.add(cel2)
        user2 = User(
            username='u2',
            email='u2@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T2',
            texto='C2',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.CELULA,
            vis_celula_id=user1.celula_id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user1, art) is True
        assert user_can_view_article(user2, art) is False


def test_user_can_view_by_estabelecimento(client):
    from utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        est = user1.celula.estabelecimento
        setor = user1.celula.setor
        cel2 = Celula(nome='Celula 3', estabelecimento=est, setor=setor)
        db.session.add(cel2)
        user2 = User(
            username='u3',
            email='u3@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T3',
            texto='C3',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.ESTABELECIMENTO,
            estabelecimento_id=est.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is True



def test_user_can_view_by_setor(client):
    from utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        est = user1.celula.estabelecimento
        setor = user1.celula.setor
        cel2 = Celula(nome='Celula 4', estabelecimento=est, setor=setor)
        db.session.add(cel2)
        user2 = User(
            username='u4',
            email='u4@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T4',
            texto='C4',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.SETOR,
            setor_id=setor.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is True


def test_user_can_view_by_instituicao(client):
    from utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        inst = user1.celula.estabelecimento.instituicao
        est2 = Estabelecimento(codigo='E2', nome_fantasia='Est 2', instituicao=inst)
        db.session.add(est2)
        setor2 = Setor(nome='Setor X', estabelecimento=est2)
        db.session.add(setor2)
        cel2 = Celula(nome='Celula 5', estabelecimento=est2, setor=setor2)
        db.session.add(cel2)
        user2 = User(
            username='u5',
            email='u5@test',
            password_hash='x',
            estabelecimento=est2,
            setor=setor2,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T5',
            texto='C5',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.INSTITUICAO,
            instituicao_id=inst.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is True

