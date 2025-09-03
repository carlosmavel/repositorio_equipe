import os
import sys

# Garante que o diretório raiz do projeto esteja no PYTHONPATH quando executado diretamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

from sqlalchemy import Text, func

from app import app

try:
    from . import seed_funcoes
except ImportError:  # pragma: no cover - fallback para execução direta
    import seed_funcoes


id_counters = {}


def get_or_create(model, defaults=None, **kwargs):
    """Fetches an existing row matching ``kwargs`` or creates one.

    Columns of type ``Text`` are excluded from the lookup to avoid Oracle
    ``CLOB`` comparison errors. Any excluded fields are instead applied only
    when creating a new instance.


    When creating a new row, a manual incremental ``id`` is assigned for
    databases (like Oracle) that don't auto-generate integer primary keys.

    """

    params = defaults.copy() if defaults else {}
    filter_kwargs = {}
    for key, value in kwargs.items():
        column = model.__table__.columns.get(key)
        if column is not None and isinstance(column.type, Text):
            params[key] = value
        else:
            filter_kwargs[key] = value

    instance = model.query.filter_by(**filter_kwargs).first()
    if not instance:
        params.update(filter_kwargs)
        instance = model(**params)

        if hasattr(model, "id") and getattr(instance, "id", None) is None:
            current = id_counters.get(model)
            if current is None:
                current = db.session.query(func.max(model.id)).scalar() or 0
            current += 1
            id_counters[model] = current
            instance.id = current

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
