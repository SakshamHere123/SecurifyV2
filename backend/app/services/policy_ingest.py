import os

from pypdf import PdfReader


def extract_text(file_path: str) -> str:
    """Extracts raw text from an admin-uploaded policy document.
    Supports PDF, Markdown, and plain text -- the formats an admin is
    realistically going to have a company security policy in.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    # .md and .txt are already plain text -- no extraction needed
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = 250, overlap: int = 50) -> list[str]:
    """Splits policy text into overlapping word-based chunks.

    Why chunk at all? Embedding a whole multi-page policy as one vector
    smears every rule together -- a search for "S3 bucket encryption" would
    match weakly against a vector that's an average of 20 unrelated rules.
    Small chunks let the retriever pull back just the relevant paragraph.

    Why overlap? So a rule that happens to fall on a chunk boundary doesn't
    get split in half and lose meaning in both pieces.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap  # step back before the next chunk so they overlap

    return chunks
