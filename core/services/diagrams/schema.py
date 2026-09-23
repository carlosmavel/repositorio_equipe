"""Contrato versionado para snapshots do editor Excalidraw.

O formato deste módulo é do Orquetask (e não a versão do Excalidraw).  Um
snapshot antigo, portanto, continua interpretável quando o editor for
atualizado e pode ser migrado explicitamente no futuro.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


ORQUETASK_DIAGRAM_SCHEMA_VERSION = 1
MAX_ELEMENTS = 20_000
MAX_JSON_BYTES = 10 * 1024 * 1024
MAX_FILES = 100
MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 50 * 1024 * 1024

# UI/session state must never become part of a historical snapshot.
EPHEMERAL_APP_STATE_KEYS = frozenset({
    "collaborators", "contextMenu", "cursorButton", "draggingElement",
    "editingElement", "editingGroupId", "editingLinearElement",
    "errorMessage", "isLoading", "openDialog", "openMenu", "pasteDialog",
    "previousSelectedElementIds", "resizingElement", "selectedElementIds",
    "selectedGroupIds", "selectionElement", "suggestedBindings", "toast",
    "userToFollow", "zenModeEnabled",
})


class DiagramSchemaError(ValueError):
    """Erro seguro para exposição como resposta HTTP 400."""


@dataclass(frozen=True)
class DiagramFile:
    file_id: str
    content: bytes
    content_type: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class DiagramSavePayload:
    document: dict[str, Any]
    canonical_json: str
    content_hash: str
    files: tuple[DiagramFile, ...]
    lock_version: int | None


def canonical_json(value: Any) -> str:
    """Serializa JSON de maneira determinística para hashing e auditoria."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DiagramSchemaError(f"{field} deve ser um objeto JSON.")
    return value


def validate_save_payload(data: Any, uploaded_files: Mapping[str, Any] | None = None) -> DiagramSavePayload:
    """Valida e normaliza uma carga JSON/multipart para o schema atual."""
    data = _object(data, "payload")
    version = data.get("schemaVersion")
    if version != ORQUETASK_DIAGRAM_SCHEMA_VERSION:
        raise DiagramSchemaError(
            f"schemaVersion incompatível; esperado {ORQUETASK_DIAGRAM_SCHEMA_VERSION}."
        )
    elements = data.get("elements")
    if not isinstance(elements, list):
        raise DiagramSchemaError("elements deve ser uma lista.")
    if len(elements) > MAX_ELEMENTS:
        raise DiagramSchemaError(f"elements excede o limite de {MAX_ELEMENTS} itens.")
    if any(not isinstance(element, dict) for element in elements):
        raise DiagramSchemaError("Cada item de elements deve ser um objeto.")

    app_state = _object(data.get("appState"), "appState")
    app_state = {key: value for key, value in app_state.items()
                 if key not in EPHEMERAL_APP_STATE_KEYS}
    metadata = _object(data.get("metadata", {}), "metadata")
    # Metadados técnicos têm valores JSON escalares para evitar conteúdo livre
    # duplicando a cena e contornando os limites do contrato.
    if any(not isinstance(value, (str, int, float, bool, type(None)))
           for value in metadata.values()):
        raise DiagramSchemaError("metadata aceita apenas valores escalares.")

    manifest = data.get("files", {})
    manifest = _object(manifest, "files")
    uploads = uploaded_files or {}
    if len(manifest) > MAX_FILES or len(uploads) > MAX_FILES:
        raise DiagramSchemaError(f"files excede o limite de {MAX_FILES} itens.")
    if set(manifest) != set(uploads):
        raise DiagramSchemaError("O manifesto files deve corresponder aos arquivos enviados.")

    parsed_files = []
    file_refs = {}
    total = 0
    for file_id, descriptor in manifest.items():
        if not isinstance(file_id, str) or not file_id or len(file_id) > 200:
            raise DiagramSchemaError("Identificador de arquivo inválido.")
        descriptor = _object(descriptor, f"files.{file_id}")
        upload = uploads[file_id]
        content = upload.read() if hasattr(upload, "read") else bytes(upload)
        total += len(content)
        if not content or len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_FILE_BYTES:
            raise DiagramSchemaError("Arquivo vazio ou limite de arquivos excedido.")
        content_type = str(descriptor.get("mimeType") or getattr(upload, "mimetype", "") or
                           "application/octet-stream")
        if len(content_type) > 120:
            raise DiagramSchemaError("mimeType inválido.")
        parsed = DiagramFile(file_id, content, content_type)
        parsed_files.append(parsed)
        file_refs[file_id] = {"sha256": parsed.sha256, "mimeType": content_type,
                              "size": len(content)}

    document = {
        "schemaVersion": ORQUETASK_DIAGRAM_SCHEMA_VERSION,
        "elements": elements,
        "appState": app_state,
        "files": file_refs,
        "metadata": metadata,
    }
    canonical = canonical_json(document)
    if len(canonical.encode("utf-8")) > MAX_JSON_BYTES:
        raise DiagramSchemaError(f"A cena excede o limite de {MAX_JSON_BYTES} bytes.")
    lock_version = data.get("lockVersion")
    if lock_version is not None and (isinstance(lock_version, bool) or
                                     not isinstance(lock_version, int) or lock_version < 0):
        raise DiagramSchemaError("lockVersion deve ser um inteiro não negativo.")
    return DiagramSavePayload(
        document=document, canonical_json=canonical,
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        files=tuple(parsed_files), lock_version=lock_version,
    )
