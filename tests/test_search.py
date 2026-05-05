import pytest

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, User, Article, Attachment, RevisionRequest, ArticleStatus

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
                         mime_type='application/pdf', content='Dom Casmurro',
                         ocr_text='Dom Casmurro', ocr_status='concluido')
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


def test_search_includes_articles_in_review_without_revision_request_details(client):
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
    assert b'Solicita' not in resp.data
    assert b'Ajustar fluxo da se' not in resp.data


def test_search_ignores_pending_and_error_ocr_status(client):
    with app.app_context():
        art_pending = Article(
            titulo='Pendente OCR',
            texto='Texto base',
            status=ArticleStatus.APROVADO,
            user_id=client.user.id,
            celula_id=client.user.celula_id
        )
        db.session.add(art_pending)
        db.session.flush()
        db.session.add(
            Attachment(
                article_id=art_pending.id,
                filename='anexo_pendente.pdf',
                mime_type='application/pdf',
                ocr_text='frase_unica_pendente',
                ocr_status='pendente'
            )
        )

        art_error = Article(
            titulo='Erro OCR',
            texto='Texto base',
            status=ArticleStatus.APROVADO,
            user_id=client.user.id,
            celula_id=client.user.celula_id
        )
        db.session.add(art_error)
        db.session.flush()
        db.session.add(
            Attachment(
                article_id=art_error.id,
                filename='anexo_erro.pdf',
                mime_type='application/pdf',
                ocr_text='frase_unica_erro',
                ocr_status='erro'
            )
        )
        db.session.commit()

    login(client)
    resp_pending = client.get('/pesquisar', query_string={'q': 'frase_unica_pendente'})
    assert resp_pending.status_code == 200
    assert b'Pendente OCR' not in resp_pending.data

    resp_error = client.get('/pesquisar', query_string={'q': 'frase_unica_erro'})
    assert resp_error.status_code == 200
    assert b'Erro OCR' not in resp_error.data


def test_search_includes_concluded_or_low_yield_ocr_status(client):
    with app.app_context():
        art_low = Article(
            titulo='Baixo aproveitamento OCR',
            texto='Texto base',
            status=ArticleStatus.APROVADO,
            user_id=client.user.id,
            celula_id=client.user.celula_id
        )
        db.session.add(art_low)
        db.session.flush()
        db.session.add(
            Attachment(
                article_id=art_low.id,
                filename='anexo_baixo.pdf',
                mime_type='application/pdf',
                ocr_text='frase_unica_baixo_aproveitamento',
                ocr_status='baixo_aproveitamento'
            )
        )
        db.session.commit()

    login(client)
    resp = client.get('/pesquisar', query_string={'q': 'frase_unica_baixo_aproveitamento'})
    assert resp.status_code == 200
    assert b'Baixo aproveitamento OCR' in resp.data


def test_article_search_with_percent_without_edges(client):
    login(client)
    resp = client.get('/pesquisar', query_string={'q': 'Dom%Casmurro'})
    assert resp.status_code == 200
    assert b'Art' in resp.data


def test_article_search_with_percent_prefix_and_suffix(client):
    login(client)
    resp_prefix = client.get('/pesquisar', query_string={'q': '%Casmurro'})
    resp_suffix = client.get('/pesquisar', query_string={'q': 'Dom%'})
    assert resp_prefix.status_code == 200
    assert resp_suffix.status_code == 200
    assert b'Art' in resp_prefix.data
    assert b'Art' in resp_suffix.data
