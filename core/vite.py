"""Resolve entradas do manifest do Vite para templates Jinja."""

from __future__ import annotations

import json
from pathlib import Path

from flask import current_app, url_for


def _manifest() -> dict:
    path = Path(current_app.static_folder) / "dist" / ".vite" / "manifest.json"
    try:
        stamp = path.stat().st_mtime_ns
    except FileNotFoundError as error:
        # Testes de views não precisam compilar Node; produção falha cedo para
        # impedir que uma implantação referencie assets inexistentes.
        if current_app.testing:
            return {
                "frontend/article-editor/index.js": {"file": "test/article-editor.js"},
                "frontend/diagram-editor/index.jsx": {"file": "test/diagram-editor.js"},
                "frontend/article-diagram-viewer/index.js": {"file": "test/article-diagram-viewer.js"},
            }
        raise RuntimeError(
            "Manifest do frontend não encontrado; execute `npm run build`."
        ) from error

    cached = current_app.extensions.get("vite_manifest")
    if cached and cached[0] == stamp:
        return cached[1]
    data = json.loads(path.read_text(encoding="utf-8"))
    current_app.extensions["vite_manifest"] = (stamp, data)
    return data


def vite_asset(entry: str) -> str:
    """Retorna a URL versionada do JavaScript de uma entrada."""
    try:
        filename = _manifest()[entry]["file"]
    except KeyError as error:
        raise RuntimeError(f"Entrada ausente no manifest do Vite: {entry}") from error
    return url_for("static", filename=f"dist/{filename}")


def vite_css(entry: str) -> list[str]:
    """Retorna os CSS extraídos pertencentes somente à entrada solicitada."""
    try:
        filenames = _manifest()[entry].get("css", [])
    except KeyError as error:
        raise RuntimeError(f"Entrada ausente no manifest do Vite: {entry}") from error
    return [url_for("static", filename=f"dist/{filename}") for filename in filenames]
