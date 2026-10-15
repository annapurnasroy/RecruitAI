
from io import BytesIO
from pypdf import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract selectable text from a PDF using pypdf."""
    if not pdf_bytes:
        return ""

    try:
        reader = PdfReader(BytesIO(pdf_bytes))

        if reader.is_encrypted:
            raise ValueError(
                "This PDF is password-protected and cannot be read."
            )

        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts).strip()

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read this PDF: {exc}") from exc
