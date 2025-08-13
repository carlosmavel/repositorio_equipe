# utils.py

import bleach
from bleach.css_sanitizer import CSSSanitizer
import re

import os
import json
from docx import Document
import openpyxl
import xlrd
from odf import opendocument
from odf.text import P
import logging
import time
try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover
    cv2 = None
    np = None
try:
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover
    convert_from_path = None
try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None
try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None
try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    try:
        from PyPDF2 import PdfReader  # type: ignore
    except Exception:  # pragma: no cover
        PdfReader = None

try:
    from .database import db  # type: ignore  # pragma: no cover
    from .models import OrdemServico  # type: ignore  # pragma: no cover
except ImportError:  # pragma: no cover
    from core.database import db  # type: ignore
    from core.models import OrdemServico  # type: ignore

from sqlalchemy import select

logger = logging.getLogger(__name__)


def _load_ocr_settings() -> dict:
    """Load OCR settings from a JSON file if present."""
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_settings = _load_ocr_settings()
DEFAULT_OCR_LANG = os.getenv("OCR_LANG") or _settings.get("OCR_LANG", "por+eng")
_psms_raw = os.getenv("OCR_PSMS") or _settings.get("OCR_PSMS")
if isinstance(_psms_raw, str):
    try:
        DEFAULT_OCR_PSMS = [int(p.strip()) for p in _psms_raw.split(",") if p.strip()]
    except ValueError:
        DEFAULT_OCR_PSMS = [6, 3]
elif isinstance(_psms_raw, list):
    DEFAULT_OCR_PSMS = [int(p) for p in _psms_raw]
else:
    DEFAULT_OCR_PSMS = [6, 3]






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
def extract_text(
    path: str, lang: str | None = None, psms: list[int] | None = None
) -> tuple[str, list[dict]]:
    """
    Extrai texto de vários formatos de arquivo:
    - .txt, .docx, .xlsx, .xls, .ods, .pdf
    Retorna todo o texto concatenado e metadados (se houver).
    """
    ext = os.path.splitext(path)[1].lower()
    text_parts: list[str] = []

    # TXT
    if ext == '.txt':
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(), []

    # DOCX
    if ext == '.docx':
        doc = Document(path)
        for para in doc.paragraphs:
            text_parts.append(para.text)
        return '\n'.join(text_parts), []

    # XLSX
    if ext == '.xlsx':
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if cell is not None:
                        text_parts.append(str(cell))
        return '\n'.join(text_parts), []

    # XLS (Excel antigo)
    if ext == '.xls':
        wb = xlrd.open_workbook(path)
        for sheet in wb.sheets():
            for rx in range(sheet.nrows):
                for cx in range(sheet.ncols):
                    cell = sheet.cell(rx, cx).value
                    if cell:
                        text_parts.append(str(cell))
        return '\n'.join(text_parts), []

    # ODS (LibreOffice Calc)
    if ext == '.ods':
        doc = opendocument.load(path)
        for elem in doc.getElementsByType(P):
            text_parts.append(str(elem))
        return '\n'.join(text_parts), []

    # PDF (texto ou imagem)
    if ext == '.pdf':
        return extract_text_from_pdf(path, lang=lang, psms=psms)

    # outros formatos não suportados
    return '', []


def detect_and_rotate(image):
    """Detecta a orientação da imagem e a rotaciona conforme necessário.

    Retorna a imagem possivelmente rotacionada e o ângulo detectado em graus.
    """
    if not pytesseract:  # pragma: no cover - dependencias ausentes
        return image, 0
    try:
        osd = pytesseract.image_to_osd(image)
        match = re.search(r"Rotate: (\d+)", osd)
        angle = int(match.group(1)) if match else 0
        if angle != 0 and Image:
            # PIL.rotate gira no sentido anti-horário; usamos negativo
            return image.rotate(-angle, expand=True), angle
    except Exception:  # pragma: no cover - falha na detecção
        pass
    return image, 0


def preprocess_image(img, debug_dir=None, page_idx=0):
    """Aplica etapas de pre-processamento utilizando OpenCV."""
    if not (cv2 and np):  # pragma: no cover - dependencias ausentes
        return img

    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_idx}_gray.png"), gray)

    sharp = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 1.0), -0.5, 0)
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_idx}_sharp.png"), sharp)

    _, binary = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_idx}_binary.png"), binary)

    return Image.fromarray(binary)


