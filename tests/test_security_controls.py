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


def test_login_avatar_requires_signed_cookie(app_ctx):
    with app.app_context():
        from core.models import Instituicao, Estabelecimento, Setor, Celula

        inst = Instituicao(codigo="INST2", nome="Inst2")
        est = Estabelecimento(codigo="E2", nome_fantasia="Estab2", instituicao=inst)
        setor = Setor(nome="Setor2", estabelecimento=est)
        celula = Celula(nome="Cel2", estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, celula])
        db.session.flush()

        user = User(
            username="avatar_user",
            email="avatar@example.com",
            estabelecimento=est,
            setor=setor,
            celula=celula,
            foto="avatar_login.jpg",
        )
        user.set_password("Secret1!")
        db.session.add(user)
        db.session.commit()

    folder = app.config["PROFILE_PICS_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "avatar_login.jpg"), "wb") as f:
        f.write(b"avatar-bytes")

    client = app.test_client()
    resp_without_cookie = client.get("/login-avatar")
    assert resp_without_cookie.status_code == 404

    client.post("/login", data={"username": "avatar_user", "password": "Secret1!"})
    resp_with_cookie = client.get("/login-avatar")
    assert resp_with_cookie.status_code == 200
    assert resp_with_cookie.data == b"avatar-bytes"


def test_logout_clears_login_avatar_cookie(app_ctx):
    with app.app_context():
        from core.models import Instituicao, Estabelecimento, Setor, Celula

        inst = Instituicao(codigo="INST3", nome="Inst3")
        est = Estabelecimento(codigo="E3", nome_fantasia="Estab3", instituicao=inst)
        setor = Setor(nome="Setor3", estabelecimento=est)
        celula = Celula(nome="Cel3", estabelecimento=est, setor=setor)
        db.session.add_all([inst, est, setor, celula])
        db.session.flush()

        user = User(
            username="logout_avatar",
            email="logout_avatar@example.com",
            estabelecimento=est,
            setor=setor,
            celula=celula,
            foto="logout_avatar.jpg",
        )
        user.set_password("Secret1!")
        db.session.add(user)
        db.session.commit()

    folder = app.config["PROFILE_PICS_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "logout_avatar.jpg"), "wb") as f:
        f.write(b"logout-avatar")

    client = app.test_client()
    client.post("/login", data={"username": "logout_avatar", "password": "Secret1!"})
    assert client.get("/login-avatar").status_code == 200

    client.get("/logout")
    assert client.get("/login-avatar").status_code == 404


def test_secure_cookie_flags_present(app_ctx):
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_send_email_without_smtp_credentials_raises(monkeypatch):
    monkeypatch.setenv("MAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    local_app = app
    with local_app.app_context():
        with pytest.raises(RuntimeError):
            send_email("to@example.com", "Subject", "<p>Body</p>")
