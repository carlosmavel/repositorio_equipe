from core.database import db
from core.models import (
    Article,
    Attachment,
    Celula,
    Estabelecimento,
    Funcao,
    Instituicao,
    OCRReprocessAudit,
    Setor,
    User,
)
from core.permission_catalog import CATALOG_BY_CODE


def _login_with_permissions(client, permissions):
    inst = Instituicao(codigo='INSTOCR', nome='Instituição OCR')
    db.session.add(inst)
    db.session.flush()

    est = Estabelecimento(codigo='ESTOCR', nome_fantasia='Est OCR', instituicao_id=inst.id)
    db.session.add(est)
    db.session.flush()

    setor = Setor(nome='Setor OCR', estabelecimento_id=est.id)
    db.session.add(setor)
    db.session.flush()

    cel = Celula(nome='Célula OCR', estabelecimento_id=est.id, setor_id=setor.id)
    db.session.add(cel)
    db.session.flush()

    user = User(
        username='ocr_user',
        email='ocr_user@test.local',
        estabelecimento_id=est.id,
        setor_id=setor.id,
        celula_id=cel.id,
    )
    user.set_password('x')
    db.session.add(user)
    db.session.flush()

    for codigo in permissions:
        funcao = Funcao.query.filter_by(codigo=codigo).first()
        if not funcao:
            funcao = Funcao(codigo=codigo, nome=codigo)
            db.session.add(funcao)
            db.session.flush()
        user.permissoes_personalizadas.append(funcao)

    db.session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = user.username

    return user


def _criar_artigo_com_anexos(user, status_pdf='erro'):
    artigo = Article(titulo='Artigo OCR', texto='Texto', user_id=user.id, celula_id=user.celula_id)
    db.session.add(artigo)
    db.session.flush()

    anexo_pdf = Attachment(
        article_id=artigo.id,
        filename='arquivo.pdf',
        mime_type='application/pdf',
        ocr_status=status_pdf,
        ocr_attempts=2,
    )
    anexo_txt = Attachment(
        article_id=artigo.id,
        filename='arquivo.txt',
        mime_type='text/plain',
        ocr_status='nao_aplicavel',
        ocr_attempts=0,
    )
    db.session.add_all([anexo_pdf, anexo_txt])
    db.session.commit()
    return artigo, anexo_pdf, anexo_txt


def test_permission_catalog_includes_artigo_ocr_reprocessar(app_ctx):
    assert 'artigo_ocr_reprocessar' in CATALOG_BY_CODE


def test_admin_reprocess_attachment_requires_permission(client):
    user = _login_with_permissions(client, [])
    _, anexo_pdf, _ = _criar_artigo_com_anexos(user)

    resp = client.post(f'/admin/ocr/reprocess/attachment/{anexo_pdf.id}', follow_redirects=False)

    assert resp.status_code == 302
    assert '/meus-artigos' in resp.headers['Location']


def test_admin_reprocess_attachment_updates_state_attempt_and_audit(client):
    user = _login_with_permissions(client, ['artigo_ocr_reprocessar'])
    _, anexo_pdf, _ = _criar_artigo_com_anexos(user)

    resp = client.post(f'/admin/ocr/reprocess/attachment/{anexo_pdf.id}', follow_redirects=False)

    assert resp.status_code == 302
    db.session.refresh(anexo_pdf)
    assert anexo_pdf.ocr_status == 'pendente'
    assert anexo_pdf.ocr_attempts == 3

    auditoria = OCRReprocessAudit.query.filter_by(attachment_id=anexo_pdf.id).one()
    assert auditoria.triggered_by_user_id == user.id
    assert auditoria.trigger_scope == 'attachment'
    assert auditoria.previous_status == 'erro'
    assert auditoria.new_status == 'pendente'
    assert auditoria.attempts_before == 2
    assert auditoria.attempts_after == 3


def test_admin_reprocess_article_reprocesses_only_pdf_attachments(client):
    user = _login_with_permissions(client, ['admin'])
    artigo, anexo_pdf, anexo_txt = _criar_artigo_com_anexos(user, status_pdf='baixo_aproveitamento')

    resp = client.post(f'/admin/ocr/reprocess/article/{artigo.id}', follow_redirects=False)

    assert resp.status_code == 302
    db.session.refresh(anexo_pdf)
    db.session.refresh(anexo_txt)
    assert anexo_pdf.ocr_status == 'pendente'
    assert anexo_pdf.ocr_attempts == 3
    assert anexo_txt.ocr_status == 'nao_aplicavel'
    assert anexo_txt.ocr_attempts == 0


def test_admin_reprocess_bulk_by_status(client):
    user = _login_with_permissions(client, ['artigo_ocr_reprocessar'])

    artigo_erro = Article(titulo='Artigo erro', texto='Texto', user_id=user.id, celula_id=user.celula_id)
    artigo_baixo = Article(titulo='Artigo baixo', texto='Texto', user_id=user.id, celula_id=user.celula_id)
    db.session.add_all([artigo_erro, artigo_baixo])
    db.session.flush()

    anexo_erro = Attachment(
        article_id=artigo_erro.id,
        filename='erro.pdf',
        mime_type='application/pdf',
        ocr_status='erro',
        ocr_attempts=1,
    )
    anexo_baixo = Attachment(
        article_id=artigo_baixo.id,
        filename='baixo.pdf',
        mime_type='application/pdf',
        ocr_status='baixo_aproveitamento',
        ocr_attempts=4,
    )
    db.session.add_all([anexo_erro, anexo_baixo])
    db.session.commit()

    resp_erro = client.post('/admin/ocr/reprocess/errors', follow_redirects=False)
    resp_baixo = client.post('/admin/ocr/reprocess/low-yield', follow_redirects=False)

    assert resp_erro.status_code == 302
    assert resp_baixo.status_code == 302

    db.session.refresh(anexo_erro)
    db.session.refresh(anexo_baixo)
    assert anexo_erro.ocr_status == 'pendente'
    assert anexo_erro.ocr_attempts == 2
    assert anexo_baixo.ocr_status == 'pendente'
    assert anexo_baixo.ocr_attempts == 5
