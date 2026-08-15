import io

import fitz
import pytest
from httpx import AsyncClient

from app.services.pdf_extraction import PDFExtractionService


def build_sample_pdf(text: str = "Jane Doe\nPython Developer") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_pdf_extraction_from_bytes() -> None:
    service = PDFExtractionService()
    pdf_bytes = build_sample_pdf("Hello Resume World")

    result = await service.extract_from_bytes(pdf_bytes, source="test.pdf")

    assert result.page_count == 1
    assert "Hello Resume World" in result.text
    assert result.character_count == len(result.text)


@pytest.mark.asyncio
async def test_upload_resume_extracts_text(client: AsyncClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.resume_upload.settings.upload_dir",
        tmp_path,
    )

    pdf_bytes = build_sample_pdf("Senior Backend Engineer")
    files = {"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["file_name"] == "resume.pdf"
    assert data["page_count"] == 1
    assert "Senior Backend Engineer" in data["text"]
    assert data["character_count"] == len(data["text"])
    assert "candidate_id" in data


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client: AsyncClient) -> None:
    files = {"file": ("resume.txt", io.BytesIO(b"not a pdf"), "text/plain")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_empty_pdf(client: AsyncClient) -> None:
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}

    response = await client.post("/api/v1/resumes/upload", files=files)

    assert response.status_code == 422
