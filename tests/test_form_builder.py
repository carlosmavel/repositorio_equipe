import pytest
from app import app, db
from core.models import (
    Cargo,
    Instituicao,
    Estabelecimento,
    Setor,
    Celula,
    User,
    Formulario,
    Secao,
    CampoFormulario,
    Funcao,
)
from core.utils import user_can_access_form_builder

def setup_org(prefix):
    inst = Instituicao(codigo=f'I{str(prefix)[:6]}', nome=f'Inst_{prefix}')
    db.session.add(inst)
    db.session.flush()
    est = Estabelecimento(codigo=f'E_{prefix}', nome_fantasia='Est', instituicao_id=inst.id)
    db.session.add(est)
    db.session.flush()
    setor = Setor(nome=f'Set_{prefix}', estabelecimento_id=est.id)
    db.session.add(setor)
    db.session.flush()
    cel = Celula(nome=f'Cel_{prefix}', estabelecimento_id=est.id, setor_id=setor.id)
    db.session.add(cel)
    db.session.commit()
    return est.id, setor.id, cel.id


def create_user(username, atende=False, admin=False):
    est_id, setor_id, cel_id = setup_org(username)
    cargo = Cargo(nome=f'Cargo_{username}', pode_atender_os=atende)
    db.session.add(cargo)
    if admin:
        funcao_admin = Funcao(codigo='admin', nome='Admin')
        db.session.add(funcao_admin)
        cargo.permissoes.append(funcao_admin)
    db.session.flush()
    user = User(
        username=username,
        email=f'{username}@test',
        estabelecimento_id=est_id,
        setor_id=setor_id,
        celula_id=cel_id,
        cargo_id=cargo.id,
    )
    user.set_password('x')
    db.session.add(user)
    db.session.commit()
    return user.id


@pytest.fixture
def client(app_ctx):
    with app_ctx.test_client() as client:
        yield client


def login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user


def test_permission_function(app_ctx):
    with app_ctx.app_context():
        user_allowed_id = create_user('u1', True)
        user_denied_id = create_user('u2', False)
        user_allowed = User.query.get(user_allowed_id)
        user_denied = User.query.get(user_denied_id)
        assert user_allowed.pode_atender_os is True
        assert user_denied.pode_atender_os is False
        assert user_can_access_form_builder(user_allowed) is True
        assert user_can_access_form_builder(user_denied) is False


def test_admin_has_form_builder_access(client):
    with app.app_context():
        admin_id = create_user('admin_user', atende=False, admin=True)
    login(client, admin_id)
    resp = client.get('/ordem-servico/formularios/')
    assert resp.status_code == 200
    with app.app_context():
        admin = User.query.get(admin_id)
        assert admin.pode_atender_os is True
        assert user_can_access_form_builder(admin) is True


def test_route_permission(client):
    with app.app_context():
        user_denied_id = create_user('deny', False)
    login(client, user_denied_id)
    resp = client.get('/ordem-servico/formularios/')
    assert resp.status_code == 302

    with app.app_context():
        user_allowed_id = create_user('allow', True)
    login(client, user_allowed_id)
    resp = client.get('/ordem-servico/formularios/')
    assert resp.status_code == 200


def test_create_formulario(client):
    with app.app_context():
        user_allowed_id = create_user('creator', True)
    login(client, user_allowed_id)
    resp = client.post('/ordem-servico/formularios/', data={'nome': 'Form1', 'estrutura': '{}'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Form1' in resp.data
    with app.app_context():
        assert Formulario.query.filter_by(nome='Form1').first() is not None


def test_field_added_after_type_selection(client):
    with app.app_context():
        user_allowed_id = create_user('builder_menu', True)
    login(client, user_allowed_id)
    resp = client.get('/ordem-servico/formularios/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'id="previewContainer"' in html
    assert "onclick=\"addField('text')\"" in html


def test_section_model_relationship(app_ctx):
    with app_ctx.app_context():
        user_id = create_user('rel', True)
        user = User.query.get(user_id)
        f = Formulario(nome='F', estrutura='[]', criado_por_id=user.id, celula_id=user.celula_id)
        db.session.add(f)
        db.session.flush()
        s = Secao(formulario_id=f.id, titulo='Sec', ordem=0)
        db.session.add(s)
        db.session.flush()
        c = CampoFormulario(formulario_id=f.id, secao_id=s.id, tipo='text', label='Perg', obrigatoria=False, ordem=0)
        db.session.add(c)
        db.session.commit()
        sec = Secao.query.filter_by(formulario_id=f.id).first()
        assert sec.titulo == 'Sec'
        assert sec.campos[0].label == 'Perg'
        assert sec.campos[0].secao_id == sec.id


def test_toggle_and_filter_formulario(client):
    with app.app_context():
        user_allowed_id = create_user('filter', True)
    login(client, user_allowed_id)
    client.post('/ordem-servico/formularios/', data={'nome': 'FormAtivo', 'estrutura': '{}'}, follow_redirects=True)
    client.post('/ordem-servico/formularios/', data={'nome': 'FormInativo', 'estrutura': '{}'}, follow_redirects=True)
    with app.app_context():
        form_inativo = Formulario.query.filter_by(nome='FormInativo').first()
        form_id = form_inativo.id
    client.post(f'/ordem-servico/formularios/{form_id}/toggle-ativo', follow_redirects=True)
    resp = client.get('/ordem-servico/formularios/?status=ativos')
    assert b'FormAtivo' in resp.data
    assert b'FormInativo' not in resp.data
    resp = client.get('/ordem-servico/formularios/?status=inativos')
    assert b'FormInativo' in resp.data
    assert b'FormAtivo' not in resp.data
    resp = client.get('/ordem-servico/formularios/?status=todos')
    assert b'FormAtivo' in resp.data and b'FormInativo' in resp.data


def test_filter_and_search_visible_with_no_active_forms(client):
    with app.app_context():
        user_allowed_id = create_user('noactive', True)
    login(client, user_allowed_id)
    client.post('/ordem-servico/formularios/', data={'nome': 'FormX', 'estrutura': '{}'}, follow_redirects=True)
    with app.app_context():
        form = Formulario.query.filter_by(nome='FormX').first()
        form_id = form.id
    client.post(f'/ordem-servico/formularios/{form_id}/toggle-ativo', follow_redirects=True)
    resp = client.get('/ordem-servico/formularios/?status=ativos')
    assert b'id="formSearch"' in resp.data
    assert b'name="status"' in resp.data
    assert b'Nenhum formul' in resp.data


def test_formulario_visibility_by_celula(client):
    with app.app_context():
        u1_id = create_user('vis1', True)
        u2_id = create_user('vis2', True)
    login(client, u1_id)
    client.post('/ordem-servico/formularios/', data={'nome': 'FormU1', 'estrutura': '{}'}, follow_redirects=True)
    login(client, u2_id)
    resp = client.get('/ordem-servico/formularios/')
    assert b'FormU1' not in resp.data
