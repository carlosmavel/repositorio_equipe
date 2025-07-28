import os
import sys

# Ensure project root is in sys.path for module imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ.setdefault('SECRET_KEY', 'test_secret')
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

# Stub external OCR dependencies when not available
import types
if 'pdf2image' not in sys.modules:
    pdf2image = types.ModuleType('pdf2image')
    pdf2image.convert_from_path = lambda path: []
    sys.modules['pdf2image'] = pdf2image

if 'pytesseract' not in sys.modules:
    pytesseract = types.ModuleType('pytesseract')
    pytesseract.image_to_string = lambda img: ''
    sys.modules['pytesseract'] = pytesseract

import pytest
from app import app, db


@pytest.fixture
def app_ctx():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_ctx):
    with app_ctx.test_client() as client:
        yield client
