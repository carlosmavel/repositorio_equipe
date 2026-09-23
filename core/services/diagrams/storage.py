"""Porta de armazenamento para assets e previews de diagramas."""

from pathlib import Path
import hashlib
import os
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename


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
