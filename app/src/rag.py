"""Request-time RAG helpers. Documents are ingested into Vectorize offline."""

from dataclasses import dataclass
import re
from typing import Any

EMBEDDING_MODEL = "@cf/baai/bge-base-en-v1.5"
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class Citation:
    source: str
    title: str
    section: str
    chunk_id: str
    text: str


def chunk_markdown(markdown: str, source: str, chunk_size: int = 900, overlap: int = 120) -> list[dict[str, Any]]:
    """Split Markdown by headings first, retaining enough metadata for citations."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")
    lines = markdown.splitlines()
    section = "Document"
    pieces: list[dict[str, str]] = []
    current: list[str] = []
    for line in lines:
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            if current:
                pieces.append({"section": section, "text": "\n".join(current).strip()})
                current = []
            section = heading.group(1).strip()
        elif line.strip():
            current.append(line.strip())
    if current:
        pieces.append({"section": section, "text": "\n".join(current).strip()})

    result: list[dict[str, Any]] = []
    for piece in pieces:
        text = re.sub(r"\s+", " ", piece["text"]).strip()
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                index = len(result)
                result.append({
                    "id": f"{source}:{index}",
                    "source": source,
                    "title": source.rsplit("/", 1)[-1],
                    "section": piece["section"],
                    "text": chunk,
                })
            if end == len(text):
                break
            start = end - overlap
    return result


def _metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def citations_from_matches(matches: Any, limit: int = DEFAULT_TOP_K) -> list[Citation]:
    """Convert the untyped Vectorize response into bounded, safe citation records."""
    if not isinstance(matches, list):
        return []
    citations: list[Citation] = []
    for match in matches[: max(0, limit)]:
        if not isinstance(match, dict):
            continue
        metadata = _metadata(match.get("metadata"))
        text = metadata.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        citations.append(Citation(
            source=str(metadata.get("source", "unknown")),
            title=str(metadata.get("title", metadata.get("source", "Documentation"))),
            section=str(metadata.get("section", "Document")),
            chunk_id=str(match.get("id", "")),
            text=text.strip(),
        ))
    return citations


async def retrieve(env: Any, question: str, top_k: int = DEFAULT_TOP_K) -> list[Citation]:
    """Embed a question and query the Vectorize binding without assuming response shape."""
    embedding = await env.AI.run(EMBEDDING_MODEL, {"text": [question]})
    vector = embedding.get("data", [None])[0] if isinstance(embedding, dict) else None
    if not isinstance(vector, list) or not vector:
        raise RuntimeError("Embedding model returned no vector")
    matches = await env.VECTORIZE.query(vector, {"topK": max(1, min(top_k, 20)), "returnMetadata": "all"})
    raw = matches.get("matches", []) if isinstance(matches, dict) else getattr(matches, "matches", [])
    return citations_from_matches(raw, top_k)


def build_grounded_prompt(question: str, citations: list[Citation]) -> str:
    context = "\n\n".join(
        f"[{citation.title} — {citation.section} | {citation.source}]\n{citation.text}"
        for citation in citations
    ) or "[No matching documentation was retrieved.]"
    return (
        "Answer the question using only the documentation excerpts below. "
        "If they do not support an answer, say that clearly. Do not invent citations.\n\n"
        f"Documentation excerpts:\n{context}\n\nQuestion:\n{question.strip()}"
    )
