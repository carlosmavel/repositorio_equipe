import os
import sys

# Ensure project root is in sys.path for module imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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
