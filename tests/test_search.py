import pytest

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, User, Article, Attachment, ArticleStatus

@pytest.fixture
def client(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo='INST001', nome='Inst')
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao=inst)
        setor = Setor(nome='S', estabelecimento=est)
        cel = Celula(nome='C', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.flush()
        user = User(username='u', email='u@test', password_hash='x',
                    estabelecimento=est, setor=setor, celula=cel)
        db.session.add(user)
        db.session.flush()
        art = Article(titulo='Art', texto='Texto', status=ArticleStatus.APROVADO,
                      user_id=user.id, celula_id=cel.id)
        db.session.add(art)
        db.session.flush()
        att = Attachment(article_id=art.id, filename='dom_casmurro.pdf',
                         mime_type='application/pdf', content='Dom Casmurro')
        db.session.add(att)
        db.session.commit()
        with app_ctx.test_client() as client:
            client.user = user
            yield client

def login(client):
    with client.session_transaction() as sess:
        sess['user_id'] = client.user.id
        sess['username'] = client.user.username


def test_partial_search_attachment_content(client):
    login(client)
    resp = client.get('/pesquisar', query_string={'q': 'casm'})
    assert resp.status_code == 200
    assert b'Art' in resp.data


def test_exact_phrase_search(client):
    login(client)
    resp = client.get('/pesquisar', query_string={'q': '"Dom Casmurro"'})
    assert resp.status_code == 200
    assert b'Art' in resp.data
