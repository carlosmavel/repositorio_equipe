# utils.py

import bleach
from bleach.css_sanitizer import CSSSanitizer

import os
from docx import Document
import openpyxl
import xlrd
from odf import opendocument
from odf.text import P
from PyPDF2 import PdfReader

#-------------------------------------------------------------------------------------------
# Configura o campo de texto para se comportar corretamente quando recebe tags HTML
#-------------------------------------------------------------------------------------------
def sanitize_html(text: str) -> str:
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's', 'sub', 'sup',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
        'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    allowed_attrs = {
        '*': ['class', 'style'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan']
    }
    # Configura quais propriedades CSS permitimos
    css_sanitizer = CSSSanitizer(
        allowed_css_properties=[
            'color',
            'background-color',
            'text-align',
            'width',
            'height',
            'border'
        ]
    )

    return bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
        css_sanitizer=css_sanitizer
    )

#-------------------------------------------------------------------------------------------
# Extração de texto dos anexos
#-------------------------------------------------------------------------------------------
def extract_text(path: str) -> str:
    """
    Extrai texto de vários formatos de arquivo:
    - .txt, .docx, .xlsx, .xls, .ods, .pdf
    Retorna todo o texto concatenado como string.
    """
    ext = os.path.splitext(path)[1].lower()
    text_parts = []

    # TXT
    if ext == '.txt':
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # DOCX
    if ext == '.docx':
        doc = Document(path)
        for para in doc.paragraphs:
            text_parts.append(para.text)
        return '\n'.join(text_parts)

    # XLSX
    if ext == '.xlsx':
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if cell is not None:
                        text_parts.append(str(cell))
        return '\n'.join(text_parts)

    # XLS (Excel antigo)
    if ext == '.xls':
        wb = xlrd.open_workbook(path)
        for sheet in wb.sheets():
            for rx in range(sheet.nrows):
                for cx in range(sheet.ncols):
                    cell = sheet.cell(rx, cx).value
                    if cell:
                        text_parts.append(str(cell))
        return '\n'.join(text_parts)

    # ODS (LibreOffice Calc)
    if ext == '.ods':
        doc = opendocument.load(path)
        for elem in doc.getElementsByType(P):
            text_parts.append(str(elem))
        return '\n'.join(text_parts)

    # PDF (texto)
    if ext == '.pdf':
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return '\n'.join(text_parts)
        except Exception:
            return ''

    # outros formatos não suportados
    return ''

import secrets
import string

DEFAULT_NEW_USER_PASSWORD = 'Mudanca123!'

def generate_random_password(length=12):
    """Gera uma senha aleatória com letras, números e caracteres especiais."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))
