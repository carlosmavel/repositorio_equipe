try:
    from .core.database import db
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.database import db

try:
    from .core.models import (
        Instituicao,
        Estabelecimento,
        Setor,
        Celula,
        Cargo,
        Funcao,
        User,
        Article,
    )
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.models import (
        Instituicao,
        Estabelecimento,
        Setor,
        Celula,
        Cargo,
        Funcao,
        User,
        Article,
    )

try:
    from .core.enums import Permissao, ArticleVisibility, ArticleStatus
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.enums import Permissao, ArticleVisibility, ArticleStatus

from werkzeug.security import generate_password_hash
from datetime import datetime, timezone
from app import app
from . import seed_funcoes


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


def create_articles():
    """Cria artigos de exemplo para todos os usuários."""
    with app.app_context():
        print("Criando artigos de exemplo...")
        users = User.query.all()
        visibilities = list(ArticleVisibility)
        for user in users:
            if not user.celula_id:
                continue
            for vis in visibilities:
                title = f"Artigo {vis.value.title()} - {user.username}"
                exists = Article.query.filter_by(titulo=title, user_id=user.id).first()
                if exists:
                    continue
                data = {
                    "titulo": title,
                    "texto": f"Conteúdo visível por {vis.label}.",
                    "user_id": user.id,
                    "celula_id": user.celula_id,
                    "visibility": vis,
                    "status": ArticleStatus.APROVADO,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                if vis is ArticleVisibility.INSTITUICAO:
                    inst_id = getattr(user.estabelecimento, "instituicao_id", None)
                    if not inst_id:
                        continue
                    data["instituicao_id"] = inst_id
                elif vis is ArticleVisibility.ESTABELECIMENTO:
                    if not user.estabelecimento_id:
                        continue
                    data["estabelecimento_id"] = user.estabelecimento_id
                elif vis is ArticleVisibility.SETOR:
                    if not user.setor_id:
                        continue
                    data["setor_id"] = user.setor_id
                elif vis is ArticleVisibility.CELULA:
                    data["vis_celula_id"] = user.celula_id

                db.session.add(Article(**data))
        db.session.commit()
        print("🚀 Artigos de exemplo criados.")


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
        cel_s2_1 = get_or_create(Celula, nome="Celula Setor2 1", estabelecimento=est1, setor=setor2)
        cel_s2_2 = get_or_create(Celula, nome="Celula Setor2 2", estabelecimento=est1, setor=setor2)
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
            ("Analista Celula 2 JR", [setor1], [cel2], ["artigo_criar"]),
            ("Analista Celula 2 SR", [setor1], [cel2], [
                "artigo_criar",
                Permissao.ARTIGO_APROVAR_CELULA.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_CELULA.value,
                Permissao.ARTIGO_REVISAR_CELULA.value,
                Permissao.ARTIGO_EDITAR_CELULA.value,
            ]),
            ("Analista Setor2 Celula 1 JR", [setor2], [cel_s2_1], ["artigo_criar"]),
            ("Analista Setor2 Celula 1 SR", [setor2], [cel_s2_1], [
                "artigo_criar",
                Permissao.ARTIGO_APROVAR_CELULA.value,
                Permissao.ARTIGO_ASSUMIR_REVISAO_CELULA.value,
                Permissao.ARTIGO_REVISAR_CELULA.value,
                Permissao.ARTIGO_EDITAR_CELULA.value,
            ]),
            ("Analista Setor2 Celula 2 JR", [setor2], [cel_s2_2], ["artigo_criar"]),
            ("Analista Setor2 Celula 2 SR", [setor2], [cel_s2_2], [
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
            ("analistas2c1jr", "Analista Setor2 Celula 1 JR", cel_s2_1),
            ("analistas2c1sr", "Analista Setor2 Celula 1 SR", cel_s2_1),
            ("analistas2c2jr", "Analista Setor2 Celula 2 JR", cel_s2_2),
            ("analistas2c2sr", "Analista Setor2 Celula 2 SR", cel_s2_2),
            ("gestor1", "Gestor Setor 1", cel1),
            ("gestor2", "Gestor Setor 2", cel_s2_1),
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

        # Usuário administrador padrao
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@seudominio.com",
                password_hash=generate_password_hash("Senha123!"),
                nome_completo="Admin de Souza",
                matricula="ADM001",
                cpf="000.000.000-00",
                estabelecimento_id=cel1.estabelecimento_id,
                setor_id=cel1.setor_id,
                celula_id=cel1.id,
            )
            func_admin = Funcao.query.filter_by(codigo="admin").first()
            if func_admin:
                admin.permissoes_personalizadas.append(func_admin)
            db.session.add(admin)

        db.session.commit()

        create_articles()

        print("Seed completo concluído.")


if __name__ == "__main__":
    run()
