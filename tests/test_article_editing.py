import os
import pytest

os.environ['SECRET_KEY'] = 'test_secret'
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'

from app import app, db
from models import (
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    User,
    Article,
    Funcao,
    ArticleVisibility,
)
from enums import Permissao
from utils import user_can_edit_article, user_can_view_article

@pytest.fixture
def base_setup():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        inst = Instituicao(nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor1 = Setor(nome='S1', estabelecimento=est)
        setor2 = Setor(nome='S2', estabelecimento=est)
        cel1 = Celula(nome='C1', estabelecimento=est, setor=setor1)
        cel2 = Celula(nome='C2', estabelecimento=est, setor=setor1)
        cel3 = Celula(nome='C3', estabelecimento=est, setor=setor2)
        db.session.add_all([inst, est, setor1, setor2, cel1, cel2, cel3])
        db.session.flush()
        author = User(username='auth', email='a@test', password_hash='x',
                      estabelecimento=est, setor=setor1, celula=cel1)
        db.session.add(author)
        db.session.flush()
        art = Article(titulo='T', texto='C', user_id=author.id,
                      celula_id=cel1.id, setor_id=setor1.id,
                      estabelecimento_id=est.id, instituicao_id=inst.id,
                      visibility=ArticleVisibility.CELULA)
        db.session.add(art)
        db.session.commit()
        data = {
            'inst': inst, 'est': est, 'setor1': setor1, 'setor2': setor2,
            'cel1': cel1, 'cel2': cel2, 'cel3': cel3,
            'author': author, 'article': art
        }
        yield data
        db.session.remove()
        db.drop_all()

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


def test_edit_by_celula(base_setup):
    art = base_setup['article']
    cel1 = base_setup['cel1']
    est = base_setup['est']
    setor1 = base_setup['setor1']
    user = User(username='u1', email='u1@test', password_hash='x',
                estabelecimento=est, setor=setor1, celula=cel1)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_EDITAR_CELULA)
    assert user_can_edit_article(user, art) is True
    assert user_can_view_article(user, art) is True


def test_edit_by_celula_wrong(base_setup):
    art = base_setup['article']
    cel2 = base_setup['cel2']
    est = base_setup['est']
    setor1 = base_setup['setor1']
    user = User(username='u2', email='u2@test', password_hash='x',
                estabelecimento=est, setor=setor1, celula=cel2)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_EDITAR_CELULA)
    assert user_can_edit_article(user, art) is False
    assert user_can_view_article(user, art) is False


def test_edit_by_setor(base_setup):
    art = base_setup['article']
    est = base_setup['est']
    setor1 = base_setup['setor1']
    cel2 = base_setup['cel2']
    user = User(username='u3', email='u3@test', password_hash='x',
                estabelecimento=est, setor=setor1, celula=cel2)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_EDITAR_SETOR)
    assert user_can_edit_article(user, art) is True


def test_edit_by_setor_wrong(base_setup):
    art = base_setup['article']
    est = base_setup['est']
    setor2 = base_setup['setor2']
    cel3 = base_setup['cel3']
    user = User(username='u4', email='u4@test', password_hash='x',
                estabelecimento=est, setor=setor2, celula=cel3)
    db.session.add(user)
    db.session.commit()
    add_perm(user, Permissao.ARTIGO_EDITAR_SETOR)
    assert user_can_edit_article(user, art) is False

