import os
import sys

# Garante que o diretório raiz do projeto esteja no PYTHONPATH quando executado diretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database import db
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.database import db

try:
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
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.models import (
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
    from core.enums import Permissao, ArticleVisibility, ArticleStatus
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.enums import Permissao, ArticleVisibility, ArticleStatus

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
from app import app

try:
    from . import seed_funcoes
    from .bootstrap_admin import ensure_initial_admin
except ImportError:  # pragma: no cover - fallback para execução direta
    import seed_funcoes
    from bootstrap_admin import ensure_initial_admin


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

        inst1 = get_or_create(
            Instituicao,
            codigo="INST001",
            nome="Empresa 01",
            descricao="Operadora de Saúde",
        )

        est1 = get_or_create(
            Estabelecimento,
            codigo="EST1",
            nome_fantasia="Centro Administrativo",
            instituicao=inst1,
        )
        est2 = get_or_create(
            Estabelecimento,
            codigo="EST2",
            nome_fantasia="Hospital 01",
            instituicao=inst1,
        )

        setor1 = get_or_create(
            Setor, nome="Tecnologia da Informação", estabelecimento=est1
        )
        setor2 = get_or_create(Setor, nome="Regulação", estabelecimento=est1)
        setor3 = get_or_create(Setor, nome="Contas Médicas", estabelecimento=est1)
        setor1_e2 = get_or_create(Setor, nome="Faturamento", estabelecimento=est2)
        setor2_e2 = get_or_create(Setor, nome="Recepção", estabelecimento=est2)
        setor3_e2 = get_or_create(
            Setor, nome="Centro Cirúrgico", estabelecimento=est2
        )

        cel1 = get_or_create(
            Celula,
            nome="TI - Regras e Parametrizações",
            estabelecimento=est1,
            setor=setor1,
        )
        cel2 = get_or_create(
            Celula,
            nome="TI - Infraestrutura",
            estabelecimento=est1,
            setor=setor1,
        )
        cel3 = get_or_create(
            Celula,
            nome="TI - Operadora",
            estabelecimento=est1,
            setor=setor1,
        )

        cel_s2_1 = get_or_create(
            Celula,
            nome="Gestão de Redes",
            estabelecimento=est1,
            setor=setor2,
        )
        cel_s2_2 = get_or_create(
            Celula,
            nome="Gestão de Autorizações",
            estabelecimento=est1,
            setor=setor2,
        )

        cel_s3_1 = get_or_create(
            Celula,
            nome="Cobrança Intercâmbio",
            estabelecimento=est1,
            setor=setor3,
        )
        cel_s3_2 = get_or_create(
            Celula,
            nome="Contas Recursos Próprios",
            estabelecimento=est1,
            setor=setor3,
        )

        cel4 = get_or_create(
            Celula,
            nome="Faturamento Internações",
            estabelecimento=est2,
            setor=setor1_e2,
        )
        cel5 = get_or_create(
            Celula,
            nome="Faturamento Consultas",
            estabelecimento=est2,
            setor=setor1_e2,
        )
        cel6 = get_or_create(
            Celula,
            nome="Atendimento",
            estabelecimento=est2,
            setor=setor2_e2,
        )
        cel7 = get_or_create(
            Celula,
            nome="Autorizações",
            estabelecimento=est2,
            setor=setor2_e2,
        )
        cel8 = get_or_create(
            Celula,
            nome="Sala 01",
            estabelecimento=est2,
            setor=setor3_e2,
        )
        cel9 = get_or_create(
            Celula,
            nome="Sala 02",
            estabelecimento=est2,
            setor=setor3_e2,
        )

        celulas = [
            cel1,
            cel2,
            cel3,
            cel_s2_1,
            cel_s2_2,
            cel_s3_1,
            cel_s3_2,
            cel4,
            cel5,
            cel6,
            cel7,
            cel8,
            cel9,
        ]

        cargos = []
        for cel in celulas:
            cargos.append(
                (
                    f"Analista {cel.nome} JR",
                    [cel.setor],
                    [cel],
                    ["artigo_criar"],
                )
            )
            cargos.append(
                (
                    f"Analista {cel.nome} SR",
                    [cel.setor],
                    [cel],
                    [
                        "artigo_criar",
                        Permissao.ARTIGO_APROVAR_CELULA.value,
                        Permissao.ARTIGO_ASSUMIR_REVISAO_CELULA.value,
                        Permissao.ARTIGO_REVISAR_CELULA.value,
                        Permissao.ARTIGO_EDITAR_CELULA.value,
                    ],
                )
            )

        for setor in [
            setor1,
            setor2,
            setor3,
            setor1_e2,
            setor2_e2,
            setor3_e2,
        ]:
            cargos.append(
                (
                    f"Gestor {setor.nome}",
                    [setor],
                    [],
                    [
                        "artigo_criar",
                        Permissao.ARTIGO_APROVAR_SETOR.value,
                        Permissao.ARTIGO_ASSUMIR_REVISAO_SETOR.value,
                        Permissao.ARTIGO_REVISAR_SETOR.value,
                        Permissao.ARTIGO_EDITAR_SETOR.value,
                    ],
                )
            )

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
            (
                "analista_ti_regras_jr",
                f"Analista {cel1.nome} JR",
                cel1,
            ),
            (
                "analista_ti_regras_sr",
                f"Analista {cel1.nome} SR",
                cel1,
            ),
            (
                "analista_ti_infra_jr",
                f"Analista {cel2.nome} JR",
                cel2,
            ),
            (
                "analista_ti_infra_sr",
                f"Analista {cel2.nome} SR",
                cel2,
            ),
            (
                "analista_gestao_redes_jr",
                f"Analista {cel_s2_1.nome} JR",
                cel_s2_1,
            ),
            (
                "analista_gestao_redes_sr",
                f"Analista {cel_s2_1.nome} SR",
                cel_s2_1,
            ),
            (
                "analista_gestao_autorizacoes_jr",
                f"Analista {cel_s2_2.nome} JR",
                cel_s2_2,
            ),
            (
                "analista_gestao_autorizacoes_sr",
                f"Analista {cel_s2_2.nome} SR",
                cel_s2_2,
            ),
            (
                "gestor_ti",
                f"Gestor {setor1.nome}",
                cel1,
            ),
            (
                "gestor_regulacao",
                f"Gestor {setor2.nome}",
                cel_s2_1,
            ),
            (
                "gestor_faturamento",
                f"Gestor {setor1_e2.nome}",
                cel4,
            ),
        ]

        for username, cargo_nome, cel in users:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=f"{username}@example.com",
                    password_hash=generate_password_hash("Senha123!"),
                    deve_trocar_senha=True,
                    estabelecimento_id=cel.estabelecimento_id,
                    setor_id=cel.setor_id,
                    celula_id=cel.id,
                    cargo=cargo_objs[cargo_nome],
                )
                db.session.add(user)

        bootstrap_result = ensure_initial_admin(
            initial_password=os.getenv("INITIAL_ADMIN_PASSWORD"),
        )
        if bootstrap_result.created and bootstrap_result.generated_password:
            print(
                "Admin inicial criado pelo seed. "
                f"username={bootstrap_result.user.username} "
                f"senha_temporaria={bootstrap_result.generated_password}"
            )

        db.session.commit()

        create_articles()

        print("Seed completo concluído.")


if __name__ == "__main__":
    run()
