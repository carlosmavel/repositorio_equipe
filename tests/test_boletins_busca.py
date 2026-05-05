from datetime import date

from app import app, db
from core.models import Boletim, Celula, Estabelecimento, Funcao, Instituicao, Setor, User


def _grant_permissions(user, permissions):
    for codigo in permissions:
        funcao = Funcao.query.filter_by(codigo=codigo).first()
        if not funcao:
            funcao = Funcao(codigo=codigo, nome=codigo)
            db.session.add(funcao)
            db.session.flush()
        user.permissoes_personalizadas.append(funcao)


def _setup_user(client, permissions):
    inst = Instituicao(codigo='IBUSCA', nome='Inst Busca')
    est = Estabelecimento(codigo='EBUSCA', nome_fantasia='Est Busca', instituicao=inst)
    setor = Setor(nome='Setor Busca', estabelecimento=est)
    cel = Celula(nome='Celula Busca', estabelecimento=est, setor=setor)
    db.session.add_all([inst, est, setor, cel])
    db.session.flush()

    user = User(username='busca_user', email='busca@test.local', estabelecimento=est, setor=setor, celula=cel)
    user.set_password('123')
    db.session.add(user)
    db.session.flush()

    _grant_permissions(user, permissions)
    db.session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = user.username

    return user


def _create_boletim(user, titulo, ocr_text, data):
    boletim = Boletim(titulo=titulo, ocr_text=ocr_text, arquivo=f'{titulo}.pdf', data_boletim=data, created_by=user.id)
    db.session.add(boletim)
    db.session.commit()
    return boletim


def test_busca_boletim_match_titulo(client):
    with app.app_context():
        user = _setup_user(client, ['boletim_buscar', 'boletim_visualizar'])
        _create_boletim(user, 'Comunicado Geral de RH', 'Texto irrelevante', date(2026, 1, 1))

    resp = client.get('/boletins/buscar', query_string={'q': 'Comunicado'})

    assert resp.status_code == 200
    assert b'Comunicado Geral de RH' in resp.data


def test_busca_boletim_match_ocr(client):
    with app.app_context():
        user = _setup_user(client, ['boletim_buscar', 'boletim_visualizar'])
        _create_boletim(user, 'Atualização Financeira', 'Processo de faturamento consolidado', date(2026, 1, 2))

    resp = client.get('/boletins/buscar', query_string={'q': 'faturamento'})

    assert resp.status_code == 200
    assert b'Atualiza' in resp.data



def test_busca_boletim_ignora_acentos(client):
    with app.app_context():
        user = _setup_user(client, ['boletim_buscar', 'boletim_visualizar'])
        _create_boletim(user, 'Boletim de Ação Integrada', 'Texto com informação técnica', date(2026, 1, 3))

    resp = client.get('/boletins/buscar', query_string={'q': '%acao%'})

    assert resp.status_code == 200
    assert b'Boletim de A' in resp.data

def test_busca_boletim_sem_permissao(client):
    with app.app_context():
        _setup_user(client, ['boletim_visualizar'])

    resp = client.get('/boletins/buscar', follow_redirects=True)

    assert resp.status_code == 200
    assert b'Permiss' in resp.data


def test_listagem_exibe_atalho_buscar_com_permissao(client):
    with app.app_context():
        _setup_user(client, ['boletim_buscar', 'boletim_visualizar'])

    resp = client.get('/boletins')

    assert resp.status_code == 200
    assert b'Pesquisar boletins' in resp.data
    assert b'>Buscar<' in resp.data


def test_listagem_oculta_atalho_buscar_sem_permissao(client):
    with app.app_context():
        _setup_user(client, ['boletim_visualizar'])

    resp = client.get('/boletins')

    assert resp.status_code == 200
    assert b'Pesquisar boletins' not in resp.data
    assert b'>Buscar<' not in resp.data


def test_busca_boletim_frase_exata_sem_percentual(client):
    with app.app_context():
        user = _setup_user(client, ['boletim_buscar', 'boletim_visualizar'])
        _create_boletim(user, 'Comunicado Dia dos pais 2026', 'Texto irrelevante', date(2026, 1, 4))
        _create_boletim(user, 'Comunicado Dia livre dos pais 2026', 'Texto irrelevante', date(2026, 1, 5))

    resp = client.get('/boletins/buscar', query_string={'q': 'Dia dos pais'})

    assert resp.status_code == 200
    assert b'Comunicado Dia dos pais 2026' in resp.data
    assert b'Comunicado Dia livre dos pais 2026' not in resp.data


def test_busca_boletim_aproximada_com_percentual(client):
    with app.app_context():
        user = _setup_user(client, ['boletim_buscar', 'boletim_visualizar'])
        _create_boletim(user, 'Comunicado Dia livre dos pais 2026', 'Texto irrelevante', date(2026, 1, 6))

    resp = client.get('/boletins/buscar', query_string={'q': '%Dia%pais%'})

    assert resp.status_code == 200
    assert b'Comunicado Dia livre dos pais 2026' in resp.data
