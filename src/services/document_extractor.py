"""Text extraction utilities for PDF, DOCX, and TXT files."""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def extract_text_from_file(file_path: str) -> Optional[str]:
    """
    Extract plain text from a file.
    Supports: .pdf, .docx, .doc, .txt
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            return await _extract_pdf(file_path)
        elif suffix in (".docx", ".doc"):
            return await _extract_docx(file_path)
        elif suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8", errors="ignore")
        else:
            logger.warning(f"Unsupported file type: {suffix}")
            return None
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return None


async def _extract_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber (preferred) or PyPDF2 as fallback."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        pass  # Fall through to PyPDF2

    try:
        import PyPDF2
        text_parts = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except ImportError:
        logger.error("Install pdfplumber or PyPDF2: pip install pdfplumber")
        raise


async def _extract_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        logger.error("Install python-docx: pip install python-docx")
        raise
