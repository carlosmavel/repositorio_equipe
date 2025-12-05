# utils.py

import bleach
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
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None
try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None
try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

try:
    from .database import db  # type: ignore  # pragma: no cover
    from .models import OrdemServico  # type: ignore  # pragma: no cover
except ImportError:  # pragma: no cover
    from core.database import db  # type: ignore
    from core.models import OrdemServico  # type: ignore

from sqlalchemy import select

logger = logging.getLogger(__name__)
#-------------------------------------------------------------------------------------------
# Configura o campo de texto para se comportar corretamente quando recebe tags HTML
#-------------------------------------------------------------------------------------------
def sanitize_html(text: str) -> str:
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's', 'sub', 'sup',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a'
    ]
    allowed_attrs = {
        '*': ['class'],
        'a': ['href', 'title'],
    }

    return bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
        protocols=['http', 'https', 'mailto']
    )

"""
Funções utilitárias do projeto.

Este módulo recebeu melhorias relacionadas ao pós-processamento do OCR. Toda a
extração existente permanece inalterada e os novos comportamentos são opcionais
e executados somente quando parâmetros específicos são informados.
"""

#-------------------------------------------------------------------------------------------
# Extração de texto dos anexos
#-------------------------------------------------------------------------------------------
def extract_text(path: str, **ocr_options) -> str:
    """Extrai texto de vários formatos de arquivo.

    Parâmetros adicionais são encaminhados para as rotinas de OCR quando o
    arquivo é um PDF ou imagem. O comportamento padrão permanece idêntico ao
    anterior quando nenhum parâmetro extra é fornecido.
    """
    progress_callback = ocr_options.pop("progress_callback", None)

    ext = os.path.splitext(path)[1].lower()
    text_parts: list[str] = []

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

    # PDF
    if ext == '.pdf':
        return extract_text_from_pdf(path, progress_callback=progress_callback, **ocr_options)

    # outros formatos não suportados
    return ''


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


def _reconstruct_text(data: dict, width: int) -> str:
    """Reordena blocos de texto obtidos via ``image_to_data``."""
    items = []
    for i, txt in enumerate(data.get("text", [])):
        if not txt:
            continue
        items.append(
            (
                data["page_num"][i],
                data["top"][i],
                data["left"][i],
                txt,
            )
        )

    from itertools import groupby

    pages: list[str] = []
    for page, group in groupby(items, key=lambda x: x[0]):
        group_items = list(group)
        xs = [g[2] for g in group_items]
        column_split = None
        if xs:
            mid = width / 2
            left_count = sum(1 for x in xs if x < mid)
            right_count = sum(1 for x in xs if x >= mid)
            if left_count > 0 and right_count > 0 and left_count / len(xs) > 0.2 and right_count / len(xs) > 0.2:
                column_split = mid

        if column_split:
            left_items = sorted([g for g in group_items if g[2] < column_split], key=lambda x: (x[1], x[2]))
            right_items = sorted([g for g in group_items if g[2] >= column_split], key=lambda x: (x[1], x[2]))
            ordered = left_items + right_items
        else:
            ordered = sorted(group_items, key=lambda x: (x[1], x[2]))

        current_y = None
        page_lines: list[str] = []
        for _, top, left, text in ordered:
            if current_y is None or abs(top - current_y) > 10:
                page_lines.append(text)
                current_y = top
            else:
                page_lines[-1] += " " + text
        pages.append("\n".join(page_lines).strip())

    return "\n".join(pages)


def _clean_text(text: str) -> str:
    """Remove ruídos comuns do OCR e normaliza o texto."""
    text = re.sub(r"(?<!\S)[ºª|—](?!\S)", "", text)
    text = re.sub(r"\s[?<>]\s", " ", text)
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _detect_sparse(data: dict, width: int, height: int) -> bool:
    words = [t for t in data.get("text", []) if t.strip()]
    if not words:
        return True
    areas = [data["width"][i] * data["height"][i] for i, t in enumerate(data["text"]) if t.strip()]
    density = sum(areas) / float(width * height)
    return density < 0.02 or len(words) < 20


def extract_text_from_image(
    image,
    lang: str = "por",
    *,
    reorder: bool = False,
    clean: bool = False,
    detect_sparse: bool = False,
) -> str:
    """Realiza OCR na imagem usando pytesseract com pós-processamento opcional."""
    if not pytesseract:  # pragma: no cover - dependencias ausentes
        return ""

    if reorder or detect_sparse:
        data = pytesseract.image_to_data(
            image, lang=lang, config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT
        )
        text = _reconstruct_text(data, image.width)
        if detect_sparse and _detect_sparse(data, image.width, image.height):
            aux = pytesseract.image_to_string(image, lang=lang, config="--oem 3 --psm 11")
            if aux:
                text = text + "\n" + aux.replace("\x0c", "").strip()
    else:
        text = pytesseract.image_to_string(
            image, lang=lang, config="--oem 3 --psm 6"
        )

    text = text.replace("\x0c", "").strip()
    if clean:
        text = _clean_text(text)
    return text