def select_best_psm(image, lang: str, psms: list[int]):
    """Seleciona o melhor *Page Segmentation Mode* (PSM) para a imagem.

    Para cada PSM candidato executa ``pytesseract.image_to_data`` coletando a
    confiança média (ignorando valores ``-1``) e a quantidade de palavras
    reconhecidas. Retorna o PSM com maior média de confiança e, em caso de
    empate, o com maior contagem de palavras, junto com as estatísticas
    calculadas para cada PSM.
    """

    if not pytesseract:  # pragma: no cover - dependencias ausentes
        return (psms[0] if psms else 6, [])

    stats: list[tuple[int, float, int]] = []
    best_psm = psms[0]
    best_mean = -1.0
    best_words = -1

    for psm in psms:
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=f"--oem 3 --psm {psm}",
            output_type=pytesseract.Output.DICT,
        )
        confs = [int(c) for c in data.get("conf", []) if c != "-1"]
        mean_conf = sum(confs) / len(confs) if confs else 0.0
        words = [w for w in data.get("text", []) if w.strip()]
        word_count = len(words)
        stats.append((psm, mean_conf, word_count))
        if mean_conf > best_mean or (
            mean_conf == best_mean and word_count > best_words
        ):
            best_psm = psm
            best_mean = mean_conf
            best_words = word_count

    return best_psm, stats


def extract_text_from_image(
    image, lang: str | None = None, psms: list[int] | None = None
):
    """Realiza OCR na imagem usando pytesseract.

    Retorna o texto reconhecido e metadados sobre o processo, incluindo o PSM
    selecionado e as estatísticas de cada PSM candidato.
    """
    if not pytesseract:  # pragma: no cover - dependencias ausentes
        return "", {"best_psm": None, "candidates": [], "angle": None, "processing_time": 0.0}

    start_time = time.perf_counter()
    rotated, angle = detect_and_rotate(image)
    lang = lang or DEFAULT_OCR_LANG
    psms = psms or DEFAULT_OCR_PSMS
    best_psm, stats = select_best_psm(rotated, lang, psms)
    text = pytesseract.image_to_string(
        rotated, lang=lang, config=f"--oem 3 --psm {best_psm}"
    )
    text = text.replace('\x0c', '').strip()
    processing_time = time.perf_counter() - start_time
    metadata = {
        "best_psm": best_psm,
        "candidates": stats,
        "angle": angle,
        "processing_time": processing_time,
    }
    return text, metadata


def extract_text_from_pdf(
    path: str, lang: str | None = None, psms: list[int] | None = None
) -> tuple[str, list[dict]]:
    """Extrai texto de PDFs.

    Primeiro tenta usar o texto embutido com ``pypdf``/``PyPDF2``. Se não houver
    esse texto ou a biblioteca não estiver disponível, recorre ao OCR usando
    ``pdf2image`` + ``pytesseract``.
    """
    lang = lang or DEFAULT_OCR_LANG
    psms = psms or DEFAULT_OCR_PSMS
    text_parts: list[str] = []
    metadata: list[dict] = []

    reader = None
    if PdfReader is not None:
        try:
            reader = PdfReader(path)
        except Exception as e:  # pragma: no cover - falha no parse
            logger.error("Erro ao extrair texto do PDF %s: %s", path, e)

    images: list[Image.Image] | None = None
    debug_dir = os.path.splitext(path)[0] + "_ocr_debug"

    if reader is not None:
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                text_parts.append(text)
                metadata.append(
                    {
                        "page": page_number,
                        "best_psm": None,
                        "mean_conf": None,
                        "word_count": None,
                    }
                )
                continue
            if not (convert_from_path and Image and pytesseract):
                logger.warning(
                    "Dependencias de OCR indisponiveis para a pagina %s de %s",
                    page_number,
                    path,
                )
                text_parts.append("")
                metadata.append(
                    {
                        "page": page_number,
                        "best_psm": None,
                        "mean_conf": None,
                        "word_count": None,
                    }
                )
                continue
            if images is None:
                try:
                    images = convert_from_path(path, dpi=300)
                    os.makedirs(debug_dir, exist_ok=True)
                except Exception as e:  # pragma: no cover - erro ao converter
                    logger.error("Erro ao converter PDF %s: %s", path, e)
                    return "\n".join(text_parts), metadata
            img = images[page_number - 1]
            try:
                pre = preprocess_image(img, debug_dir=debug_dir, page_idx=page_number)
                best_psm, stats = select_best_psm(pre, lang, psms)
                text = pytesseract.image_to_string(
                    pre, lang=lang, config=f"--oem 3 --psm {best_psm}"
                )
                text = text.replace('\x0c', '').strip()
                text_parts.append(text)
                mean_conf, word_count = next(
                    ((m, w) for p, m, w in stats if p == best_psm),
                    (0.0, 0),
                )
                metadata.append(
                    {
                        "page": page_number,
                        "best_psm": best_psm,
                        "mean_conf": mean_conf,
                        "word_count": word_count,
                    }
                )
                logger.info("Pagina %s processada via OCR", page_number)
            except Exception as e:  # pragma: no cover
                logger.error(
                    "Erro no OCR da pagina %s do PDF %s: %s", page_number, path, e
                )
                text_parts.append("")
                metadata.append(
                    {
                        "page": page_number,
                        "best_psm": None,
                        "mean_conf": None,
                        "word_count": None,
                    }
                )
        return "\n".join(text_parts), metadata

    # Se nao foi possivel ler com PdfReader, tenta OCR em todas as paginas
    if not (convert_from_path and Image and pytesseract):
        logger.warning("pdf2image, PIL ou pytesseract indisponivel para %s", path)
        return "", []
    try:
        images = convert_from_path(path, dpi=300)
    except Exception as e:  # pragma: no cover - erro ao converter
        logger.error("Erro ao converter PDF %s: %s", path, e)
        return "", []
    os.makedirs(debug_dir, exist_ok=True)
    for i, img in enumerate(images, start=1):
        try:
            pre = preprocess_image(img, debug_dir=debug_dir, page_idx=i)
            best_psm, stats = select_best_psm(pre, lang, psms)
            text = pytesseract.image_to_string(
                pre, lang=lang, config=f"--oem 3 --psm {best_psm}"
            )
            text = text.replace('\x0c', '').strip()
            text_parts.append(text)
            mean_conf, word_count = next(
                ((m, w) for p, m, w in stats if p == best_psm),
                (0.0, 0),
            )
            metadata.append(
                {
                    "page": i,
                    "best_psm": best_psm,
                    "mean_conf": mean_conf,
                    "word_count": word_count,
                }
            )
            logger.info("Pagina %s processada com sucesso", i)
        except Exception as e:  # pragma: no cover
            logger.error("Erro no OCR da pagina %s do PDF %s: %s", i, path, e)
            metadata.append(
                {
                    "page": i,
                    "best_psm": None,
                    "mean_conf": None,
                    "word_count": None,
                }
            )
    return "\n".join(text_parts), metadata

