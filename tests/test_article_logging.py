from io import BytesIO

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User


import pytest


@pytest.fixture
def client(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo='IL', nome='Inst Log')
        est = Estabelecimento(codigo='EL', nome_fantasia='Est Log', instituicao=inst)
        setor = Setor(nome='Setor Log', estabelecimento=est)
        cel = Celula(nome='Cel Log', estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, cel])
        db.session.commit()

        func = Funcao.query.filter_by(codigo='artigo_criar').first()
        if not func:
            func = Funcao(codigo='artigo_criar', nome='artigo_criar')
            db.session.add(func)
            db.session.flush()

        user = User(
            username='logger_user',
            email='logger@test',
            password_hash='x',
            estabelecimento_id=est.id,
            setor_id=setor.id,
            celula_id=cel.id,
        )
        user.permissoes_personalizadas.append(func)
        db.session.add(user)
        db.session.commit()
        uid = user.id

        with app_ctx.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = uid
                sess['username'] = 'logger_user'
            yield client


def test_novo_artigo_emite_eventos_criticos_com_contexto(monkeypatch, client):
    eventos = []

    def _fake_log_article_event(_logger, event, **context):
        eventos.append((event, context))

    monkeypatch.setattr('blueprints.articles.log_article_event', _fake_log_article_event)

    response = client.post(
        '/novo-artigo',
        headers={'X-Request-ID': 'req-123'},
        data={
            'titulo': 'Artigo com log',
            'texto': 'Conteudo',
            'visibility': 'celula',
            'acao': 'enviar',
            'progress_id': 'prog-1',
            'files': (BytesIO(b'conteudo txt'), 'arquivo.txt'),
        },
        content_type='multipart/form-data',
        follow_redirects=False,
    )

    assert response.status_code == 302
    nomes = [nome for nome, _ in eventos]
    assert 'article_create_started' in nomes
    assert 'article_attachment_registered' in nomes
    assert 'article_create_committed' in nomes

    attachment_ctx = next(ctx for nome, ctx in eventos if nome == 'article_attachment_registered')
    assert attachment_ctx['user_id'] is not None
    assert attachment_ctx['route'] == '/novo-artigo'
    assert attachment_ctx['action'] == 'enviar'
    assert attachment_ctx['filename'].endswith('_arquivo.txt')
    assert attachment_ctx['file_size'] == len(b'conteudo txt')
    assert attachment_ctx['mime_type'] == 'text/plain'
    assert attachment_ctx['progress_id'] == 'prog-1'
    assert attachment_ctx['correlation_id'] == 'req-123'


def test_articles_propagam_x_request_id_no_response(client):
    response = client.get('/upload-progress/abc', headers={'X-Request-ID': 'corr-xyz'})
    assert response.status_code == 200
    assert response.headers.get('X-Request-ID') == 'corr-xyz'
