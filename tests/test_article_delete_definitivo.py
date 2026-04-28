from app import app, db
from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User, Article, Attachment, ArticleDeletionAudit
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
