try:
    from seeds.bootstrap_admin import ensure_initial_admin
    from core.models import User, Instituicao, Estabelecimento, Setor, Celula
except ImportError:  # pragma: no cover - fallback for package execution
    from ..seeds.bootstrap_admin import ensure_initial_admin
    from ..core.models import User, Instituicao, Estabelecimento, Setor, Celula


def test_bootstrap_admin_is_idempotent_and_requires_password_change(app_ctx):
    first = ensure_initial_admin(
        username='admin',
        email='admin@example.com',
    )

    assert first.created is True
    assert first.generated_password
    assert first.user.deve_trocar_senha is True
    assert first.user.estabelecimento_id is None
    assert first.user.setor_id is None
    assert first.user.celula_id is None
    assert Instituicao.query.count() == 0
    assert Estabelecimento.query.count() == 0
    assert Setor.query.count() == 0
    assert Celula.query.count() == 0

    second = ensure_initial_admin(
        username='admin',
        email='admin@example.com',
    )

    assert second.created is False
    assert second.generated_password is None
    assert second.user.deve_trocar_senha is True
    assert second.user.estabelecimento_id is None
    assert second.user.setor_id is None
    assert second.user.celula_id is None
    assert User.query.filter_by(username='admin').count() == 1
