import re

DOCUMENTS = [
    {
        "title": "DocPilot overview",
        "content": """
DocPilot AI is a documentation assistant built with Cloudflare Workers.
The project uses Cloudflare Workers AI and the Google Gemma model for chat generation.
The application exposes a health endpoint at GET /health and a question endpoint at POST /api/chat.
The project is designed to answer questions using documentation context instead of guessing.
The long-term architecture includes ingestion, chunking, embeddings, and retrieval augmented generation.
The project should keep a clear separation between document loading, retrieval, and LLM prompting.
""".strip(),
    },
    {
        "title": "AI engineering roadmap",
        "content": """
The AI engineering roadmap starts with a working LLM app, then adds a documentation store.
Next steps include loading Markdown files, splitting them into chunks, generating embeddings, and storing vectors.
A retrieval step selects the most relevant chunks for a user question and sends them to the model as context.
The final answer should cite the source sections and state when the answer is not supported by the documents.
Production quality also requires monitoring, rate limiting, testing, and evaluation metrics.
""".strip(),
    },
]


def chunk_text(text, chunk_size=500, overlap=100):
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def rank_chunks(question, chunks):
    q_tokens = {token.lower() for token in re.findall(r"[a-z0-9]+", question)}
    ranked = []
    for chunk in chunks:
        score = 0
        text = chunk.lower()
        for token in q_tokens:
            score += text.count(token)
        ranked.append({"text": chunk, "score": score})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def load_default_context(question, limit=3):
    available_chunks = []
    for doc in DOCUMENTS:
        for chunk in chunk_text(doc["content"]):
            available_chunks.append({"title": doc["title"], "text": chunk})

    ranked = rank_chunks(question, [item["text"] for item in available_chunks])
    selections = []
    seen = set()

    for item in ranked:
        text = item["text"]
        if not text or text in seen:
            continue
        seen.add(text)
        for doc_piece in available_chunks:
            if doc_piece["text"] == text:
                selections.append({"title": doc_piece["title"], "text": text})
                break
        if len(selections) >= limit:
            break

    if not selections:
        return "No relevant documentation context was found for this question."

    return "\n\n".join(f"[{item['title']}]\n{item['text']}" for item in selections)
