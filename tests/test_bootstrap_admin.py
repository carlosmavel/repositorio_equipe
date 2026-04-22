try:
    from seeds.bootstrap_admin import ensure_initial_admin
    from core.models import User
except ImportError:  # pragma: no cover - fallback for package execution
    from ..seeds.bootstrap_admin import ensure_initial_admin
    from ..core.models import User


def test_bootstrap_admin_is_idempotent_and_requires_password_change(app_ctx):
    first = ensure_initial_admin(
        username='admin',
        email='admin@example.com',
    )

    assert first.created is True
    assert first.generated_password
    assert first.user.deve_trocar_senha is True

    second = ensure_initial_admin(
        username='admin',
        email='admin@example.com',
    )

    assert second.created is False
    assert second.generated_password is None
    assert second.user.deve_trocar_senha is True
    assert User.query.filter_by(username='admin').count() == 1
