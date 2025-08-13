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


DEFAULT_OCR_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ocr_config.json"
)


def load_ocr_config(path: str | None = None) -> dict:
    """Carrega as configurações de OCR a partir de um arquivo JSON.

    O caminho pode ser informado manualmente ou lido da variável de ambiente
    ``OCR_CONFIG_PATH``. Quando o arquivo não é encontrado ou ocorre algum
    erro de leitura, um dicionário vazio é retornado.
    """

    if path is None:
        path = os.getenv("OCR_CONFIG_PATH", DEFAULT_OCR_CONFIG_PATH)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # pragma: no cover - arquivo inexistente ou invalido
        return {}






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
def extract_text(path: str, pdf_dpi: int | None = None) -> str:
    """
    Extrai texto de vários formatos de arquivo:
    - .txt, .docx, .xlsx, .xls, .ods, .pdf
    Retorna todo o texto concatenado como string.

    Parameters
    ----------
    path: str
        Caminho do arquivo a ser processado.
    pdf_dpi: int | None, opcional
        DPI utilizado quando ``path`` aponta para um PDF. Quando ``None``, o
        valor é obtido da variável de ambiente ``PDF_OCR_DPI`` (padrão: 300).
    """
    if pdf_dpi is None:
        pdf_dpi = int(os.getenv("PDF_OCR_DPI", "300"))

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

    # PDF (texto ou imagem)
    if ext == '.pdf':
        return extract_text_from_pdf(path, dpi=pdf_dpi)

    # outros formatos não suportados
    return ''


