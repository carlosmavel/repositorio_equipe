from datetime import datetime, timedelta, timezone

import pytest

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User, Article, Attachment


@pytest.fixture
def client(app_ctx):
    with app.app_context():
        inst = Instituicao(codigo='INST001', nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Est', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Set', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        with app_ctx.test_client() as client:
            client.base_ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
            yield client


def login_admin(client):
    ids = client.base_ids
    with app.app_context():
        f = Funcao.query.filter_by(codigo='admin').first()
        if not f:
            f = Funcao(codigo='admin', nome='Admin')
            db.session.add(f)
            db.session.commit()
        u = User(
            username='adm',
            email='adm@test',
            estabelecimento_id=ids['est'],
            setor_id=ids['setor'],
            celula_id=ids['cel'],
        )
        u.set_password('x')
        u.permissoes_personalizadas.append(f)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_admin_dashboard(client):
    login_admin(client)
    ids = client.base_ids
    now = datetime.now(timezone.utc)
    with app.app_context():
        admin_user = User.query.filter_by(username='adm').first()
        article = Article(
            titulo='Artigo OCR',
            texto='conteudo',
            user_id=admin_user.id,
            celula_id=ids['cel'],
        )
        db.session.add(article)
        db.session.flush()

        db.session.add_all([
            Attachment(
                article_id=article.id,
                filename='pendente.pdf',
                original_filename='pendente.pdf',
                mime_type='application/pdf',
                ocr_status='pendente',
            ),
            Attachment(
                article_id=article.id,
                filename='processando.pdf',
                original_filename='processando.pdf',
                mime_type='application/pdf',
                ocr_status='processando',
                ocr_started_at=now - timedelta(minutes=45),
            ),
            Attachment(
                article_id=article.id,
                filename='concluido.pdf',
                original_filename='concluido.pdf',
                mime_type='application/pdf',
                ocr_status='concluido',
                ocr_char_count=120,
                ocr_processing_time_seconds=10.2,
            ),
            Attachment(
                article_id=article.id,
                filename='erro.pdf',
                original_filename='erro.pdf',
                mime_type='application/pdf',
                ocr_status='erro',
                ocr_last_error='Falha no OCR',
                ocr_char_count=0,
                ocr_processing_time_seconds=4.0,
            ),
            Attachment(
                article_id=article.id,
                filename='baixo.pdf',
                original_filename='baixo.pdf',
                mime_type='application/pdf',
                ocr_status='baixo_aproveitamento',
                ocr_error_message='Texto insuficiente',
                ocr_char_count=22,
                ocr_processing_time_seconds=3.3,
            ),
        ])
        db.session.commit()

    resp = client.get('/admin/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'OCR por Status (Elegíveis)' in html
    assert 'Resumo OCR' in html
    assert 'Total elegível:</strong> 5' in html
    assert 'Últimos erros OCR' in html
    assert 'Falha no OCR' in html
    assert 'Texto insuficiente' in html
    assert 'Itens presos em processando' in html
    assert '(artigo' in html
