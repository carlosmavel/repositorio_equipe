from pathlib import Path
from datetime import date, datetime, timezone

from core.database import db
from core.models import Attachment, Boletim, User
from core.services.ocr_queue import (
    OCR_STATUS_BAIXO_APROVEITAMENTO,
    OCR_STATUS_CONCLUIDO,
    OCR_STATUS_PENDENTE,
    OCR_STATUS_PROCESSANDO,
    enqueue_attachment_for_ocr,
    enqueue_boletim_for_ocr,
    is_pdf_ocr_eligible,
    process_pending_ocr_attachments,
    process_pending_ocr_boletins,
)
from core.utils import normalize_ocr_text_for_search


def test_normalize_ocr_text_for_search_preserves_words_accents_and_punctuation():
    assert (
        normalize_ocr_text_for_search("  João\r\n\t  d\'Água,  nº 10.  ")
        == "João d'Água, nº 10."
    )


def test_process_pending_ocr_attachments_normalizes_searchable_text(
    app_ctx, monkeypatch, tmp_path
):
    app_ctx.config["UPLOAD_FOLDER"] = str(tmp_path)
    file_path = Path(tmp_path) / "anexo_espacos.pdf"
    file_path.write_bytes(b"%PDF-1.4")

    attachment = Attachment(
        article_id=1, filename="anexo_espacos.pdf", mime_type="application/pdf"
    )
    enqueue_attachment_for_ocr(attachment)
    db.session.add(attachment)
    db.session.commit()

    monkeypatch.setattr(
        "core.services.ocr_queue.extract_text",
        lambda *_: "  Texto\n\tcom   espaços\r\nredundantes.  ",
    )

    result = process_pending_ocr_attachments(batch_size=10, low_yield_threshold=1)

    db.session.refresh(attachment)
    assert result.concluded == 1
    assert attachment.content == "Texto com espaços redundantes."
    assert attachment.ocr_text == "Texto com espaços redundantes."
    assert attachment.ocr_char_count == len("Texto com espaços redundantes.")


def test_process_pending_ocr_boletins_normalizes_searchable_text(
    app_ctx, monkeypatch, tmp_path
):
    app_ctx.config["UPLOAD_FOLDER"] = str(tmp_path)
    file_path = Path(tmp_path) / "boletim_espacos.pdf"
    file_path.write_bytes(b"%PDF-1.4")

    user = User(username="ocr_boletim", email="ocr-boletim@test.local", password_hash="x")
    db.session.add(user)
    db.session.flush()
    boletim = Boletim(
        titulo="Boletim Diário",
        arquivo="boletim_espacos.pdf",
        data_boletim=date(2026, 6, 17),
        created_by=user.id,
    )
    enqueue_boletim_for_ocr(boletim)
    db.session.add(boletim)
    db.session.commit()

    monkeypatch.setattr(
        "core.services.ocr_queue.extract_text",
        lambda *_: "  Linha 1\n\tLinha   2 com acentuação.  ",
    )

    result = process_pending_ocr_boletins(batch_size=10, low_yield_threshold=1)

    db.session.refresh(boletim)
    assert result.concluded == 1
    assert boletim.ocr_text == "Linha 1 Linha 2 com acentuação."
    assert boletim.ocr_char_count == len("Linha 1 Linha 2 com acentuação.")
    assert "linha 1 linha 2 com acentuacao" in boletim.search_text_normalized


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
