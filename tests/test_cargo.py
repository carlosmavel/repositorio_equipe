import pytest
from pathlib import Path


from app import app, db
from core.models import Cargo, Instituicao, Estabelecimento, Setor, Celula, Funcao, User

@pytest.fixture
def client(app_ctx):

    with app.app_context():
        
        inst = Instituicao(codigo='INST001', nome='Inst')
        db.session.add(inst)
        db.session.flush()
        est = Estabelecimento(codigo='E1', nome_fantasia='Estab', instituicao_id=inst.id)
        db.session.add(est)
        db.session.flush()
        setor = Setor(nome='Setor1', estabelecimento_id=est.id)
        db.session.add(setor)
        db.session.flush()
        cel = Celula(nome='Cel1', estabelecimento_id=est.id, setor_id=setor.id)
        db.session.add(cel)
        db.session.commit()
        base_ids = {'est': est.id, 'setor': setor.id, 'cel': cel.id}
        with app_ctx.test_client() as client:
            client.base_ids = base_ids
            yield client
        
        

def login_admin(client):
    ids = client.base_ids
    with app.app_context():
        f = Funcao.query.filter_by(codigo='admin').first()
        if not f:
            f = Funcao(codigo='admin', nome='Admin')
            db.session.add(f)
            db.session.commit()
        u = User(username='adm', email='adm@test', estabelecimento_id=ids['est'], setor_id=ids['setor'], celula_id=ids['cel'])
        u.set_password('x')
        u.permissoes_personalizadas.append(f)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    with client.session_transaction() as sess:
        sess['user_id'] = uid


def test_create_cargo(client):
    login_admin(client)
    ids = client.base_ids
    with app.app_context():
        f = Funcao(codigo='TEST', nome='Teste')
        db.session.add(f)
        db.session.commit()
        fid = f.id
    response = client.post('/admin/cargos', data={
        'nome': 'Analista',
        'descricao': 'Analisa as coisas',
        'nivel_hierarquico': '3',
        'ativo_check': 'on',
        'setor_ids': [str(ids['setor'])],
        'celula_ids': [str(ids['cel'])],
        'funcao_ids': [str(fid)]
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        cargo = Cargo.query.filter_by(nome='Analista').first()
        assert cargo is not None
        assert cargo.descricao == 'Analisa as coisas'
        assert cargo.nivel_hierarquico == 3
        assert cargo.ativo is True
        assert cargo.default_setores.filter_by(id=ids['setor']).count() == 1
        assert cargo.default_celulas.filter_by(id=ids['cel']).count() == 1
        assert cargo.permissoes.filter_by(id=fid).count() == 1


def test_cargo_explorer_starts_collapsed_with_accessible_controls(client):
    login_admin(client)
    response = client.get('/admin/cargos')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="collapse show hier-children"' not in html
    assert 'class="collapse hier-children"' in html
    assert 'aria-expanded="false"' in html
    assert 'aria-label="Expandir instituição Inst"' in html
    assert 'aria-label="Expandir estabelecimento Estab"' in html
    assert 'aria-label="Expandir setor Setor1"' in html
    assert 'aria-label="Expandir célula Cel1"' in html
    assert 'id="toggleAllCargos"' in html
    assert 'id="cargoResultCount"' in html
    assert 'id="cargoSearchEmpty"' in html


def test_cargo_linked_to_multiple_cells_is_rendered_once_at_sector_level(client):
    login_admin(client)
    ids = client.base_ids
    with app.app_context():
        segunda_celula = Celula(
            nome='Cel2', estabelecimento_id=ids['est'], setor_id=ids['setor']
        )
        cargo = Cargo(nome='Gestor compartilhado', nivel_hierarquico=1, ativo=True)
        cargo.default_estabelecimentos.append(Estabelecimento.query.get(ids['est']))
        cargo.default_setores.append(Setor.query.get(ids['setor']))
        cargo.default_celulas.extend([Celula.query.get(ids['cel']), segunda_celula])
        db.session.add_all([segunda_celula, cargo])
        db.session.commit()

    html = client.get('/admin/cargos').get_data(as_text=True)

    assert html.count('data-cargo="Gestor compartilhado"') == 1
    setor_inicio = html.index('id="setor-')
    cargo_posicao = html.index('data-cargo="Gestor compartilhado"')
    primeira_celula = html.index('class="hier-node level-celula', setor_inicio)
    assert setor_inicio < cargo_posicao < primeira_celula


def test_cargo_template_uses_single_surface_macro_and_event_driven_search():
    source = (Path(__file__).parents[1] / 'templates' / 'admin' / 'cargos.html').read_text(encoding='utf-8')

    assert '{% macro cargo_linha(' in source
    assert source.count('class="cargo-item"') == 1
    assert 'card-body p-0' not in source
    assert 'tab-content' not in source
    assert 'tab-pane' not in source
    assert 'shown.bs.collapse' in source
    assert 'hidden.bs.collapse' in source
    assert "setTimeout(function()" not in source
    assert "ancestors(item).forEach" in source
    assert "autoOpened.forEach" in source
    assert "manualOpened.has(id)" in source
