import pytest


from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User, Article, ArticleStatus
from core.enums import Permissao
from core.utils import (
    user_can_edit_article,
    user_can_approve_article,
    user_can_review_article,
    user_can_view_article,
)

@pytest.fixture
def client(app_ctx):
    
    with app.app_context():
        
        inst = Instituicao(codigo='INST001', nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Setor', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
        with app_ctx.test_client() as client:
            client.base_ids = ids
            yield client
        
        

def login_user(client, perms=None):
    perms = perms or []
    ids = client.base_ids
    with app.app_context():
        db.session.query(User).delete()
        db.session.commit()
        funcoes = []
        for code in perms:
            if isinstance(code, Permissao):
                code = code.value
            f = Funcao.query.filter_by(codigo=code).first()
            if not f:
                f = Funcao(codigo=code, nome=code)
                db.session.add(f)
                db.session.flush()
            funcoes.append(f)
        user = User(username='u', email='u@test', estabelecimento_id=ids['est'], setor_id=ids['setor'], celula_id=ids['cel'])
        user.set_password('x')
        for f in funcoes:
            user.permissoes_personalizadas.append(f)
        db.session.add(user)
        db.session.commit()
        uid = user.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_novo_artigo_requires_permission(client):
    login_user(client, [])
    resp = client.get('/novo-artigo')
    assert resp.status_code == 302
    assert '/meus-artigos' in resp.headers['Location']

    login_user(client, ['artigo_criar'])
    resp = client.get('/novo-artigo')
    assert resp.status_code == 200

def test_aprovacao_requires_permission(client):
    login_user(client, [])
    resp = client.get('/aprovacao')
    assert resp.status_code == 302

    login_user(client, [Permissao.ARTIGO_APROVAR_CELULA])
    resp = client.get('/aprovacao')
    assert resp.status_code == 200


class _EmptyRelation:
    def filter_by(self, **kwargs):
        return self

    def count(self):
        return 0

    def all(self):
        return []


class _FakeUser:
    def __init__(self, perms=None, user_id=123):
        self._perms = set(perms or [])
        self.id = user_id
        self.estabelecimento = None
        self.celula = None
        self.setor = None
        self.setor_id = None
        self.celula_id = None
        self.extra_setores = _EmptyRelation()
        self.extra_celulas = _EmptyRelation()

    def has_permissao(self, code):
        return code in self._perms


def _build_article(author_id=999):
    return Article(titulo='Art', texto='Texto', status=ArticleStatus.APROVADO, user_id=author_id)


@pytest.mark.parametrize(
    "checker",
    [
        user_can_edit_article,
        user_can_approve_article,
        user_can_review_article,
        user_can_view_article,
    ],
)
def test_user_none_returns_false_without_exception(checker):
    article = _build_article()
    assert checker(None, article) is False


def test_valid_user_permissions_keep_current_behavior():
    article = _build_article(author_id=999)
    admin = _FakeUser(perms={'admin'}, user_id=123)

    assert user_can_edit_article(admin, article) is True
    assert user_can_review_article(admin, article) is True
    assert user_can_view_article(admin, article) is True
    assert user_can_approve_article(admin, article) is True


def test_pesquisar_filter_with_none_user_does_not_raise_exception():
    articles = [_build_article(author_id=1), _build_article(author_id=2)]
    filtered = [a for a in articles if user_can_view_article(None, a)]
    assert filtered == []