import secrets
import string

DEFAULT_NEW_USER_PASSWORD = 'Mudanca123!'


def gerar_codigo_os() -> str:
    """Gera um código sequencial para Ordem de Serviço.

    O código possui um prefixo alfabético seguido de seis dígitos. Exemplo:
    ``A000001``. Quando o número atinge ``999999`` o prefixo é avançado para a
    próxima letra. A consulta utiliza ``SELECT ... FOR UPDATE`` para evitar
    condições de corrida; portanto, é esperado que esta função seja chamada
    dentro de uma transação ativa.
    """

    stmt = (
        select(OrdemServico.codigo)
        .order_by(OrdemServico.codigo.desc())
        .limit(1)
        .with_for_update()
    )
    ultimo_codigo = db.session.execute(stmt).scalar()

    if ultimo_codigo:
        prefixo = ultimo_codigo[0]
        numero = int(ultimo_codigo[1:]) + 1
        if numero > 999999:
            prefixo = chr(ord(prefixo) + 1)
            numero = 1
    else:
        prefixo, numero = 'A', 1

    if ord(prefixo) > ord('Z'):
        raise ValueError('Limite de códigos atingido')

    codigo = f"{prefixo}{numero:06d}"

    # Garantia adicional de unicidade
    while db.session.execute(
        select(OrdemServico.id).filter_by(codigo=codigo)
    ).scalar():
        numero += 1
        if numero > 999999:
            prefixo = chr(ord(prefixo) + 1)
            numero = 1
            if ord(prefixo) > ord('Z'):
                raise ValueError('Limite de códigos atingido')
        codigo = f"{prefixo}{numero:06d}"

    return codigo


