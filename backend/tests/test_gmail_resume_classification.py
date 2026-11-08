from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock

import fitz
import pytest
from google.oauth2.credentials import Credentials
from app.services.pdf_extraction import PDFExtractionResult

from app.services.gmail_ingestion import GmailIngestionService


def make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 780), text)
    content = document.tobytes()
    document.close()
    return content


def make_docx(text: str) -> bytes:
    xml_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(
            f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
            for line in xml_text.splitlines()
        )
        + "</w:body></w:document>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return output.getvalue()


def attachment(message_id: str, attachment_id: str, filename: str) -> dict:
    return {
        "message_id": message_id,
        "attachment_id": attachment_id,
        "filename": filename,
        "size": 1000,
        "mime_type": "application/pdf",
        "subject": "Documents",
        "sender": "sender@example.com",
        "date": "2026-01-01",
    }


@pytest.mark.asyncio
async def test_classifies_resume_and_unrelated_pdf_from_extracted_content(monkeypatch):
    resume_text = """Jordan Lee
jordan.lee@example.com
+1 415 555 2678
Professional Summary
Software engineer with 5 years experience.
Skills
Python, Java, SQL, React
Work Experience
Software Engineer, Acme Corp, 2021 - Present
Built internal systems.
Education
Bachelor of Science in Computer Science, State University, 2020
Projects
Inventory Application - Built using Python"""
    scholarship_text = """Scholarship Application Guidelines
This information flyer describes available scholarships and application deadlines.
Applicants should provide proof of enrollment and financial aid documents."""

    documents = {
        "resume-id": make_pdf(resume_text),
        "scholarship-id": make_pdf(scholarship_text),
    }
    service = GmailIngestionService()
    downloads = []
    extract_text = AsyncMock(wraps=service._extract_attachment_text)
    monkeypatch.setattr(service, "_extract_attachment_text", extract_text)

    def download(credentials, message_id, attachment_id):
        downloads.append(attachment_id)
        if attachment_id == "duplicate-resume-id":
            return documents["resume-id"]
        return documents[attachment_id]

    monkeypatch.setattr(service, "download_attachment", download)
    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [
            attachment("message-1", "resume-id", "profile.pdf"),
            attachment("message-2", "scholarship-id", "scholarship.pdf"),
        ],
    )

    assert results[0]["classification"] == "RESUME"
    assert results[0]["confidence"] >= 0.6
    assert "skills" in results[0]["classification_reason"]
    assert results[1]["classification"] == "NON_RESUME"
    assert results[1]["confidence"] >= 0.8
    assert len(results[0]["content_hash"]) == 64
    assert len(downloads) == 2

    repeated = await service.classify_attachments(
        Credentials(token="test-token"),
        [attachment("message-3", "duplicate-resume-id", "candidate.pdf")],
    )
    assert repeated[0]["classification"] == "RESUME"
    assert len(downloads) == 3
    assert extract_text.await_count == 2


@pytest.mark.asyncio
async def test_extracts_and_classifies_docx_resume(monkeypatch):
    resume_text = """Morgan Rivera
morgan.rivera@example.com
Skills
Python, SQL, data analysis
Experience
Data Analyst, Example Corp, 2022 - Present
Education
Bachelor of Science, Example University
Projects
Sales Forecast Dashboard"""
    content = make_docx(resume_text)
    service = GmailIngestionService()
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: content,
    )

    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [attachment("message-1", "docx-id", "profile.docx")],
    )

    assert results[0]["classification"] == "RESUME"
    assert results[0]["confidence"] >= 0.6


@pytest.mark.asyncio
async def test_classifies_unrelated_docx_document(monkeypatch):
    content = make_docx(
        "Scholarship Application Guidelines\n"
        "This information flyer describes available scholarships and deadlines. "
        "Applicants should provide proof of enrollment and financial aid documents."
    )
    service = GmailIngestionService()
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: content,
    )

    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [attachment("message-1", "scholarship-docx", "guidelines.docx")],
    )

    assert results[0]["classification"] == "NON_RESUME"
    assert results[0]["confidence"] >= 0.8
    assert "non-resume" in results[0]["classification_reason"].lower()


