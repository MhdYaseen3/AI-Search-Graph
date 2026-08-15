import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract

from PIL import Image
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PDFExtractionResult:
    text: str
    page_count: int
    character_count: int


class PDFExtractionService:
    """Extract text from text-based and scanned PDF resume files."""

    OCR_THRESHOLD = 50

    async def extract_text(
        self,
        file_path: str | Path,
    ) -> str:
        """Extract text from a PDF, using OCR when necessary."""

        path = Path(file_path)

        if not path.exists():
            raise ValidationError(
                f"PDF file not found: {path}"
            )

        if path.suffix.lower() != ".pdf":
            raise ValidationError(
                "Only PDF files are supported"
            )

        content = path.read_bytes()

        result = self._extract_from_bytes(
            content,
            source=path.name,
        )

        return result.text

    async def extract_from_bytes(
        self,
        content: bytes,
        *,
        source: str = "upload.pdf",
    ) -> PDFExtractionResult:
        """Extract text from PDF bytes."""

        if not content:
            raise ValidationError(
                "PDF file is empty"
            )

        return self._extract_from_bytes(
            content,
            source=source,
        )

    def _extract_from_bytes(
        self,
        content: bytes,
        *,
        source: str,
    ) -> PDFExtractionResult:

        try:
            with fitz.open(
                stream=content,
                filetype="pdf",
            ) as document:

                page_count = document.page_count

                # --------------------------------
                # STEP 1: Normal PDF text extraction
                # --------------------------------

                text_parts: list[str] = []

                for page in document:
                    text_parts.append(
                        page.get_text()
                    )

                extracted = "\n".join(
                    text_parts
                ).strip()

                logger.info(
                    "PyMuPDF extracted %d characters "
                    "from %s (%d pages)",
                    len(extracted),
                    source,
                    page_count,
                )

                # --------------------------------
                # STEP 2: OCR fallback
                # --------------------------------

                if len(extracted) < self.OCR_THRESHOLD:

                    logger.info(
                        "Little/no text detected in %s. "
                        "Starting OCR.",
                        source,
                    )

                    extracted = self._extract_with_ocr(
                        document
                    )

                logger.info(
                    "Final extraction: %d characters "
                    "from %s",
                    len(extracted),
                    source,
                )

                return PDFExtractionResult(
                    text=extracted,
                    page_count=page_count,
                    character_count=len(extracted),
                )

        except ValidationError:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to extract text from PDF: %s",
                source,
            )

            raise ValidationError(
                "Unable to extract text from PDF"
            ) from exc

    def _extract_with_ocr(
        self,
        document,
    ) -> str:
        """Extract text from image/scanned PDF pages using OCR."""

        text_parts: list[str] = []

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            logger.info(
                "Running OCR on page %d",
                page_number,
            )

            # Render PDF page as image.
            matrix = fitz.Matrix(
                2,
                2,
            )

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                [
                    pixmap.width,
                    pixmap.height,
                ],
                pixmap.samples,
            )

            # OCR
            text = pytesseract.image_to_string(
                image,
                lang="eng",
            )

            if text.strip():
                text_parts.append(
                    text.strip()
                )

        return "\n\n".join(
            text_parts
        ).strip()