import pytest


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
