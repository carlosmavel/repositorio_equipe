import os
import smtplib
from email.message import EmailMessage

from flask import current_app


def _smtp_bool(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_smtp_config() -> dict[str, object]:
    provider = os.getenv("MAIL_PROVIDER", "smtp").strip().lower()
    if provider != "smtp":
        raise RuntimeError("MAIL_PROVIDER inválido; use 'smtp'.")

    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = _smtp_bool(os.getenv("SMTP_USE_TLS", "true"))
    default_sender = os.getenv("MAIL_DEFAULT_SENDER", "orquetask.noreply@gmail.com")

    if not host:
        raise RuntimeError("SMTP_HOST ausente; envio de e-mail bloqueado.")
    if not username:
        raise RuntimeError("SMTP_USERNAME ausente; envio de e-mail bloqueado.")
    if not password:
        raise RuntimeError("SMTP_PASSWORD ausente; envio de e-mail bloqueado.")
    if not use_tls:
        raise RuntimeError("SMTP_USE_TLS deve ser verdadeiro; TLS é obrigatório.")

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "use_tls": use_tls,
        "default_sender": default_sender,
    }


def send_email(to_email: str, subject: str, html_content: str) -> None:
    """Envia e-mail via SMTP (Gmail), com TLS obrigatório."""
    config = _get_smtp_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = str(config["default_sender"])
    message["To"] = to_email
    message.set_content("Este e-mail requer cliente com suporte a HTML.")
    message.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(str(config["host"]), int(config["port"])) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(str(config["username"]), str(config["password"]))
            smtp.send_message(message)
    except Exception:
        current_app.logger.error("Erro ao enviar e-mail via SMTP.", exc_info=False)
