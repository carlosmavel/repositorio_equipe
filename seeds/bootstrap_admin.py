import secrets
import string
from dataclasses import dataclass

try:
    from core.database import db
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.database import db

try:
    from core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.models import Instituicao, Estabelecimento, Setor, Celula, Funcao, User


@dataclass
class BootstrapAdminResult:
    user: User
    created: bool
    generated_password: str | None


def _get_or_create(model, defaults=None, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    params = defaults or {}
    params.update(kwargs)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance


def _generate_secure_password(length: int = 20) -> str:
    if length < 12:
        raise ValueError("O tamanho mínimo da senha inicial é 12 caracteres.")

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        candidate = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in candidate)
            and any(char.isupper() for char in candidate)
            and any(char.isdigit() for char in candidate)
            and any(char in "!@#$%^&*()-_=+" for char in candidate)
        ):
            return candidate


def ensure_initial_admin(
    username: str = "admin",
    email: str = "admin@seudominio.com",
    initial_password: str | None = None,
    nome_completo: str = "Administrador Inicial",
) -> BootstrapAdminResult:
    """Garante usuário administrador inicial de forma idempotente."""

    admin_funcao = Funcao.query.filter_by(codigo="admin").first()
    if not admin_funcao:
        admin_funcao = Funcao(codigo="admin", nome="Administrador")
        db.session.add(admin_funcao)
        db.session.flush()

    existing_admin = User.query.filter_by(username=username).first()
    if not existing_admin:
        existing_admin = User.query.filter_by(email=email).first()

    if existing_admin:
        if admin_funcao not in existing_admin.permissoes_personalizadas:
            existing_admin.permissoes_personalizadas.append(admin_funcao)
        existing_admin.deve_trocar_senha = True
        db.session.commit()
        return BootstrapAdminResult(user=existing_admin, created=False, generated_password=None)

    instituicao = _get_or_create(
        Instituicao,
        codigo="BOOT001",
        nome="Bootstrap Instituição",
        defaults={"descricao": "Estrutura mínima para bootstrap do admin."},
    )
    estabelecimento = _get_or_create(
        Estabelecimento,
        codigo="BOOT-EST",
        nome_fantasia="Bootstrap Estabelecimento",
        defaults={"instituicao_id": instituicao.id},
    )
    setor = _get_or_create(
        Setor,
        nome="Bootstrap Setor",
        defaults={"estabelecimento_id": estabelecimento.id},
    )
    celula = _get_or_create(
        Celula,
        nome="Bootstrap Célula",
        defaults={"estabelecimento_id": estabelecimento.id, "setor_id": setor.id},
    )

    generated_password = None
    password = initial_password
    if not password:
        generated_password = _generate_secure_password()
        password = generated_password

    admin = User(
        username=username,
        email=email,
        nome_completo=nome_completo,
        estabelecimento_id=estabelecimento.id,
        setor_id=setor.id,
        celula_id=celula.id,
        deve_trocar_senha=True,
    )
    admin.set_password(password)
    admin.permissoes_personalizadas.append(admin_funcao)

    db.session.add(admin)
    db.session.commit()

    return BootstrapAdminResult(user=admin, created=True, generated_password=generated_password)
