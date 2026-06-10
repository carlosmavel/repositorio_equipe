from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGIN_TEMPLATE = ROOT / "templates" / "auth" / "login.html"


def test_login_template_does_not_show_forgot_password_link():
    source = LOGIN_TEMPLATE.read_text(encoding="utf-8")

    assert "Esqueci minha senha" not in source
    assert "forgot_password" not in source
