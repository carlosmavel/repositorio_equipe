import pytest

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, User, Cargo, Article, Attachment, RevisionRequest, ArticleStatus

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


def test_search_includes_articles_in_review_without_polluting_results(client):
    with app.app_context():
        art_review = Article(
            titulo='Artigo em revisão',
            texto='Texto revisão',
            status=ArticleStatus.EM_REVISAO,
            user_id=client.user.id,
            celula_id=client.user.celula_id
        )
        db.session.add(art_review)
        db.session.flush()

        pedido = RevisionRequest(
            artigo_id=art_review.id,
            user_id=client.user.id,
            comentario='Ajustar fluxo da seção 2'
        )
        db.session.add(pedido)
        db.session.commit()

    login(client)
    resp = client.get('/pesquisar', query_string={'q': 'revisão'})
    assert resp.status_code == 200
    assert b'Artigo em revis' in resp.data
    html = resp.get_data(as_text=True)
    assert 'Solicita' not in html
    assert 'Solicitação de revisão:' not in html
    assert 'Solicitado por:' not in html
    assert 'Ajustar fluxo da seção 2' not in html


def test_article_page_shows_revision_history_with_full_name_and_cargo(client):
    est_id = client.user.estabelecimento_id
    setor_id = client.user.setor_id
    celula_id = client.user.celula_id

    with app.app_context():
        cargo = Cargo(nome='Coordenador')
        db.session.add(cargo)
        db.session.flush()

        solicitante = User(
            username='solicitante',
            nome_completo='Maria da Silva Santos',
            email='solicitante@test',
            password_hash='x',
            estabelecimento_id=est_id,
            setor_id=setor_id,
            celula_id=celula_id,
            cargo_id=cargo.id,
        )
        db.session.add(solicitante)
        db.session.flush()

        art_review = Article(
            titulo='Artigo com histórico',
            texto='Texto histórico',
            status=ArticleStatus.EM_REVISAO,
            user_id=client.user.id,
            celula_id=client.user.celula_id,
        )
        db.session.add(art_review)
        db.session.flush()

        pedido = RevisionRequest(
            artigo_id=art_review.id,
            user_id=solicitante.id,
            comentario='Revisar indicadores da seção final',
        )
        db.session.add(pedido)
        db.session.commit()
        artigo_id = art_review.id

    login(client)
    resp = client.get(f'/artigo/{artigo_id}')
    assert resp.status_code == 200
    assert b'Hist' in resp.data
    assert b'Maria da Silva Santos' in resp.data
    assert b'Coordenador' in resp.data
    assert b'Revisar indicadores da se' in resp.data
