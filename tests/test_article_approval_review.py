import pytest


from app import app, db
from core.models import (
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    User,
    Article,
    Funcao,
    ArticleVisibility,
)
from core.enums import Permissao
from core.utils import (
    user_can_approve_article,
    user_can_review_article,
)

@pytest.fixture
def base_setup(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor1 = Setor(nome='S1', estabelecimento=est)
        setor2 = Setor(nome='S2', estabelecimento=est)
        cel1 = Celula(nome='C1', estabelecimento=est, setor=setor1)
        cel2 = Celula(nome='C2', estabelecimento=est, setor=setor1)
        cel3 = Celula(nome='C3', estabelecimento=est, setor=setor2)
        db.session.add_all([inst, est, setor1, setor2, cel1, cel2, cel3])
        db.session.flush()
        author = User(
            username='auth', email='a@test', password_hash='x',
            estabelecimento=est, setor=setor1, celula=cel1
        )
        db.session.add(author)
        db.session.flush()
        art = Article(
            titulo='T', texto='C', user_id=author.id,
            celula_id=cel1.id, setor_id=setor1.id,
            estabelecimento_id=est.id, instituicao_id=inst.id,
            visibility=ArticleVisibility.CELULA
        )
        db.session.add(art)
        db.session.commit()
        data = {
            'inst': inst, 'est': est, 'setor1': setor1, 'setor2': setor2,
            'cel1': cel1, 'cel2': cel2, 'cel3': cel3,
            'author': author, 'article': art
        }
        yield data
        
        


def add_perm(user, code):
    if isinstance(code, Permissao):
        code = code.value
    f = Funcao.query.filter_by(codigo=code).first()
    if not f:
        f = Funcao(codigo=code, nome=code)
        db.session.add(f)
        db.session.flush()
    user.permissoes_personalizadas.append(f)
    db.session.commit()


def test_approve_by_celula(base_setup):
    art = base_setup['article']
    cel1 = base_setup['cel1']
    est = base_setup['est']
    setor1 = base_setup['setor1']
    user = User(username='u1', email='u1@test', password_hash='x',
                estabelecimento=est, setor=setor1, celula=cel1)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_APROVAR_CELULA)
    assert user_can_approve_article(user, art) is True


def test_approve_by_celula_wrong(base_setup):
    art = base_setup['article']
    cel2 = base_setup['cel2']
    est = base_setup['est']
    setor1 = base_setup['setor1']
    user = User(username='u2', email='u2@test', password_hash='x',
                estabelecimento=est, setor=setor1, celula=cel2)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_APROVAR_CELULA)
    assert user_can_approve_article(user, art) is False


def test_review_by_setor(base_setup):
    art = base_setup['article']
    est = base_setup['est']
    setor1 = base_setup['setor1']
    cel2 = base_setup['cel2']
    user = User(username='u3', email='u3@test', password_hash='x',
                estabelecimento=est, setor=setor1, celula=cel2)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_REVISAR_SETOR)
    assert user_can_review_article(user, art) is True


def test_review_by_setor_wrong(base_setup):
    art = base_setup['article']
    est = base_setup['est']
    setor2 = base_setup['setor2']
    cel3 = base_setup['cel3']
    user = User(username='u4', email='u4@test', password_hash='x',
                estabelecimento=est, setor=setor2, celula=cel3)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_REVISAR_SETOR)
    assert user_can_review_article(user, art) is False


def test_approve_levels(base_setup):
    art = base_setup["article"]
    inst = base_setup["inst"]
    est = base_setup["est"]
    setor1 = base_setup["setor1"]
    setor2 = base_setup["setor2"]
    cel1 = base_setup["cel1"]
    cel2 = base_setup["cel2"]
    cel3 = base_setup["cel3"]

    est2 = Estabelecimento(codigo="E2", nome_fantasia="Est2", instituicao=inst)
    setorx = Setor(nome="SX", estabelecimento=est2)
    celx = Celula(nome="CX", estabelecimento=est2, setor=setorx)
    db.session.add_all([est2, setorx, celx])
    db.session.commit()

    cases = [
        (Permissao.ARTIGO_APROVAR_CELULA, est, setor1, cel1),
        (Permissao.ARTIGO_APROVAR_SETOR, est, setor1, cel2),
        (Permissao.ARTIGO_APROVAR_ESTABELECIMENTO, est, setor2, cel3),
        (Permissao.ARTIGO_APROVAR_INSTITUICAO, est2, setorx, celx),
        (Permissao.ARTIGO_APROVAR_TODAS, est2, setorx, celx),
    ]

    for perm, e, s, c in cases:
        user = User(
            username=f"u_{perm.value}",
            email=f"{perm.value}@test",
            password_hash="x",
            estabelecimento=e,
            setor=s,
            celula=c,
        )
        db.session.add(user)
        db.session.commit()
        add_perm(user, perm)
        assert user_can_approve_article(user, art) is True


def test_review_levels(base_setup):
    art = base_setup["article"]
    inst = base_setup["inst"]
    est = base_setup["est"]
    setor1 = base_setup["setor1"]
    setor2 = base_setup["setor2"]
    cel1 = base_setup["cel1"]
    cel2 = base_setup["cel2"]
    cel3 = base_setup["cel3"]

    est2 = Estabelecimento(codigo="E3", nome_fantasia="Est3", instituicao=inst)
    setorx = Setor(nome="SY", estabelecimento=est2)
    celx = Celula(nome="CY", estabelecimento=est2, setor=setorx)
    db.session.add_all([est2, setorx, celx])
    db.session.commit()

    cases = [
        (Permissao.ARTIGO_REVISAR_CELULA, est, setor1, cel1),
        (Permissao.ARTIGO_REVISAR_SETOR, est, setor1, cel2),
        (Permissao.ARTIGO_REVISAR_ESTABELECIMENTO, est, setor2, cel3),
        (Permissao.ARTIGO_REVISAR_INSTITUICAO, est2, setorx, celx),
        (Permissao.ARTIGO_REVISAR_TODAS, est2, setorx, celx),
    ]

    for perm, e, s, c in cases:
        user = User(
            username=f"u_{perm.value}",
            email=f"{perm.value}@test",
            password_hash="x",
            estabelecimento=e,
            setor=s,
            celula=c,
        )
        db.session.add(user)
        db.session.commit()
        add_perm(user, perm)
        assert user_can_review_article(user, art) is True
