from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from mimetypes import guess_type
from pathlib import Path

from flask import current_app

try:
    from ..database import db
    from ..models import Attachment
    from ..utils import extract_text
except ImportError:  # pragma: no cover
    from core.database import db
    from core.models import Attachment
    from core.utils import extract_text

OCR_STATUS_PENDENTE = "pendente"
OCR_STATUS_PROCESSANDO = "processando"
OCR_STATUS_CONCLUIDO = "concluido"
OCR_STATUS_ERRO = "erro"
OCR_STATUS_BAIXO_APROVEITAMENTO = "baixo_aproveitamento"
OCR_STATUS_NAO_APLICAVEL = "nao_aplicavel"


@dataclass
class OCRBatchResult:
    recovered_stuck: int = 0
    processed: int = 0
    concluded: int = 0
    low_yield: int = 0
    failed: int = 0


def is_pdf_ocr_eligible(filename: str, mime_type: str | None = None) -> bool:
    guessed_mime = mime_type or guess_type(filename)[0]
    return (guessed_mime == "application/pdf") or filename.lower().endswith(".pdf")


def enqueue_attachment_for_ocr(attachment: Attachment) -> None:
    attachment.ocr_status = OCR_STATUS_PENDENTE
    attachment.ocr_requested_at = datetime.now(timezone.utc)
    attachment.ocr_started_at = None
    attachment.ocr_finished_at = None
    attachment.ocr_processed_at = None
    attachment.ocr_last_error = None
    attachment.ocr_error_message = None
    attachment.ocr_pages_failed = None
    attachment.ocr_pages_success = None
    attachment.ocr_page_count = None
    attachment.ocr_char_count = None
    attachment.ocr_processing_time_seconds = None
    attachment.ocr_confidence_score = None


def _recover_stuck_processing(stuck_timeout_minutes: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stuck_timeout_minutes)
    stuck_items = (
        Attachment.query
        .filter(Attachment.ocr_status == OCR_STATUS_PROCESSANDO)
        .filter(Attachment.ocr_started_at.isnot(None))
        .filter(Attachment.ocr_started_at < cutoff)
        .all()
    )

    for item in stuck_items:
        item.ocr_status = OCR_STATUS_PENDENTE
        item.ocr_last_error = "Reenfileirado automaticamente após timeout em processando."
    if stuck_items:
        db.session.commit()

    return len(stuck_items)


def process_pending_ocr_attachments(
    batch_size: int = 20,
    stuck_timeout_minutes: int = 30,
    low_yield_threshold: int = 80,
) -> OCRBatchResult:
    result = OCRBatchResult()
    result.recovered_stuck = _recover_stuck_processing(stuck_timeout_minutes)

    pendentes = (
        Attachment.query
        .filter(Attachment.ocr_status == OCR_STATUS_PENDENTE)
        .order_by(Attachment.ocr_requested_at.asc().nullsfirst(), Attachment.created_at.asc())
        .limit(batch_size)
        .all()
    )

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])

    for attachment in pendentes:
        result.processed += 1

        attachment.ocr_status = OCR_STATUS_PROCESSANDO
        started_at = datetime.now(timezone.utc)
        attachment.ocr_started_at = started_at
        attachment.ocr_attempts = (attachment.ocr_attempts or 0) + 1
        attachment.ocr_last_attempt_at = started_at
        db.session.commit()

        file_path = upload_folder / attachment.filename

        try:
            content = extract_text(str(file_path))
            attachment.content = content
            attachment.ocr_text = content
            finished_at = datetime.now(timezone.utc)
            attachment.ocr_finished_at = finished_at
            attachment.ocr_processed_at = finished_at
            attachment.ocr_last_error = None
            attachment.ocr_error_message = None
            attachment.ocr_char_count = len((content or "").strip())
            attachment.ocr_page_count = 1
            attachment.ocr_pages_success = 1
            attachment.ocr_pages_failed = 0
            attachment.ocr_engine = "extract_text"
            attachment.ocr_processing_time_seconds = max((finished_at - started_at).total_seconds(), 0.0)

            if len((content or "").strip()) < low_yield_threshold:
                attachment.ocr_status = OCR_STATUS_BAIXO_APROVEITAMENTO
                result.low_yield += 1
            else:
                attachment.ocr_status = OCR_STATUS_CONCLUIDO
                result.concluded += 1
        except Exception as exc:  # pragma: no cover - proteção operacional
            attachment.ocr_status = OCR_STATUS_ERRO
            finished_at = datetime.now(timezone.utc)
            attachment.ocr_finished_at = finished_at
            attachment.ocr_processed_at = finished_at
            attachment.ocr_last_error = str(exc)
            attachment.ocr_error_message = str(exc)
            attachment.ocr_processing_time_seconds = max((finished_at - started_at).total_seconds(), 0.0)
            result.failed += 1
            current_app.logger.exception(
                "Falha no OCR do attachment id=%s filename=%s",
                attachment.id,
                attachment.filename,
            )

        db.session.commit()

    return result
