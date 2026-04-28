import secrets
import string
from dataclasses import dataclass

try:
    from core.database import db
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.database import db

try:
    from core.models import Funcao, User
except ImportError:  # pragma: no cover - fallback for package execution
    from ..core.models import Funcao, User

ADMIN_PERMISSION_CODES = ("admin", "artigo_excluir_definitivo")


@dataclass
class BootstrapAdminResult:
    user: User
    created: bool
    generated_password: str | None


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

    admin_funcoes = []
    for codigo in ADMIN_PERMISSION_CODES:
        funcao = Funcao.query.filter_by(codigo=codigo).first()
        if not funcao:
            nome = "Administrador" if codigo == "admin" else codigo.replace("_", " ").capitalize()
            funcao = Funcao(codigo=codigo, nome=nome)
            db.session.add(funcao)
            db.session.flush()
        admin_funcoes.append(funcao)

    existing_admin = User.query.filter_by(username=username).first()
    if not existing_admin:
        existing_admin = User.query.filter_by(email=email).first()

    if existing_admin:
        for funcao in admin_funcoes:
            if funcao not in existing_admin.permissoes_personalizadas:
                existing_admin.permissoes_personalizadas.append(funcao)
        existing_admin.deve_trocar_senha = True
        db.session.commit()
        return BootstrapAdminResult(user=existing_admin, created=False, generated_password=None)

    generated_password = None
    password = initial_password
    if not password:
        generated_password = _generate_secure_password()
        password = generated_password

    admin = User(
        username=username,
        email=email,
        nome_completo=nome_completo,
        deve_trocar_senha=True,
    )
    admin.set_password(password)
    for funcao in admin_funcoes:
        admin.permissoes_personalizadas.append(funcao)

    db.session.add(admin)
    db.session.commit()

    return BootstrapAdminResult(user=admin, created=True, generated_password=generated_password)