def preprocess_image(
    img,
    debug_dir: str | None = None,
    page_idx: int = 0,
    *,
    apply_sharpen: bool = True,
    apply_threshold: bool = True,
    brightness: int = 0,
    contrast: float = 1.0,
    denoise: str | None = None,
    denoise_ksize: int = 3,
    adaptive_threshold: bool = False,
    block_size: int = 25,
    c: int = 10,
    deskew: bool = True,
    perspective: bool = True,
):
    """Aplica etapas de pré-processamento utilizando OpenCV.

    Parameters
    ----------
    img: ``PIL.Image``
        Imagem a ser processada.
    debug_dir: str | None, opcional
        Se fornecido, salva arquivos intermediários neste diretório.
    page_idx: int, opcional
        Índice da página (usado no nome dos arquivos de depuração).
    apply_sharpen: bool, opcional
        Se ``True`` (padrão), aplica um filtro de nitidez.
    apply_threshold: bool, opcional
        Se ``True`` (padrão), aplica limiarização de Otsu para binarização.

    Returns
    -------
    ``PIL.Image``
        Imagem resultante após as transformações selecionadas.
    """
    if not (cv2 and np):  # pragma: no cover - dependencias ausentes
        return img

    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    if deskew:
        coords = np.column_stack(np.where(gray > 0))
        if coords.size:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            h, w = img_array.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            img_array = cv2.warpAffine(
                img_array,
                M,
                (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    if perspective:
        try:
            thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            contours, _ = cv2.findContours(
                thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2).astype("float32")
                    s = pts.sum(axis=1)
                    diff = np.diff(pts, axis=1)
                    rect = np.zeros((4, 2), dtype="float32")
                    rect[0] = pts[np.argmin(s)]
                    rect[2] = pts[np.argmax(s)]
                    rect[1] = pts[np.argmin(diff)]
                    rect[3] = pts[np.argmax(diff)]
                    (tl, tr, br, bl) = rect
                    widthA = np.linalg.norm(br - bl)
                    widthB = np.linalg.norm(tr - tl)
                    maxWidth = int(max(widthA, widthB))
                    heightA = np.linalg.norm(tr - br)
                    heightB = np.linalg.norm(tl - bl)
                    maxHeight = int(max(heightA, heightB))
                    dst = np.array(
                        [
                            [0, 0],
                            [maxWidth - 1, 0],
                            [maxWidth - 1, maxHeight - 1],
                            [0, maxHeight - 1],
                        ],
                        dtype="float32",
                    )
                    M = cv2.getPerspectiveTransform(rect, dst)
                    img_array = cv2.warpPerspective(
                        img_array, M, (maxWidth, maxHeight)
                    )
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        except Exception:
            pass

    processed = cv2.convertScaleAbs(gray, alpha=contrast, beta=brightness)

    if denoise == "gaussian":
        processed = cv2.GaussianBlur(
            processed, (denoise_ksize, denoise_ksize), 0
        )
    elif denoise == "median":
        processed = cv2.medianBlur(processed, denoise_ksize)

    if apply_sharpen:
        processed = cv2.addWeighted(
            processed, 1.5, cv2.GaussianBlur(processed, (0, 0), 1.0), -0.5, 0
        )

    if apply_threshold:
        if adaptive_threshold:
            processed = cv2.adaptiveThreshold(
                processed,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                c,
            )
        else:
            _, processed = cv2.threshold(
                processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

    if debug_dir:
        cv2.imwrite(os.path.join(debug_dir, f"page_{page_idx}_pre.png"), processed)

    return Image.fromarray(processed)


def split_image_into_regions(image):
    """Divide a imagem em regiões distintas com base em contornos.

    Utilizado para melhorar a acurácia do OCR em documentos que possuem
    múltiplas áreas de texto. Caso o OpenCV não esteja disponível, retorna
    apenas a imagem original.
    """

    if not (cv2 and np):  # pragma: no cover
        yield image
        return

    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    found = False
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < 100:  # ignora ruídos
            continue
        found = True
        yield image.crop((x, y, x + w, y + h))
    if not found:
        yield image

def extract_text_from_image(
    image,
    lang: str = "por",
    oem: str | None = None,
    psm: str | None = None,
    *,
    whitelist: str | None = None,
    blacklist: str | None = None,
    split_regions: bool | None = None,
    multiple_passes: list[dict] | None = None,
    config: dict | None = None,
) -> str:
    """Realiza OCR na imagem usando pytesseract.

    Parameters
    ----------
    image: PIL.Image
        Imagem já carregada na memória.
    lang: str, opcional
        Idioma para o OCR (padrão ``"por"``).
    oem: str | None, opcional
        *OEM* (OCR Engine Mode) do Tesseract. Se ``None``, utiliza ``"3"``.
    psm: str | None, opcional
        *PSM* (Page Segmentation Mode). Se ``None``, utiliza ``"6"``.
    whitelist: str | None, opcional
        Lista de caracteres permitidos pelo Tesseract.
    blacklist: str | None, opcional
        Lista de caracteres proibidos pelo Tesseract.
    split_regions: bool | None, opcional
        Se ``True``, divide a imagem em múltiplas regiões de texto.
    multiple_passes: list[dict] | None, opcional
        Lista de tentativas adicionais de OCR com parâmetros diferenciados.
    config: dict | None, opcional
        Dicionário de configuração carregado de ``ocr_config.json``.
    """

    if not pytesseract:  # pragma: no cover - dependencias ausentes
        return ""

    cfg = load_ocr_config() if config is None else config

    if oem is None:
        oem = str(cfg.get("oem", "3"))
    if psm is None:
        psm = str(cfg.get("psm", "6"))
    if whitelist is None:
        whitelist = cfg.get("whitelist")
    if blacklist is None:
        blacklist = cfg.get("blacklist")
    if split_regions is None:
        split_regions = cfg.get("split_regions", False)
    if multiple_passes is None:
        multiple_passes = cfg.get("multiple_passes")

    def _run(image, psm_value, oem_value, wl, bl):
        parts: list[str] = []
        if oem_value:
            parts.append(f"--oem {oem_value}")
        if psm_value:
            parts.append(f"--psm {psm_value}")
        if wl:
            parts.append(f"-c tessedit_char_whitelist={wl}")
        if bl:
            parts.append(f"-c tessedit_char_blacklist={bl}")
        cfg_str = " ".join(parts)
        return pytesseract.image_to_string(image, lang=lang, config=cfg_str)

    regions = list(split_image_into_regions(image)) if split_regions else [image]

    results: list[str] = []
    for region in regions:
        if multiple_passes:
            for attempt in multiple_passes:
                psm_v = attempt.get("psm", psm)
                oem_v = attempt.get("oem", oem)
                wl = attempt.get("whitelist", whitelist)
                bl = attempt.get("blacklist", blacklist)
                results.append(_run(region, psm_v, oem_v, wl, bl))
        else:
            results.append(_run(region, psm, oem, whitelist, blacklist))

    return "\n".join(filter(None, results))


def extract_text_from_pdf(
    path: str,
    dpi: int | None = None,
    *,
    apply_sharpen: bool | None = None,
    apply_threshold: bool | None = None,
    lang: str | None = None,
    oem: str | None = None,
    psm: str | None = None,
    config: dict | None = None,
) -> str:


    """Extrai texto de PDFs.

    Primeiro tenta usar o texto embutido com ``pypdf``/``PyPDF2``. Se não houver
    esse texto ou a biblioteca não estiver disponível, recorre ao OCR usando
    ``pdf2image`` + ``pytesseract``. As etapas de pré-processamento podem ser
    habilitadas ou desabilitadas conforme o tipo de documento.

    Parameters
    ----------
    path: str
        Caminho para o arquivo PDF.
    dpi: int | None, opcional
        Resolução em *dots per inch* utilizada ao converter o PDF em imagens.
        Valores mais altos tendem a melhorar a acurácia do OCR, mas aumentam o
        tempo de processamento e o consumo de memória. Quando ``None``, o valor
        é obtido da variável de ambiente ``PDF_OCR_DPI`` (padrão: 300).
    apply_sharpen: bool, opcional
        Aplica filtro de nitidez antes do OCR.
    apply_threshold: bool, opcional
        Realiza a limiarização (binarização) após o filtro de nitidez.
    lang: str, opcional
        Idioma a ser utilizado no Tesseract (padrão ``"por"``).
    oem: str | None, opcional
        ``OEM`` do Tesseract. ``None`` utiliza ``"3"``.
    psm: str | None, opcional
        ``PSM`` do Tesseract. ``None`` utiliza ``"6"``.
    """

    cfg = load_ocr_config() if config is None else config

    if dpi is None:
        dpi = int(os.getenv("PDF_OCR_DPI", "300"))

    if lang is None:
        lang = cfg.get("lang", "por")
    if oem is None:
        oem = str(cfg.get("oem", "3"))
    if psm is None:
        psm = str(cfg.get("psm", "6"))

    pre_cfg = cfg.get("preprocess", {})
    if apply_sharpen is None:
        apply_sharpen = pre_cfg.get("apply_sharpen", True)
    if apply_threshold is None:
        apply_threshold = pre_cfg.get("apply_threshold", True)

    text_parts: list[str] = []
    ocr_available = bool(convert_from_path and Image and pytesseract)
    page_errors = False

    # 1) Percorre cada pagina com PdfReader ------------------------------
    if PdfReader is not None:
        try:
            reader = PdfReader(path)
            debug_dir = os.path.splitext(path)[0] + "_ocr_debug"
            os.makedirs(debug_dir, exist_ok=True)
            for page_number, page in enumerate(getattr(reader, "pages", []), start=1):
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(text)
                elif ocr_available:
                    try:
                        try:
                            img = convert_from_path(
                                path,
                                dpi=dpi,
                                first_page=page_number,
                                last_page=page_number,
                            )[0]
                        except Exception as e:  # pragma: no cover
                            page_errors = True
                            logger.error(
                                "Erro ao converter pagina %s do PDF %s: %s",
                                page_number,
                                path,
                                e,
                            )
                            continue
                        pre = preprocess_image(
                            img,
                            debug_dir=debug_dir,
                            page_idx=page_number,
                            apply_sharpen=apply_sharpen,
                            apply_threshold=apply_threshold,
                            brightness=pre_cfg.get("brightness", 0),
                            contrast=pre_cfg.get("contrast", 1.0),
                            denoise=pre_cfg.get("denoise"),
                            denoise_ksize=pre_cfg.get("denoise_ksize", 3),
                            adaptive_threshold=pre_cfg.get("adaptive_threshold", False),
                            block_size=pre_cfg.get("block_size", 25),
                            c=pre_cfg.get("C", 10),
                            deskew=pre_cfg.get("deskew", True),
                            perspective=pre_cfg.get("perspective", True),
                        )
                        text_ocr = extract_text_from_image(
                            pre,
                            lang=lang,
                            oem=oem,
                            psm=psm,
                            whitelist=cfg.get("whitelist"),
                            blacklist=cfg.get("blacklist"),
                            split_regions=cfg.get("split_regions"),
                            multiple_passes=cfg.get("multiple_passes"),
                            config=cfg,
                        )
                        text_parts.append(text_ocr)
                        logger.info("Pagina %s processada via OCR", page_number)
                    except Exception as e:  # pragma: no cover
                        page_errors = True
                        logger.error(
                            "Erro no OCR da pagina %s do PDF %s: %s",
                            page_number,
                            path,
                            e,
                        )
                else:
                    logger.warning(
                        "Dependencias de OCR indisponiveis para a pagina %s de %s",
                        page_number,
                        path,
                    )
            if text_parts:
                return "\n".join(text_parts)
            if not page_errors:
                return ""
        except Exception as e:  # pragma: no cover - falha no parse
            page_errors = True
            logger.error("Erro ao extrair texto do PDF %s: %s", path, e)
    if not text_parts:
        if page_errors:
            logger.warning(
                "OCR por pagina falhou para %s; acionando fallback completo",
                path,
            )

        # 2) Fallback para OCR completo -------------------------------------
        if not ocr_available:
            logger.warning("pdf2image, PIL ou pytesseract indisponivel para %s", path)
            return ""

        try:
            images = convert_from_path(path, dpi=dpi)
        except Exception as e:  # pragma: no cover - erro ao converter
            logger.error("Erro ao converter PDF %s: %s", path, e)
            return ""

        debug_dir = os.path.splitext(path)[0] + "_ocr_debug"
        os.makedirs(debug_dir, exist_ok=True)

        for i, img in enumerate(images, start=1):
            try:
                pre = preprocess_image(
                    img,
                    debug_dir=debug_dir,
                    page_idx=i,
                    apply_sharpen=apply_sharpen,
                    apply_threshold=apply_threshold,
                    brightness=pre_cfg.get("brightness", 0),
                    contrast=pre_cfg.get("contrast", 1.0),
                    denoise=pre_cfg.get("denoise"),
                    denoise_ksize=pre_cfg.get("denoise_ksize", 3),
                    adaptive_threshold=pre_cfg.get("adaptive_threshold", False),
                    block_size=pre_cfg.get("block_size", 25),
                    c=pre_cfg.get("C", 10),
                    deskew=pre_cfg.get("deskew", True),
                    perspective=pre_cfg.get("perspective", True),
                )
                text = extract_text_from_image(
                    pre,
                    lang=lang,
                    oem=oem,
                    psm=psm,
                    whitelist=cfg.get("whitelist"),
                    blacklist=cfg.get("blacklist"),
                    split_regions=cfg.get("split_regions"),
                    multiple_passes=cfg.get("multiple_passes"),
                    config=cfg,
                )
                text_parts.append(text)
                logger.info("Pagina %s processada via OCR", i)
            except Exception as e:  # pragma: no cover
                logger.error("Erro no OCR da pagina %s do PDF %s: %s", i, path, e)

        return "\n".join(text_parts)

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
