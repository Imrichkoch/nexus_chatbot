from __future__ import annotations

import re
from pathlib import Path


ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".log"}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def validate_document(name: str, content: str) -> tuple[str, str]:
    clean_name = Path(name.strip()).name
    if not clean_name or Path(clean_name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Podporované sú iba TXT, MD, JSON, YAML, CSV a LOG súbory.")
    if len(content.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise OverflowError("Dokument je väčší ako povolených 10 MB.")
    clean_content = content.replace("\x00", "").strip()
    if not clean_content:
        raise ValueError("Dokument je prázdny.")
    return clean_name, clean_content


def chunk_text(content: str, target_chars: int = 1400) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > target_chars:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(paragraph), target_chars):
                chunks.append(paragraph[start : start + target_chars])
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > target_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def fts_query(text: str) -> str:
    tokens = re.findall(r"[\wáäčďéíľĺňóôŕšťúýž]{2,}", text.lower(), re.UNICODE)
    return " OR ".join(f'"{token}"' for token in tokens[:12])
