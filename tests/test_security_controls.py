import os
import pytest

from app import app, db
from core.models import User
from core.utils import send_email


def test_login_page_hides_user_metadata(app_ctx):
    with app.app_context():
        from core.models import Instituicao, Estabelecimento, Setor, Celula

        inst = Instituicao(codigo="INST", nome="Inst")
        est = Estabelecimento(codigo="E1", nome_fantasia="Estab", instituicao=inst)
        setor = Setor(nome="Setor", estabelecimento=est)
        celula = Celula(nome="Cel", estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, celula])
        db.session.flush()

        user = User(
            username="privateuser",
            email="p@example.com",
            estabelecimento=est,
            setor=setor,
            celula=celula,
        )
        user.set_password("Secret1!")
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"privateuser" not in resp.data


def test_profile_pic_requires_auth(app_ctx, tmp_path):
    folder = app.config["PROFILE_PICS_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, "test.jpg")
    with open(file_path, "wb") as f:
        f.write(b"data")

    client = app.test_client()
    resp = client.get("/profile_pics/test.jpg")
    assert resp.status_code == 401


def test_secure_cookie_flags_present(app_ctx):
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_send_email_without_key_raises(monkeypatch):
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    local_app = app
    with local_app.app_context():
        with pytest.raises(RuntimeError):
            send_email("to@example.com", "Subject", "<p>Body</p>")
