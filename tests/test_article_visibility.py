import pytest


from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, User, Article, ArticleVisibility

@pytest.fixture
def client(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(codigo='INST001', nome='Inst 1')
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
        with app_ctx.test_client() as client:
            yield client
        
        


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
    from core.utils import user_can_view_article
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
    from core.utils import user_can_view_article
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
    from core.utils import user_can_view_article
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
    from core.utils import user_can_view_article
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


def test_user_cannot_view_wrong_estabelecimento(client):
    from core.utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        est1 = user1.celula.estabelecimento
        inst = est1.instituicao
        est2 = Estabelecimento(codigo='E3', nome_fantasia='Est 3', instituicao=inst)
        db.session.add(est2)
        setor2 = Setor(nome='Setor Y', estabelecimento=est2)
        db.session.add(setor2)
        cel2 = Celula(nome='Celula X', estabelecimento=est2, setor=setor2)
        db.session.add(cel2)
        user2 = User(
            username='u6',
            email='u6@test',
            password_hash='x',
            estabelecimento=est2,
            setor=setor2,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T6',
            texto='C6',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.ESTABELECIMENTO,
            estabelecimento_id=est1.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is False


def test_user_cannot_view_wrong_setor(client):
    from core.utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        est = user1.celula.estabelecimento
        setor1 = user1.celula.setor
        setor2 = Setor(nome='Setor Z', estabelecimento=est)
        db.session.add(setor2)
        cel2 = Celula(nome='Celula Y', estabelecimento=est, setor=setor2)
        db.session.add(cel2)
        user2 = User(
            username='u7',
            email='u7@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor2,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T7',
            texto='C7',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.SETOR,
            setor_id=setor1.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is False


def test_user_cannot_view_wrong_instituicao(client):
    from core.utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        inst1 = user1.celula.estabelecimento.instituicao
        inst2 = Instituicao(codigo='INST002', nome='Inst 2')
        db.session.add(inst2)
        est2 = Estabelecimento(codigo='E4', nome_fantasia='Est 4', instituicao=inst2)
        db.session.add(est2)
        setor2 = Setor(nome='Setor W', estabelecimento=est2)
        db.session.add(setor2)
        cel2 = Celula(nome='Celula Z', estabelecimento=est2, setor=setor2)
        db.session.add(cel2)
        user2 = User(
            username='u8',
            email='u8@test',
            password_hash='x',
            estabelecimento=est2,
            setor=setor2,
            celula=cel2,
        )
        db.session.add(user2)
        art = Article(
            titulo='T8',
            texto='C8',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.INSTITUICAO,
            instituicao_id=inst1.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is False


def test_user_can_view_setor_visibility_via_extra_setor_herdado(client):
    from core.utils import user_can_view_article
    with app.app_context():
        user = User.query.first()
        est = user.estabelecimento
        setor_extra = Setor(nome='Setor Extra', estabelecimento=est)
        db.session.add(setor_extra)
        db.session.flush()
        cel_extra = Celula(nome='Celula Extra', estabelecimento=est, setor=setor_extra)
        db.session.add(cel_extra)
        db.session.flush()

        user.extra_setores.append(setor_extra)

        art = Article(
            titulo='T9',
            texto='C9',
            user_id=user.id,
            celula_id=user.celula_id,
            visibility=ArticleVisibility.SETOR,
            setor_id=setor_extra.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user, art) is True


def test_celula_visibility_does_not_leak_to_another_celula_same_setor(client):
    from core.utils import user_can_view_article
    with app.app_context():
        user1 = User.query.first()
        est = user1.estabelecimento
        setor = user1.setor
        cel2 = Celula(nome='Celula 2 mesmo setor', estabelecimento=est, setor=setor)
        db.session.add(cel2)
        db.session.flush()

        user2 = User(
            username='u9',
            email='u9@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor,
            celula=cel2,
        )
        db.session.add(user2)

        art = Article(
            titulo='T10',
            texto='C10',
            user_id=user1.id,
            celula_id=user1.celula_id,
            visibility=ArticleVisibility.CELULA,
            vis_celula_id=user1.celula_id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(user2, art) is False


def test_regression_visibility_celula_only_matching_celula_id_or_extra_celulas(client):
    from core.utils import user_can_view_article
    with app.app_context():
        author = User.query.first()
        est = author.estabelecimento
        setor = author.setor
        cel2 = Celula(nome='Celula B', estabelecimento=est, setor=setor)
        db.session.add(cel2)
        db.session.flush()
        viewer = User(
            username='u10',
            email='u10@test',
            password_hash='x',
            estabelecimento=est,
            setor=setor,
            celula=author.celula,
        )
        db.session.add(viewer)
        db.session.flush()

        art = Article(
            titulo='T11',
            texto='C11',
            user_id=author.id,
            celula_id=author.celula_id,
            visibility=ArticleVisibility.CELULA,
            vis_celula_id=cel2.id,
        )
        db.session.add(art)
        db.session.commit()

        assert user_can_view_article(viewer, art) is False
        viewer.extra_celulas.append(cel2)
        db.session.commit()
        assert user_can_view_article(viewer, art) is True
