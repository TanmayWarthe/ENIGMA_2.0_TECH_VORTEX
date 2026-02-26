"""Resume parser module for extracting text from uploaded resumes."""

import io
from PyPDF2 import PdfReader
from ai_engine import extract_resume_skills


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from a plain text file."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """Parse a resume file and extract structured information.
    
    Returns:
        dict with keys: raw_text, skills, experience, education, summary, etc.
    """
    # Extract raw text based on file type
    if filename.lower().endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_bytes)
    elif filename.lower().endswith((".txt", ".text")):
        raw_text = extract_text_from_txt(file_bytes)
    else:
        raw_text = extract_text_from_txt(file_bytes)

    if not raw_text or raw_text.startswith("Error"):
        return {
            "raw_text": raw_text,
            "skills": [],
            "experience": [],
            "education": [],
            "summary": "Unable to extract text from resume",
            "primary_domain": "Unknown",
            "years_of_experience": "Unknown",
            "strongest_skills": []
        }

    # Use AI to extract structured information
    ai_result = extract_resume_skills(raw_text)
    ai_result["raw_text"] = raw_text

    return ai_result
