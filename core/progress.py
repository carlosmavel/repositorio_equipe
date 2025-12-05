"""Pequeno utilitário para acompanhar o progresso de anexos.

Os dados são mantidos em memória apenas para feedback ao usuário durante
o ciclo de requisição. Não altera nenhuma configuração de OCR nem interfere
na lógica de extração existente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List


@dataclass
class ProgressState:
    messages: List[str] = field(default_factory=list)
    done: bool = False
    percent: float = 0.0


_progress_map: Dict[str, ProgressState] = {}
_lock = Lock()


def init_progress(progress_id: str) -> None:
    if not progress_id:
        return
    with _lock:
        _progress_map[progress_id] = ProgressState()


def add_progress_message(progress_id: str, message: str, *, percent: float | None = None) -> None:
    if not progress_id or not message:
        return
    with _lock:
        state = _progress_map.setdefault(progress_id, ProgressState())
        state.messages.append(message)
        if percent is not None:
            state.percent = max(state.percent, min(100.0, float(percent)))


def set_progress_percent(progress_id: str, percent: float) -> None:
    if not progress_id:
        return
    with _lock:
        state = _progress_map.setdefault(progress_id, ProgressState())
        state.percent = max(state.percent, min(100.0, float(percent)))


def mark_progress_done(progress_id: str) -> None:
    if not progress_id:
        return
    with _lock:
        state = _progress_map.setdefault(progress_id, ProgressState())
        state.done = True
        state.percent = 100.0


def get_progress(progress_id: str) -> ProgressState:
    with _lock:
        return _progress_map.get(progress_id, ProgressState())


def clear_progress(progress_id: str) -> None:
    if not progress_id:
        return
    with _lock:
        _progress_map.pop(progress_id, None)
