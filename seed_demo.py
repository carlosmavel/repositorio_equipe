try:
    from .database import db
except ImportError:
    from database import db

try:
    from .models import Instituicao, Estabelecimento, Setor, Celula, Cargo, Funcao, User
except ImportError:
    from models import Instituicao, Estabelecimento, Setor, Celula, Cargo, Funcao, User

try:
    from .enums import Permissao
except ImportError:
    from enums import Permissao

from werkzeug.security import generate_password_hash
from app import app
import seed_funcoes


def get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if not instance:
        params = defaults or {}
        params.update(kwargs)
        instance = model(**params)
        db.session.add(instance)
    return instance


def add_permissions(cargo, codes):
    for code in codes:
        func = Funcao.query.filter_by(codigo=code).first()
        if func and func not in cargo.permissoes:
            cargo.permissoes.append(func)


def run():
    seed_funcoes.run()
    with app.app_context():
        print("Populando dados de exemplo...")

        inst1 = get_or_create(Instituicao, nome="Instituição 1", descricao="Inst 1")
        inst2 = get_or_create(Instituicao, nome="Instituição 2", descricao="Inst 2")

        est1 = get_or_create(Estabelecimento, codigo="EST1", nome_fantasia="Estabelecimento 1", instituicao=inst1)
        est2 = get_or_create(Estabelecimento, codigo="EST2", nome_fantasia="Estabelecimento 2", instituicao=inst2)

        setor1 = get_or_create(Setor, nome="Setor 1", estabelecimento=est1)
        setor2 = get_or_create(Setor, nome="Setor 2", estabelecimento=est1)
        setor1_e2 = get_or_create(Setor, nome="Setor 1 Estab 2", estabelecimento=est2)
        setor2_e2 = get_or_create(Setor, nome="Setor 2 Estab 2", estabelecimento=est2)

        cel1 = get_or_create(Celula, nome="Celula 1", estabelecimento=est1, setor=setor1)
        cel2 = get_or_create(Celula, nome="Celula 2", estabelecimento=est1, setor=setor1)
        cel3 = get_or_create(Celula, nome="CelulaEstab2 1", estabelecimento=est2, setor=setor2_e2)
        cel4 = get_or_create(Celula, nome="CelulaEstab2 2", estabelecimento=est2, setor=setor2_e2)

        cargos = [
            ("Analista Celula 1 JR", [setor1], [cel1], ["artigo_criar"]),
            ("Analista Celula 1 SR", [setor1], [cel1], [
                "artigo_criar",
                Permissao.ARTIGO_APROVAR_CELULA.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_CELULA.value,
                Permissao.ARTIGO_REVISAR_CELULA.value,
                Permissao.ARTIGO_EDITAR_CELULA.value,
            ]),
            ("Analista Celula 2 JR", [setor2], [cel2], ["artigo_criar"]),
            ("Analista Celula 2 SR", [setor2], [cel2], [
                "artigo_criar",
                Permissao.ARTIGO_APROVAR_CELULA.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_CELULA.value,
                Permissao.ARTIGO_REVISAR_CELULA.value,
                Permissao.ARTIGO_EDITAR_CELULA.value,
            ]),
            ("Gestor Setor 1", [setor1], [], [
                Permissao.ARTIGO_APROVAR_SETOR.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_SETOR.value,
                Permissao.ARTIGO_REVISAR_SETOR.value,
                Permissao.ARTIGO_EDITAR_SETOR.value,
            ]),
            ("Gestor Setor 2", [setor2], [], [
                Permissao.ARTIGO_APROVAR_SETOR.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_SETOR.value,
                Permissao.ARTIGO_REVISAR_SETOR.value,
                Permissao.ARTIGO_EDITAR_SETOR.value,
            ]),
            ("Gestor Setor 1 Estab 2", [setor1_e2], [], [
                Permissao.ARTIGO_APROVAR_SETOR.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_SETOR.value,
                Permissao.ARTIGO_REVISAR_SETOR.value,
                Permissao.ARTIGO_EDITAR_SETOR.value,
            ]),
        ]

        cargo_objs = {}
        for nome, setores, celulas, perms in cargos:
            cargo = Cargo.query.filter_by(nome=nome).first()
            if not cargo:
                cargo = Cargo(nome=nome, ativo=True)
                db.session.add(cargo)
            for s in setores:
                if s not in cargo.default_setores:
                    cargo.default_setores.append(s)
            for c in celulas:
                if c not in cargo.default_celulas:
                    cargo.default_celulas.append(c)
            add_permissions(cargo, perms)
            cargo_objs[nome] = cargo

        users = [
            ("analista1jr", "Analista Celula 1 JR", cel1),
            ("analista1sr", "Analista Celula 1 SR", cel1),
            ("analista2jr", "Analista Celula 2 JR", cel2),
            ("analista2sr", "Analista Celula 2 SR", cel2),
            ("gestor1", "Gestor Setor 1", cel1),
            ("gestor2", "Gestor Setor 2", cel2),
            ("gestor1e2", "Gestor Setor 1 Estab 2", cel3),
        ]

        for username, cargo_nome, cel in users:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=f"{username}@example.com",
                    password_hash=generate_password_hash("Senha123!"),
                    estabelecimento_id=cel.estabelecimento_id,
                    setor_id=cel.setor_id,
                    celula_id=cel.id,
                    cargo=cargo_objs[cargo_nome],
                )
                db.session.add(user)

        db.session.commit()
        print("Seed completo concluído.")


if __name__ == "__main__":
    run()
