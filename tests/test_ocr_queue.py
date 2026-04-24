from pathlib import Path
from datetime import datetime, timezone

from core.database import db
from core.models import Attachment
from core.services.ocr_queue import (
    OCR_STATUS_BAIXO_APROVEITAMENTO,
    OCR_STATUS_CONCLUIDO,
    OCR_STATUS_PENDENTE,
    OCR_STATUS_PROCESSANDO,
    enqueue_attachment_for_ocr,
    is_pdf_ocr_eligible,
    process_pending_ocr_attachments,
)


def test_is_pdf_ocr_eligible():
    assert is_pdf_ocr_eligible("arquivo.pdf") is True
    assert is_pdf_ocr_eligible("arquivo.bin", "application/pdf") is True
    assert is_pdf_ocr_eligible("arquivo.txt", "text/plain") is False


def test_process_pending_ocr_attachments_success(app_ctx, monkeypatch, tmp_path):
    app_ctx.config["UPLOAD_FOLDER"] = str(tmp_path)
    file_path = Path(tmp_path) / "anexo.pdf"
    file_path.write_bytes(b"%PDF-1.4")

    attachment = Attachment(article_id=1, filename="anexo.pdf", mime_type="application/pdf")
    enqueue_attachment_for_ocr(attachment)
    db.session.add(attachment)
    db.session.commit()

    monkeypatch.setattr("core.services.ocr_queue.extract_text", lambda *_: "texto suficiente " * 10)

    result = process_pending_ocr_attachments(batch_size=10, low_yield_threshold=20)

    db.session.refresh(attachment)
    assert result.processed == 1
    assert result.concluded == 1
    assert attachment.ocr_status == OCR_STATUS_CONCLUIDO
    assert attachment.ocr_attempts == 1
    assert attachment.ocr_started_at is not None
    assert attachment.ocr_finished_at is not None
    assert attachment.ocr_processed_at is not None
    assert attachment.ocr_last_attempt_at is not None
    assert "texto suficiente" in (attachment.content or "")
    assert "texto suficiente" in (attachment.ocr_text or "")


def test_process_pending_ocr_attachments_recovers_stuck(app_ctx, monkeypatch):
    attachment = Attachment(article_id=1, filename="travado.pdf", mime_type="application/pdf")
    attachment.ocr_status = OCR_STATUS_PROCESSANDO
    attachment.ocr_started_at = datetime.now(timezone.utc)
    db.session.add(attachment)
    db.session.commit()

    monkeypatch.setattr("core.services.ocr_queue.extract_text", lambda *_: "curto")

    result = process_pending_ocr_attachments(batch_size=10, low_yield_threshold=10, stuck_timeout_minutes=0)

    db.session.refresh(attachment)
    assert result.recovered_stuck == 1
    assert attachment.ocr_status == OCR_STATUS_BAIXO_APROVEITAMENTO
    assert attachment.ocr_attempts == 1
    assert attachment.ocr_last_error is None
    assert attachment.ocr_error_message is None