@pytest.mark.asyncio
async def test_email_body_supports_non_resume_classification_but_not_by_itself(
    monkeypatch,
):
    service = GmailIngestionService()
    document_text = (
        "Community program overview with meeting details, enrollment instructions, "
        "important dates, local resources, and general information for participants."
    )
    content = make_pdf(document_text)
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: content,
    )
    llm_call = AsyncMock()
    monkeypatch.setattr(
        "app.services.gmail_ingestion.ProjectExtractionService._call_ollama",
        llm_call,
    )
    item = attachment("message-1", "body-context", "information.pdf")
    item["_email_body"] = "Attached is the scholarship application flyer."

    result = await service.classify_attachments(
        Credentials(token="test-token"),
        [item],
    )

    assert result[0]["classification"] == "NON_RESUME"
    assert result[0]["confidence"] >= 0.8
    llm_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_filename_alone_does_not_classify_as_resume(monkeypatch):
    service = GmailIngestionService()
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: make_pdf(
            "Quarterly community bulletin with local event announcements."
        ),
    )

    async def uncertain_ai(self, prompt):
        assert "Quarterly community bulletin" in prompt
        return '{"classification":"UNCERTAIN","confidence":0.55,"reason":"No career history found."}'

    monkeypatch.setattr(
        "app.services.gmail_ingestion.ProjectExtractionService._call_ollama",
        uncertain_ai,
    )
    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [attachment("message-1", "other-id", "Resume.pdf")],
    )

    assert results[0]["classification"] == "UNCERTAIN"


@pytest.mark.asyncio
async def test_low_confidence_non_resume_is_kept_for_review(monkeypatch):
    service = GmailIngestionService()
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: make_pdf(
            "Community program details and dates for the coming year. "
            "The event includes local information sessions, registration "
            "details, community resources, and application timelines."
        ),
    )

    async def uncertain_ai(self, prompt):
        return '{"classification":"NON_RESUME","confidence":0.6,"reason":"Not enough career evidence."}'

    monkeypatch.setattr(
        "app.services.gmail_ingestion.ProjectExtractionService._call_ollama",
        uncertain_ai,
    )
    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [attachment("message-1", "ambiguous-id", "document.pdf")],
    )

    assert results[0]["classification"] == "UNCERTAIN"
    assert results[0]["confidence"] == 0.6


@pytest.mark.asyncio
async def test_scanned_pdf_with_insufficient_ocr_text_stays_uncertain(monkeypatch):
    service = GmailIngestionService()
    scanned_pdf = make_pdf("")
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: scanned_pdf,
    )

    async def limited_ocr(self, content, *, source):
        assert content == scanned_pdf
        return PDFExtractionResult(
            text="Scholarship",
            page_count=1,
            character_count=len("Scholarship"),
        )

    llm_call = AsyncMock()
    monkeypatch.setattr(
        "app.services.gmail_ingestion.PDFExtractionService.extract_from_bytes",
        limited_ocr,
    )
    monkeypatch.setattr(
        "app.services.gmail_ingestion.ProjectExtractionService._call_ollama",
        llm_call,
    )

    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [attachment("message-1", "scanned-id", "scholarship.pdf")],
    )

    assert results[0]["classification"] == "UNCERTAIN"
    assert results[0]["confidence"] == 0.0
    assert "Insufficient readable text" in results[0]["classification_reason"]
    llm_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_document_hash_reuses_extraction_and_classification(
    monkeypatch,
):
    content = make_pdf(
        "Jordan Lee\njordan.lee@example.com\n"
        "Community profile details and general information. "
        "This document contains background information, community updates, "
        "and general notes for readers interested in local programs."
    )
    service = GmailIngestionService()
    extracted = AsyncMock(return_value=(
        "Jordan Lee\njordan.lee@example.com\n"
        "Community profile details and general information. "
        "This document contains background information, community updates, "
        "and general notes for readers interested in local programs."
    ))
    monkeypatch.setattr(service, "_extract_attachment_text", extracted)
    monkeypatch.setattr(
        service,
        "download_attachment",
        lambda credentials, message_id, attachment_id: content,
    )
    prompts: list[str] = []

    async def classify_with_context(self, prompt):
        prompts.append(prompt)
        return (
            '{"classification":"UNCERTAIN","confidence":0.6,'
            '"reason":"Insufficient career evidence."}'
        )

    monkeypatch.setattr(
        "app.services.gmail_ingestion.ProjectExtractionService._call_ollama",
        classify_with_context,
    )

    first = attachment("message-1", "attachment-1", "profile.pdf")
    first["subject"] = "Community update"
    first["_email_body"] = "Sharing a general information document."
    second = attachment("message-2", "attachment-2", "profile.pdf")
    second["subject"] = "Application for software role"
    second["_email_body"] = "Please review this candidate profile."

    results = await service.classify_attachments(
        Credentials(token="test-token"),
        [first, second],
    )

    assert results[0]["classification"] == "UNCERTAIN"
    assert results[1]["classification"] == "UNCERTAIN"
    assert extracted.await_count == 1
    assert len(prompts) == 1
    assert "Community update" in prompts[0]
