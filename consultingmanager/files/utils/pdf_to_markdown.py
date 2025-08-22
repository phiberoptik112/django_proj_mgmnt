import pdfplumber
from typing import Tuple
import re


def extract_text_and_title(pdf_path: str) -> Tuple[str, str, int]:
    """
    Extract plain text and a reasonable title guess from a PDF.
    Returns (text, title, page_count).
    """
    text_chunks = []
    title_guess = ""
    page_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            if idx == 0:
                # Guess title from first page: first non-empty line under ~120 chars
                for line in page_text.splitlines():
                    candidate = line.strip()
                    if 3 < len(candidate) <= 120:
                        title_guess = candidate
                        break
            text_chunks.append(page_text)

    full_text = "\n".join(text_chunks)
    if not title_guess:
        # Fallback to first non-empty line in full_text
        for line in full_text.splitlines():
            candidate = line.strip()
            if 3 < len(candidate) <= 120:
                title_guess = candidate
                break

    return full_text, title_guess, page_count


essential_headings = [
    "Executive Summary",
    "Summary",
    "Scope of Work",
    "Basic Services",
    "Additional Services",
    "Compensation",
    "Fees",
    "Schedule",
    "Deliverables",
    "Terms",
]


def plain_text_to_markdown(text: str, title: str) -> str:
    """Convert a simple plain-text PDF extraction into coarse-grained Markdown."""
    lines = text.splitlines()

    def is_heading(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        # Consider ALLCAPS or known headings as headers
        if stripped.isupper() and len(stripped) <= 80 and re.search(r"[A-Z]", stripped):
            return True
        for h in essential_headings:
            if stripped.lower().startswith(h.lower()):
                return True
        return False

    md_lines = [f"# {title}" if title else "# Document"]
    buffer: list[str] = []

    def flush_paragraph():
        nonlocal buffer
        if buffer:
            md_lines.append(" ".join(buffer).strip())
            md_lines.append("")
            buffer = []

    for line in lines:
        if is_heading(line):
            flush_paragraph()
            # Normalize heading level
            heading_text = line.strip().title()
            md_lines.append(f"## {heading_text}")
            md_lines.append("")
        else:
            if line.strip() == "":
                flush_paragraph()
            else:
                buffer.append(line.strip())

    flush_paragraph()
    return "\n".join(md_lines).strip() + "\n"


def summarize_markdown(md: str, max_sentences: int = 5) -> str:
    """
    Very lightweight heuristic summarizer: take opening paragraph, look for key headings
    and extract first sentences. This is intentionally simple and fast for backend usage
    without external ML dependencies.
    """
    # Prefer content under common summary headers
    sections = re.split(r"^##\s+", md, flags=re.MULTILINE)
    first_paragraph = []

    # section[0] may contain the main title line; find the first non-empty paragraph
    for line in sections[0].splitlines():
        if line.startswith("# "):
            continue
        if line.strip():
            first_paragraph.append(line.strip())
        elif first_paragraph:
            break

    summary_candidates = [" ".join(first_paragraph)] if first_paragraph else []

    for sec in sections[1:]:
        header, _, body = sec.partition("\n")
        header_lower = header.lower().strip()
        if any(h.lower() in header_lower for h in ["executive summary", "summary", "overview", "scope", "compensation", "fees"]):
            # take first non-empty line(s)
            body_lines = [l.strip() for l in body.splitlines() if l.strip()]
            if body_lines:
                summary_candidates.append(body_lines[0])
        if len(summary_candidates) >= max_sentences:
            break

    # Fallback: take first N sentences of the entire doc content under title
    if not summary_candidates:
        text = re.sub(r"\s+", " ", md)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        summary_candidates = sentences[:max_sentences]

    # Join and trim
    summary = " ".join([s for s in summary_candidates if s])
    # Reduce to ~800 chars to keep it concise
    return (summary[:800] + ("…" if len(summary) > 800 else ""))


def pdf_to_markdown_and_summary(pdf_path: str) -> tuple[str, str, int, str]:
    """
    Convert a PDF to Markdown and a brief summary.
    Returns: (markdown, summary, page_count, title)
    """
    text, title, page_count = extract_text_and_title(pdf_path)
    md = plain_text_to_markdown(text, title)
    summ = summarize_markdown(md)
    return md, summ, page_count, title
