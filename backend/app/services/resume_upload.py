import logging
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.schemas.resume import PDFUploadResponse, ResumeUploadResponse
from app.services.pdf_extraction import PDFExtractionService

logger = logging.getLogger(__name__)


class ResumeUploadService:
    """Handles resume PDF upload, validation, and storage."""

    def __init__(
        self,
        upload_dir: Path | None = None,
        pdf_extractor: PDFExtractionService | None = None,
    ) -> None:
        self.upload_dir = upload_dir or settings.upload_dir
        self.pdf_extractor = pdf_extractor or PDFExtractionService()

    async def save_resume(
        self,
        file: UploadFile,
        candidate_id: str | None = None,
    ) -> ResumeUploadResponse:
        """Validate and persist an uploaded resume PDF."""
        candidate_id = candidate_id or str(uuid4())
        self._validate_file(file)

        content = await file.read()
        self._validate_size(content)
        file_path = self._persist_file(candidate_id, file.filename or "resume.pdf", content)

        logger.info("Resume saved for candidate %s", candidate_id)

        return ResumeUploadResponse(
            candidate_id=candidate_id,
            file_name=file.filename or "resume.pdf",
            file_path=str(file_path),
            file_size_bytes=len(content),
            uploaded_at=datetime.utcnow(),
        )

    async def upload_and_extract(
        self,
        file: UploadFile,
        candidate_id: str | None = None,
    ) -> PDFUploadResponse:
        """Validate, persist, and extract text from an uploaded resume PDF."""
        candidate_id = candidate_id or str(uuid4())
        self._validate_file(file)

        content = await file.read()
        self._validate_size(content)

        extraction = await self.pdf_extractor.extract_from_bytes(
            content,
            source=file.filename or "resume.pdf",
        )
        file_path = self._persist_file(candidate_id, file.filename or "resume.pdf", content)

        logger.info(
            "Resume uploaded and extracted for candidate %s (%d pages)",
            candidate_id,
            extraction.page_count,
        )

        return PDFUploadResponse(
            candidate_id=candidate_id,
            file_name=file.filename or "resume.pdf",
            file_path=str(file_path),
            file_size_bytes=len(content),
            page_count=extraction.page_count,
            character_count=extraction.character_count,
            text=extraction.text,
            uploaded_at=datetime.utcnow(),
        )

    async def upload_and_extract_gmail(
        self,
        file: UploadFile,
        content: bytes,
        candidate_id: str,
    ) -> PDFUploadResponse:
        """Validate and extract a Gmail PDF/DOCX without changing manual uploads."""
        filename = file.filename or ""
        if not filename or Path(filename).name != filename or any(
            separator in filename for separator in ("/", "\\")
        ):
            raise ValidationError("A valid attachment filename is required")

        extension = Path(filename).suffix.lower()
        if extension not in {".pdf", ".docx"}:
            raise ValidationError("Only PDF and DOCX attachments can be imported")
        self._validate_size(content)
        if not content:
            raise ValidationError("Attachment is empty")

        content_type = (file.content_type or "").lower()
        allowed_types = {
            ".pdf": {"", "application/pdf", "application/x-pdf", "application/octet-stream"},
            ".docx": {
                "",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/zip",
                "application/octet-stream",
            },
        }
        if content_type not in allowed_types[extension]:
            raise ValidationError("Attachment type does not match its filename")

        if extension == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ValidationError("Attachment is not a valid PDF")
            extraction = await self.pdf_extractor.extract_from_bytes(
                content,
                source=filename,
            )
            text = extraction.text
            page_count = extraction.page_count
        else:
            text = self.extract_docx_text(content)
            page_count = 0

        if not text.strip():
            raise ValidationError("Attachment contains no extractable text")

        file_path = self._persist_file(candidate_id, filename, content)
        return PDFUploadResponse(
            candidate_id=candidate_id,
            file_name=filename,
            file_path=str(file_path),
            file_size_bytes=len(content),
            page_count=page_count,
            character_count=len(text),
            text=text,
            uploaded_at=datetime.utcnow(),
        )

    @staticmethod
    def extract_docx_text(content: bytes) -> str:
        try:
            with zipfile.ZipFile(BytesIO(content)) as document:
                document_xml_info = document.getinfo("word/document.xml")
                if document_xml_info.file_size > settings.max_upload_size_bytes:
                    raise ValidationError("DOCX document content is too large")
                xml = ElementTree.fromstring(document.read("word/document.xml"))
        except ValidationError:
            raise
        except (
            KeyError,
            OSError,
            RuntimeError,
            zipfile.BadZipFile,
            ElementTree.ParseError,
        ) as exc:
            raise ValidationError("Attachment is not a valid DOCX document") from exc

        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        return "\n".join(
            "".join(node.itertext())
            for node in xml.iter(f"{namespace}p")
        )

    def _persist_file(self, candidate_id: str, filename: str, content: bytes) -> Path:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.upload_dir / f"{candidate_id}_{filename}"
        file_path.write_bytes(content)
        return file_path

    def _validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise ValidationError("Filename is required")

        extension = Path(file.filename).suffix.lower()
        if extension not in settings.allowed_extension_set:
            raise ValidationError(
                f"Invalid file type. Allowed: {', '.join(settings.allowed_extension_set)}"
            )

        content_type = (file.content_type or "").lower()
        allowed_types = {
            "application/pdf",
            "application/x-pdf",
            "application/octet-stream",
        }
        if content_type and content_type not in allowed_types:
            raise ValidationError("Invalid content type. Only PDF files are supported")

    def _validate_size(self, content: bytes) -> None:
        if len(content) > settings.max_upload_size_bytes:
            raise ValidationError(
                f"File exceeds maximum size of {settings.max_upload_size_mb}MB"
            )
