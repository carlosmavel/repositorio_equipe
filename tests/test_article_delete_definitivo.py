import os

from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User, Article, Attachment, ArticleDeletionAudit, Comment, RevisionRequest, OCRReprocessAudit, Processo, ProcessoEtapa, TipoOS
from core.enums import ArticleStatus


def _setup_base():
    inst = Instituicao(codigo='INSTDEL', nome='Inst Del')
    db.session.add(inst)
    db.session.flush()
    est = Estabelecimento(codigo='EDEL', nome_fantasia='Est Del', instituicao_id=inst.id)
    db.session.add(est)
    db.session.flush()
    setor = Setor(nome='Setor Del', estabelecimento_id=est.id)
    db.session.add(setor)
    db.session.flush()
    cel = Celula(nome='Cel Del', estabelecimento_id=est.id, setor_id=setor.id)
    db.session.add(cel)
    db.session.commit()
    return est.id, setor.id, cel.id


def _login(client, username='u_del', perms=None):
    perms = perms or []
    with app.app_context():
        est_id, setor_id, cel_id = _setup_base()
        funcoes = []
        for code in perms:
            f = Funcao.query.filter_by(codigo=code).first()
            if not f:
                f = Funcao(codigo=code, nome=code)
                db.session.add(f)
                db.session.flush()
            funcoes.append(f)

        user = User(username=username, email=f'{username}@test', estabelecimento_id=est_id, setor_id=setor_id, celula_id=cel_id)
        user.set_password('x')
        for f in funcoes:
            user.permissoes_personalizadas.append(f)
        db.session.add(user)
        db.session.commit()
        uid = user.id

    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['username'] = username


def _create_article(title='Artigo Teste'):
    article = Article(titulo=title, texto='Conteúdo', status=ArticleStatus.RASCUNHO, user_id=1)
    db.session.add(article)
    db.session.commit()
    return article.id