def extract_text_from_pdf(
    path: str,
    *,
    lang: str = "por",
    reorder: bool = False,
    clean: bool = False,
    detect_sparse: bool = False,
    progress_callback=None,
) -> str:
    """Extrai texto de PDFs pesquisáveis ou via ``pdf2image`` + ``pytesseract``.

    Primeiro tenta recuperar o conteúdo diretamente (PDF pesquisável) para
    evitar OCR desnecessário. O reordenamento, a limpeza de texto e a detecção
    de layout esparso são opcionais e aplicados apenas quando os parâmetros
    correspondentes são habilitados. Com todos os parâmetros em ``False`` o
    comportamento é idêntico ao anterior.
    """
    direct_text = _extract_pdf_text_without_ocr(path)
    if direct_text:
        return direct_text

    if not (convert_from_path and Image and pytesseract):
        logger.warning("pdf2image, PIL ou pytesseract indisponivel para %s", path)
        return ""
    try:
        images = convert_from_path(path, dpi=300)
    except Exception as e:  # pragma: no cover - erro ao converter
        logger.error("Erro ao converter PDF %s: %s", path, e)
        return ""
    text_parts: list[str] = []
    total_pages = len(images)
    for i, img in enumerate(images, start=1):
        try:
            pre = preprocess_image(img, page_idx=i)
            text_parts.append(
                extract_text_from_image(
                    pre,
                    lang=lang,
                    reorder=reorder,
                    clean=clean,
                    detect_sparse=detect_sparse,
                )
            )
            logger.info("Pagina %s processada com sucesso", i)
            if progress_callback:
                percent = (i / total_pages) * 100 if total_pages else None
                progress_callback({
                    "message": f"Página {i} processada com sucesso",
                    "percent": percent,
                })
        except Exception as e:  # pragma: no cover
            logger.error("Erro no OCR da pagina %s do PDF %s: %s", i, path, e)
            text_parts.append("")
    return "\n".join(text_parts)


def _extract_pdf_text_without_ocr(path: str, sample_pages: int = 3) -> str:
    """Tenta extrair texto de PDFs pesquisáveis antes de acionar o OCR.

    O objetivo é evitar o processamento custoso de OCR em arquivos que já
    contêm texto acessível. Caso nenhuma página amostrada possua texto ou
    ocorra qualquer erro, retorna uma string vazia para que o fluxo de OCR
    seja acionado normalmente.
    """
    if not PdfReader:  # pragma: no cover - dependencias ausentes
        return ""

    def _has_meaningful_text(text: str) -> bool:
        return len(re.sub(r"\s+", "", text)) >= 40

    try:
        reader = PdfReader(path)
    except Exception as e:  # pragma: no cover - falha ao abrir
        logger.warning("Falha ao abrir PDF %s para leitura direta: %s", path, e)
        return ""

    has_text = False
    for idx, page in enumerate(reader.pages):
        try:
            snippet = (page.extract_text() or "").strip()
        except Exception as e:  # pragma: no cover - erro específico de página
            logger.info("Erro ao ler pagina %s de %s sem OCR: %s", idx + 1, path, e)
            snippet = ""
        if _has_meaningful_text(snippet):
            has_text = True
            break
        if idx + 1 >= sample_pages:
            break

    if not has_text:
        return ""

    pages_text: list[str] = []
    for idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as e:  # pragma: no cover
            logger.info("Erro ao extrair texto da pagina %s de %s: %s", idx + 1, path, e)
            page_text = ""
        pages_text.append(page_text.strip())
    joined_text = "\n".join(pages_text).strip()
    if not _has_meaningful_text(joined_text):
        return ""

    return "\n".join(text for text in pages_text if text)

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

def _password_token_serializer():
    secret = current_app.config.get("PASSWORD_RESET_SECRET") or current_app.secret_key
    return URLSafeTimedSerializer(secret)


def generate_token(user_id: int, action: str, expires_sec: int = 3600) -> str:
    """Gera um token seguro para ações como reset ou criação de senha."""
    serializer = _password_token_serializer()
    return serializer.dumps({'user_id': user_id, 'action': action})

def confirm_token(token: str, expiration: int = 3600):
    """Valida e decodifica o token, retornando o payload ou None."""
    serializer = _password_token_serializer()
    try:
        return serializer.loads(token, max_age=expiration)
    except Exception:
        return None

def send_email(to_email: str, subject: str, html_content: str) -> None:
    """Envia um e-mail utilizando o serviço SendGrid se configurado."""
    api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('EMAIL_FROM', 'no-reply@example.com')
    if not api_key:
        current_app.logger.error('SendGrid API key não configurada.', exc_info=False)
        raise RuntimeError('SENDGRID_API_KEY ausente; envio de e-mail bloqueado.')
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

    # Nunca permitir aprovação do próprio artigo
    if user.id == getattr(article, "user_id", None):
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
        if u.id != getattr(article, "user_id", None)
        and user_can_approve_article(u, article)
    ]


def user_can_access_form_builder(user):
    """Verifica se o usuário tem acesso ao criador de formulários."""
    return bool(
        user
        and (
            getattr(user, 'pode_atender_os', False)
            or getattr(user, 'has_permissao', lambda _p: False)('admin')
        )
    )


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
