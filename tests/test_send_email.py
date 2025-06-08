import os
from flask import Flask
from unittest.mock import MagicMock

# Set environment variables required by send_email
os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')
os.environ['SENDGRID_API_KEY'] = 'test_key'
os.environ['EMAIL_FROM'] = 'from@example.com'

from utils import send_email


def test_send_email_constructs_and_sends_message(monkeypatch):
    app = Flask(__name__)
    with app.app_context():
        captured = {}

        class DummyMail:
            def __init__(self, from_email, to_emails, subject, html_content):
                captured['from_email'] = from_email
                captured['to_emails'] = to_emails
                captured['subject'] = subject
                captured['html_content'] = html_content

        mock_client = MagicMock()
        monkeypatch.setattr('utils.Mail', DummyMail)
        monkeypatch.setattr('utils.SendGridAPIClient', lambda key: mock_client)

        send_email('to@example.com', 'Subject', '<p>Body</p>')

        assert captured['from_email'] == 'from@example.com'
        assert captured['to_emails'] == 'to@example.com'
        assert captured['subject'] == 'Subject'
        assert captured['html_content'] == '<p>Body</p>'
        mock_client.send.assert_called_once()
