import os
import sys

# Ensure project root is in sys.path for module imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test_secret')
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'


# Stub external OCR dependencies when not available
import types
if 'pdf2image' not in sys.modules:
    pdf2image = types.ModuleType('pdf2image')
    pdf2image.convert_from_path = lambda path: []
    sys.modules['pdf2image'] = pdf2image

if 'paddleocr' not in sys.modules:
    paddleocr = types.ModuleType('paddleocr')

    class DummyOCR:
        def __init__(self, *args, **kwargs):
            pass

        def ocr(self, img, cls=False):
            return []

    paddleocr.PaddleOCR = DummyOCR
    sys.modules['paddleocr'] = paddleocr

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