def password_meets_requirements(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def generate_random_password(length=12):
    """Gera uma senha aleatória com letras, números e caracteres especiais."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

try:
    from .enums import Permissao  # type: ignore  # pragma: no cover
except ImportError:  # pragma: no cover - fallback for direct execution
    from core.enums import Permissao

def generate_token(user_id: int, action: str, expires_sec: int = 3600) -> str:
    """Gera um token seguro para ações como reset ou criação de senha."""
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps({'user_id': user_id, 'action': action})

def confirm_token(token: str, expiration: int = 3600):
    """Valida e decodifica o token, retornando o payload ou None."""
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        return serializer.loads(token, max_age=expiration)
    except Exception:
        return None

def send_email(to_email: str, subject: str, html_content: str) -> None:
    """Envia um e-mail utilizando o serviço SendGrid se configurado."""
    api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('EMAIL_FROM', 'no-reply@example.com')
    if not api_key:
        current_app.logger.warning('SendGrid API key não configurada.')
        return
    try:
        sg = SendGridAPIClient(api_key)
        message = Mail(from_email=from_email, to_emails=to_email,
                        subject=subject, html_content=html_content)
        sg.send(message)
    except Exception as e:
        current_app.logger.error(f'Erro ao enviar e-mail: {e}')


def user_can_edit_article(user, article):
    """Verifica se o usuário pode editar determinado artigo."""
    try:
        from .models import Article  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - fallback for direct execution
        from core.models import Article

    if not isinstance(article, Article):
        return False

    if user.has_permissao("admin") or user.id == article.user_id:
        return True

    if user.has_permissao(Permissao.ARTIGO_EDITAR_TODAS.value):
        return True

    if user.has_permissao(Permissao.ARTIGO_EDITAR_INSTITUICAO.value):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.instituicao_id == user_est.instituicao_id:
            return True

    if user.has_permissao(Permissao.ARTIGO_EDITAR_ESTABELECIMENTO.value):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.estabelecimento_id == user_est.id:
            return True

    if user.has_permissao(Permissao.ARTIGO_EDITAR_SETOR.value):
        if article.setor_id == user.setor_id:
            return True
        if user.extra_setores.filter_by(id=article.setor_id).count():
            return True

    if user.has_permissao(Permissao.ARTIGO_EDITAR_CELULA.value):
        if article.celula_id == user.celula_id:
            return True
        if user.extra_celulas.filter_by(id=article.celula_id).count():
            return True

    return False


def user_can_approve_article(user, article):
    """Verifica se o usuário pode aprovar determinado artigo."""
    try:
        from .models import Article  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - fallback for direct execution
        from core.models import Article

    if not isinstance(article, Article):
        return False

    if user.has_permissao("admin") or user.has_permissao(Permissao.ARTIGO_APROVAR_TODAS.value):
        return True

    if user.has_permissao(Permissao.ARTIGO_APROVAR_INSTITUICAO.value):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.instituicao_id == user_est.instituicao_id:
            return True

    if user.has_permissao(Permissao.ARTIGO_APROVAR_ESTABELECIMENTO.value):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.estabelecimento_id == user_est.id:
            return True

    if user.has_permissao(Permissao.ARTIGO_APROVAR_SETOR.value):
        if article.setor_id == user.setor_id:
            return True
        if user.extra_setores.filter_by(id=article.setor_id).count():
            return True

    if user.has_permissao(Permissao.ARTIGO_APROVAR_CELULA.value):
        if article.celula_id == user.celula_id:
            return True
        if user.extra_celulas.filter_by(id=article.celula_id).count():
            return True

    return False


def user_can_review_article(user, article):
    """Verifica se o usuário pode revisar determinado artigo."""
    try:
        from .models import Article  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - fallback for direct execution
        from core.models import Article

    if not isinstance(article, Article):
        return False

    if user.has_permissao("admin") or user.has_permissao(Permissao.ARTIGO_REVISAR_TODAS.value):
        return True

    if user.has_permissao(Permissao.ARTIGO_REVISAR_INSTITUICAO.value):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.instituicao_id == user_est.instituicao_id:
            return True

    if user.has_permissao(Permissao.ARTIGO_REVISAR_ESTABELECIMENTO.value):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.estabelecimento_id == user_est.id:
            return True

    if user.has_permissao(Permissao.ARTIGO_REVISAR_SETOR.value):
        if article.setor_id == user.setor_id:
            return True
        if user.extra_setores.filter_by(id=article.setor_id).count():
            return True

    if user.has_permissao(Permissao.ARTIGO_REVISAR_CELULA.value):
        if article.celula_id == user.celula_id:
            return True
        if user.extra_celulas.filter_by(id=article.celula_id).count():
            return True

    return False

def user_can_view_article(user, article):
    """Verifica se o usuário tem permissão para visualizar o artigo."""
    try:
        from .models import Article  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - fallback for direct execution
        from core.models import Article
    try:
        from .enums import ArticleVisibility
    except ImportError:  # pragma: no cover - fallback for direct execution
        from core.enums import ArticleVisibility

    if not isinstance(article, Article):
        return False

    if user_can_edit_article(user, article):
        return True

    if user.has_permissao("admin"):
        return True

    if (
        user.has_permissao(Permissao.ARTIGO_APROVAR_TODAS.value)
        or user.has_permissao(Permissao.ARTIGO_REVISAR_TODAS.value)
    ):
        return True

    if (
        user.has_permissao(Permissao.ARTIGO_APROVAR_INSTITUICAO.value)
        or user.has_permissao(Permissao.ARTIGO_REVISAR_INSTITUICAO.value)
    ):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.instituicao_id == user_est.instituicao_id:
            return True

    if (
        user.has_permissao(Permissao.ARTIGO_APROVAR_ESTABELECIMENTO.value)
        or user.has_permissao(Permissao.ARTIGO_REVISAR_ESTABELECIMENTO.value)
    ):
        user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
        if user_est and article.estabelecimento_id == user_est.id:
            return True

    if (
        user.has_permissao(Permissao.ARTIGO_APROVAR_SETOR.value)
        or user.has_permissao(Permissao.ARTIGO_REVISAR_SETOR.value)
    ):
        if article.setor_id == user.setor_id or user.extra_setores.filter_by(id=article.setor_id).count():
            return True

    if (
        user.has_permissao(Permissao.ARTIGO_APROVAR_CELULA.value)
        or user.has_permissao(Permissao.ARTIGO_REVISAR_CELULA.value)
    ):
        if article.celula_id == user.celula_id or user.extra_celulas.filter_by(id=article.celula_id).count():
            return True

    # Extras concedidos especificamente
    if article.extra_users.filter_by(id=user.id).count():
        return True
    if user.celula_id and article.extra_celulas.filter_by(id=user.celula_id).count():
        return True

    vis = article.visibility

    user_est = user.estabelecimento or (user.celula.estabelecimento if user.celula else None)
    user_setor = user.setor or (user.celula.setor if user.celula else None)

    if vis is ArticleVisibility.INSTITUICAO:
        if user_est and article.instituicao_id == user_est.instituicao_id:
            return True
    elif vis is ArticleVisibility.ESTABELECIMENTO:
        if user_est and article.estabelecimento_id == user_est.id:
            return True
    elif vis is ArticleVisibility.SETOR:
        if user_setor and article.setor_id == user_setor.id:
            return True
    elif vis is ArticleVisibility.CELULA:
        # Usa a célula explícita de visibilidade se definida; caso contrário,
        # faz fallback para a célula do autor (para artigos antigos que não
        # possuam o campo vis_celula_id preenchido)
        cel_id = article.vis_celula_id or article.celula_id
        if user.celula_id == cel_id:
            return True
        # Considera usuários atribuídos a várias células
        if cel_id and user.extra_celulas.filter_by(id=cel_id).count():
            return True

    return False


def eligible_review_notification_users(article):
    """Retorna os usuários que devem ser notificados sobre a revisão do artigo."""
    try:
        from .models import User  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - fallback for direct execution
        from core.models import User

    return [
        u for u in User.query.all()
        if user_can_approve_article(u, article) or user_can_review_article(u, article)
    ]


def user_can_access_form_builder(user):
    """Verifica se o usuário tem acesso ao criador de formulários."""
    return bool(user and getattr(user, 'pode_atender_os', False))


def validar_fluxo_ramificacoes(estrutura):
    """Valida ramificações de formulários para evitar ciclos e destinos inválidos.

    Estrutura pode ser uma string JSON ou uma lista de blocos. Retorna
    ``(True, '')`` se estiver tudo correto ou ``(False, mensagem)`` em caso de
    conflito.
    """
    if isinstance(estrutura, str):
        try:
            data = json.loads(estrutura)
        except ValueError:
            return False, "Estrutura do formulário inválida."
    else:
        data = estrutura

    perguntas = []

    def coletar(itens):
        for item in itens:
            if item.get('tipo') == 'section':
                coletar(item.get('campos', []))
            else:
                perguntas.append(item)

    coletar(data)
    id_para_indice = {str(p['id']): idx for idx, p in enumerate(perguntas)}

    for idx, pergunta in enumerate(perguntas):
        for regra in pergunta.get('ramificacoes') or []:
            destino = regra.get('destino')
            if not destino or destino in ('next', 'end'):
                continue
            if destino not in id_para_indice:
                return False, (
                    f"Não é possível criar uma ramificação para a pergunta {destino}, "
                    "pois ela está inativa ou não existe."
                )
            dest_idx = id_para_indice[destino]
            if dest_idx <= idx:
                return False, (
                    f"Não é possível criar uma ramificação que retorna à Pergunta {dest_idx + 1}, "
                    "pois isso geraria um ciclo no formulário."
                )

    return True, ''
