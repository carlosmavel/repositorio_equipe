"""Porta de armazenamento para assets e previews de diagramas."""

from pathlib import Path
import hashlib
from io import BytesIO
import os
from uuid import uuid4

from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename


PREVIEW_MIME_TYPES = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/webp': 'WEBP'}
MAX_PREVIEW_BYTES = 5 * 1024 * 1024
MAX_PREVIEW_WIDTH = 4096
MAX_PREVIEW_HEIGHT = 4096
MAX_PREVIEW_PIXELS = 16_000_000


class InvalidDiagramPreview(ValueError):
    """Preview inválido, com mensagem segura para retornar ao cliente."""


def sanitize_preview(upload, *, max_bytes=MAX_PREVIEW_BYTES):
    """Valida e recodifica uma imagem, descartando metadados e bytes anexados.

    O formato detectado pelo Pillow (assinatura real) deve coincidir com o MIME
    declarado. A imagem devolvida é sempre um PNG novo, sem o payload original.
    """
    declared_type = str(getattr(upload, 'mimetype', '') or '').lower().split(';', 1)[0]
    if declared_type not in PREVIEW_MIME_TYPES:
        raise InvalidDiagramPreview('O preview deve ser PNG, JPEG ou WebP.')
    content = upload.read() if hasattr(upload, 'read') else bytes(upload)
    if not content or len(content) > max_bytes:
        raise InvalidDiagramPreview('Preview vazio ou maior que o limite permitido.')
    try:
        with Image.open(BytesIO(content)) as source:
            source.verify()
        with Image.open(BytesIO(content)) as source:
            width, height = source.size
            if (width < 1 or height < 1 or width > MAX_PREVIEW_WIDTH or
                    height > MAX_PREVIEW_HEIGHT or width * height > MAX_PREVIEW_PIXELS):
                raise InvalidDiagramPreview('Dimensões do preview fora do limite permitido.')
            if source.format != PREVIEW_MIME_TYPES[declared_type]:
                raise InvalidDiagramPreview('O conteúdo do preview não corresponde ao MIME declarado.')
            source.load()
            # RGB/RGBA also drops ICC/EXIF and unsupported ancillary data.
            clean = source.convert('RGBA' if 'A' in source.getbands() else 'RGB')
            output = BytesIO()
            clean.save(output, format='PNG', optimize=True)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        if isinstance(error, InvalidDiagramPreview):
            raise
        raise InvalidDiagramPreview('O preview não contém uma imagem válida.') from error
    result = output.getvalue()
    if len(result) > max_bytes:
        raise InvalidDiagramPreview('Preview processado maior que o limite permitido.')
    return result, 'image/png', width, height


class LocalDiagramStorage:
    def __init__(self, root=None):
        configured = root or current_app.config.get('DIAGRAM_STORAGE_FOLDER')
        self.root = Path(configured or Path(current_app.instance_path) / 'diagrams')

    def put(self, diagram_id, content, filename, *, kind='asset'):
        suffix = Path(secure_filename(filename or '')).suffix
        key = f'{diagram_id}/{kind}/{uuid4().hex}{suffix}'
        destination = self.root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return key

    def put_sha256(self, content):
        """Grava um blob uma única vez sob uma chave derivada de seu conteúdo."""
        digest = hashlib.sha256(content).hexdigest()
        key = f'assets/sha256/{digest[:2]}/{digest}'
        destination = self.root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_name(f'.{digest}.{uuid4().hex}.tmp')
            temporary.write_bytes(content)
            try:
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
        return key

    def read(self, key):
        return (self.root / key).read_bytes()

    def delete(self, key):
        path = self.root / key
        if path.exists():
            path.unlink()


def get_storage():
    factory = current_app.config.get('DIAGRAM_STORAGE_FACTORY')
    return factory() if factory else LocalDiagramStorage()
