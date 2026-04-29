from io import BytesIO

from app import app, db
from core.enums import ArticleStatus
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User, Article, Attachment


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

        funcoes = []
        for codigo in ('artigo_criar', 'artigo_excluir_definitivo'):
            func = Funcao.query.filter_by(codigo=codigo).first()
            if not func:
                func = Funcao(codigo=codigo, nome=codigo)
                db.session.add(func)
                db.session.flush()
            funcoes.append(func)

        user = User(
            username='logger_user',
            email='logger@test',
            password_hash='x',
            estabelecimento_id=est.id,
            setor_id=setor.id,
            celula_id=cel.id,
        )
        for func in funcoes:
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


def test_excluir_definitivo_emite_evento_hard_delete_com_contexto(monkeypatch, client):
    eventos = []

    def _fake_log_article_event(_logger, event, **context):
        eventos.append((event, context))

    monkeypatch.setattr('blueprints.articles.log_article_event', _fake_log_article_event)

    with app.app_context():
        user = User.query.filter_by(username='logger_user').first()
        artigo = Article(titulo='Delete me', texto='x', status=ArticleStatus.RASCUNHO, user_id=user.id)
        db.session.add(artigo)
        db.session.commit()
        aid = artigo.id

    response = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        headers={'X-Request-ID': 'req-hard-del-1'},
        data={'motivo': 'duplicado', 'confirmacao': 'Delete me'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    hard_delete_ctx = next(ctx for nome, ctx in eventos if nome == 'article_hard_delete')
    assert hard_delete_ctx['user_id'] is not None
    assert hard_delete_ctx['article_id'] == aid
    assert hard_delete_ctx['article_title'] == 'Delete me'
    assert hard_delete_ctx['attachment_count'] == 0
    assert hard_delete_ctx['reason'] == 'duplicado'
    assert hard_delete_ctx['route'] == f'/artigo/{aid}/excluir-definitivo'
    assert hard_delete_ctx['correlation_id'] == 'req-hard-del-1'


def test_excluir_definitivo_bloqueado_emite_evento_com_contexto(monkeypatch, client):
    eventos = []

    def _fake_log_article_event(_logger, event, **context):
        eventos.append((event, context))

    monkeypatch.setattr('blueprints.articles.log_article_event', _fake_log_article_event)

    with app.app_context():
        user = User.query.filter_by(username='logger_user').first()
        artigo = Article(titulo='Blocked delete', texto='x', status=ArticleStatus.RASCUNHO, user_id=user.id)
        db.session.add(artigo)
        db.session.flush()
        db.session.add(Attachment(article_id=artigo.id, filename='lock.pdf', mime_type='application/pdf', ocr_status='processando'))
        db.session.commit()
        aid = artigo.id

    response = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        headers={'X-Request-ID': 'req-hard-del-2'},
        data={'motivo': 'higienizacao', 'confirmacao': 'Blocked delete'},
        follow_redirects=False,
    )

    assert response.status_code == 302
    blocked_ctx = next(ctx for nome, ctx in eventos if nome == 'article_hard_delete_blocked')
    assert blocked_ctx['user_id'] is not None
    assert blocked_ctx['article_id'] == aid
    assert blocked_ctx['article_title'] == 'Blocked delete'
    assert blocked_ctx['attachment_count'] == 1
    assert blocked_ctx['reason'] == 'ocr_processing_in_progress'
    assert blocked_ctx['route'] == f'/artigo/{aid}/excluir-definitivo'
    assert blocked_ctx['correlation_id'] == 'req-hard-del-2'