def test_excluir_definitivo_sem_permissao(client):
    _login(client, perms=[])
    with app.app_context():
        aid = _create_article()

    resp = client.post(f'/artigo/{aid}/excluir-definitivo', data={'motivo': 'x', 'confirmacao': 'CONFIRMAR'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Permiss' in resp.data


def test_botao_excluir_definitivo_visibilidade_condicional(client):
    _login(client, username='u_del', perms=[])
    with app.app_context():
        aid = _create_article('Sem Permissao')
    sem_permissao = client.get(f'/artigo/{aid}')
    assert b'Excluir definitivamente' not in sem_permissao.data

    with app.app_context():
        user = User.query.filter_by(username='u_del').first()
        permissao = Funcao.query.filter_by(codigo='artigo_excluir_definitivo').first()
        if not permissao:
            permissao = Funcao(codigo='artigo_excluir_definitivo', nome='artigo_excluir_definitivo')
            db.session.add(permissao)
            db.session.flush()
        user.permissoes_personalizadas.append(permissao)
        db.session.commit()

    com_permissao = client.get(f'/artigo/{aid}')
    assert b'Excluir definitivamente' in com_permissao.data


def test_excluir_definitivo_confirmacao_invalida(client):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article('Titulo Correto')

    resp = client.post(f'/artigo/{aid}/excluir-definitivo', data={'motivo': 'x', 'confirmacao': 'ERRADO'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Confirma' in resp.data


def test_excluir_definitivo_motivo_ausente(client):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article()

    resp = client.post(f'/artigo/{aid}/excluir-definitivo', data={'motivo': '   ', 'confirmacao': 'CONFIRMAR'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'motivo' in resp.data.lower()


def test_excluir_definitivo_sucesso(client):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article('Titulo Sucesso')
        db.session.add(Attachment(article_id=aid, filename='a.pdf', mime_type='application/pdf', content=None))
        db.session.commit()

    resp = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        headers={'X-Request-ID': 'req-del-1'},
        data={'motivo': 'duplicado', 'confirmacao': 'Titulo Sucesso'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Article.query.get(aid) is None
        audit = ArticleDeletionAudit.query.filter_by(article_id=aid).first()
        assert audit is not None
        assert audit.article_title == 'Titulo Sucesso'
        assert audit.attachment_count == 1
        assert audit.reason == 'duplicado'
        assert audit.request_id == 'req-del-1'
        assert audit.deleted_at is not None


def test_excluir_definitivo_erro_transacional(client, monkeypatch):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article()

    original_commit = db.session.commit

    def _boom():
        raise RuntimeError('erro commit')

    monkeypatch.setattr(db.session, 'commit', _boom)
    resp = client.post(f'/artigo/{aid}/excluir-definitivo', data={'motivo': 'x', 'confirmacao': 'CONFIRMAR'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Falha ao excluir definitivamente' in resp.data

    monkeypatch.setattr(db.session, 'commit', original_commit)
    with app.app_context():
        assert Article.query.get(aid) is not None


def test_excluir_definitivo_remove_historicos_e_arquivo_fisico(client, tmp_path):
    _login(client, perms=['artigo_excluir_definitivo'])
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    with app.app_context():
        aid = _create_article('Titulo Completo')
        attachment = Attachment(article_id=aid, filename='hist.pdf', mime_type='application/pdf', content=None)
        db.session.add(attachment)
        db.session.flush()
        db.session.add(Comment(artigo_id=aid, user_id=1, texto='coment'))
        db.session.add(RevisionRequest(artigo_id=aid, user_id=1, comentario='rev'))
        db.session.add(
            OCRReprocessAudit(
                attachment_id=attachment.id,
                article_id=aid,
                triggered_by_user_id=1,
                trigger_scope='single',
                new_status='pendente',
            )
        )
        db.session.commit()

    filepath = tmp_path / 'hist.pdf'
    filepath.write_bytes(b'pdf')
    assert filepath.exists()

    resp = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        data={'motivo': 'cleanup', 'confirmacao': 'Titulo Completo'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert not filepath.exists()
    with app.app_context():
        assert Article.query.get(aid) is None
        assert Attachment.query.filter_by(article_id=aid).count() == 0
        assert Comment.query.filter_by(artigo_id=aid).count() == 0
        assert RevisionRequest.query.filter_by(artigo_id=aid).count() == 0
        assert OCRReprocessAudit.query.filter_by(article_id=aid).count() == 0


def test_excluir_definitivo_arquivo_faltando_logado_sem_quebrar_consistencia(client, tmp_path, caplog):
    _login(client, perms=['artigo_excluir_definitivo'])
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    with app.app_context():
        aid = _create_article('Titulo Missing File')
        db.session.add(Attachment(article_id=aid, filename='nao-existe.pdf', mime_type='application/pdf', content=None))
        db.session.commit()

    resp = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        data={'motivo': 'cleanup', 'confirmacao': 'Titulo Missing File'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Article.query.get(aid) is None
        assert Attachment.query.filter_by(article_id=aid).count() == 0
    assert any('article_attachment_file_not_found_during_delete' in message for message in caplog.messages)


def _vincular_artigo_a_etapa(article_id, *, processo_ativo=True, tipo_os_obrigatorio=True):
    processo = Processo(nome='Proc Critico' if processo_ativo else 'Proc Inativo', ativo=processo_ativo)
    db.session.add(processo)
    db.session.flush()

    etapa = ProcessoEtapa(processo_id=processo.id, nome='Etapa X', ordem=1)
    db.session.add(etapa)
    db.session.flush()

    tipo_os = TipoOS(nome='Tipo OS X', obrigatorio_preenchimento=tipo_os_obrigatorio)
    db.session.add(tipo_os)
    db.session.flush()

    etapa.tipos_os.append(tipo_os)
    artigo = Article.query.get(article_id)
    etapa.artigos.append(artigo)
    db.session.commit()


def test_excluir_definitivo_com_vinculo_processo_nao_critico_permite(client):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article('Titulo Nao Critico')
        _vincular_artigo_a_etapa(aid, processo_ativo=False, tipo_os_obrigatorio=True)

    resp = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        data={'motivo': 'cleanup', 'confirmacao': 'Titulo Nao Critico'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Article.query.get(aid) is None


def test_excluir_definitivo_com_vinculo_processo_ativo_sem_tipo_obrigatorio_permite(client):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article('Titulo Sem Obrigatorio')
        _vincular_artigo_a_etapa(aid, processo_ativo=True, tipo_os_obrigatorio=False)

    resp = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        data={'motivo': 'cleanup', 'confirmacao': 'Titulo Sem Obrigatorio'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert Article.query.get(aid) is None


def test_excluir_definitivo_com_vinculo_critico_bloqueia(client):
    _login(client, perms=['artigo_excluir_definitivo'])
    with app.app_context():
        aid = _create_article('Titulo Critico')
        _vincular_artigo_a_etapa(aid, processo_ativo=True, tipo_os_obrigatorio=True)

    resp = client.post(
        f'/artigo/{aid}/excluir-definitivo',
        data={'motivo': 'cleanup', 'confirmacao': 'Titulo Critico'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b'Etapa X' in resp.data
    assert b'Proc Critico' in resp.data
    with app.app_context():
        assert Article.query.get(aid) is not None
