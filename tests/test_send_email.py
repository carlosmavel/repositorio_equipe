from flask import Flask

from core.utils import send_email


class DummySMTP:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged = None
        self.sent_message = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return None

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.logged = (username, password)

    def send_message(self, message):
        self.sent_message = message


def test_send_email_uses_smtp_tls_and_credentials(monkeypatch):
    monkeypatch.setenv('MAIL_PROVIDER', 'smtp')
    monkeypatch.setenv('SMTP_HOST', 'smtp.gmail.com')
    monkeypatch.setenv('SMTP_PORT', '587')
    monkeypatch.setenv('SMTP_USERNAME', 'orquetask.noreply@gmail.com')
    monkeypatch.setenv('SMTP_PASSWORD', 'app-password')
    monkeypatch.setenv('SMTP_USE_TLS', 'true')
    monkeypatch.setenv('MAIL_DEFAULT_SENDER', 'orquetask.noreply@gmail.com')

    app = Flask(__name__)
    captured = {}

    def smtp_factory(host, port):
        client = DummySMTP(host, port)
        captured['client'] = client
        return client

    monkeypatch.setattr('core.email_service.smtplib.SMTP', smtp_factory)

    with app.app_context():
        send_email('to@example.com', 'Subject', '<p>Body</p>')

    smtp_client = captured['client']
    assert smtp_client.host == 'smtp.gmail.com'
    assert smtp_client.port == 587
    assert smtp_client.started_tls is True
    assert smtp_client.logged == ('orquetask.noreply@gmail.com', 'app-password')
    assert smtp_client.sent_message['From'] == 'orquetask.noreply@gmail.com'
    assert smtp_client.sent_message['To'] == 'to@example.com'
    assert smtp_client.sent_message['Subject'] == 'Subject'
