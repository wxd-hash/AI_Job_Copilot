import fitz


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(file_path)
    text_parts: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            text_parts.append(text.strip())
    doc.close()
    return "\n\n".join(text_parts)


def extract_text_from_pdf_bytes(content: bytes) -> str:
    """Extract all text from PDF file bytes."""
    doc = fitz.open(stream=content, filetype="pdf")
    text_parts: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            text_parts.append(text.strip())
    doc.close()
    return "\n\n".join(text_parts)
