from datetime import datetime, timezone

from app import app, db
from core.enums import ArticleStatus
from core.models import (
    Article,
    ArticleDeletionAudit,
    Celula,
    Estabelecimento,
    Funcao,
    Instituicao,
    Setor,
    User,
)


def _setup_user(client, username='notif_user', perms=None):
    perms = perms or []
    with app.app_context():
        inst = Instituicao(codigo=f'INST_{username}', nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo=f'EST_{username}', nome_fantasia='Est', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome=f'Setor {username}', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome=f'Cel {username}', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.flush()

        user = User(username=username, email=f'{username}@test', estabelecimento_id=est.id, setor_id=setor.id, celula_id=cel.id)
        user.set_password('x')
        for code in perms:
            perm = Funcao.query.filter_by(codigo=code).first()
            if not perm:
                perm = Funcao(codigo=code, nome=code)
                db.session.add(perm)
                db.session.flush()
            user.permissoes_personalizadas.append(perm)
        db.session.add(user)
        db.session.commit()
        uid = user.id
        uname = user.username

    with client.session_transaction() as sess:
        sess['user_id'] = uid
        sess['username'] = uname


def test_artigo_url_exibe_tela_amigavel_quando_recurso_foi_excluido(client):
    _setup_user(client)
    resp = client.get('/artigo/999999')
    assert resp.status_code == 200
    assert b'Este artigo n\xc3\xa3o est\xc3\xa1 mais dispon\xc3\xadvel' in resp.data
    assert b'contate o administrador' in resp.data


def test_aprovacao_detail_exibe_auditoria_quando_artigo_excluido(client):
    _setup_user(client, username='aprovador', perms=['artigo_aprovar_todas'])
    with app.app_context():
        autor = User.query.filter_by(username='aprovador').first()
        art = Article(titulo='Artigo auditado', texto='x', status=ArticleStatus.PENDENTE, user_id=autor.id)
        db.session.add(art)
        db.session.flush()
        aid = art.id
        db.session.add(
            ArticleDeletionAudit(
                article_id=aid,
                article_title='Artigo auditado',
                deleted_by_user_id=autor.id,
                deleted_at=datetime.now(timezone.utc),
                reason='limpeza',
                attachment_count=0,
            )
        )
        db.session.delete(art)
        db.session.commit()

    resp = client.get(f'/aprovacao/{aid}')
    assert resp.status_code == 200
    assert b'Detalhes da exclus\xc3\xa3o (auditoria)' in resp.data
    assert b'Artigo auditado' in resp.data
    assert b'limpeza' in resp.data
