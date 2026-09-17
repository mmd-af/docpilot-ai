"""Offline Markdown -> Workers AI embeddings -> Vectorize ingestion CLI.

Usage:
  CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_API_TOKEN=... \
  python scripts/ingest.py --index docpilot --docs docs
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag import EMBEDDING_MODEL, chunk_markdown


def api_call(url: str, token: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        body = json.load(response)
    if not isinstance(body, dict) or body.get("success") is False:
        raise RuntimeError(f"Cloudflare API failed: {body}")
    return body


def upsert_vectors(url: str, token: str, vectors: list[dict]) -> dict:
    body = "\n".join(json.dumps(vector) for vector in vectors).encode() + b"\n"
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/x-ndjson",
        },
    )
    with urlopen(request, timeout=60) as response:
        result = json.load(response)
    if not isinstance(result, dict) or result.get("success") is False:
        raise RuntimeError(f"Cloudflare Vectorize upsert failed: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--api-token", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    parser.add_argument("--chunk-size", type=int, default=900)
    args = parser.parse_args()

    base = f"https://api.cloudflare.com/client/v4/accounts/{args.account_id}"
    chunks = []
    for path in sorted(args.docs.rglob("*.md")):
        chunks.extend(
            chunk_markdown(
                path.read_text(encoding="utf-8"),
                path.as_posix(),
                args.chunk_size,
            )
        )

    for offset in range(0, len(chunks), 20):
        batch = chunks[offset : offset + 20]
        embedding = api_call(
            f"{base}/ai/run/{EMBEDDING_MODEL}",
            args.api_token,
            {"text": [chunk["text"] for chunk in batch]},
        )
        vectors = embedding.get("result", {}).get("data", [])
        if not isinstance(vectors, list) or len(vectors) != len(batch):
            raise RuntimeError("Embedding API returned an unexpected vector count")

        payload = []
        for chunk, vector in zip(batch, vectors):
            if not isinstance(vector, list):
                raise RuntimeError("Embedding API returned an invalid vector")
            chunk_id = hashlib.sha256(chunk["id"].encode()).hexdigest()[:32]
            payload.append({"id": chunk_id, "values": vector, "metadata": chunk})

        upsert_vectors(
            f"{base}/vectorize/v2/indexes/{args.index}/upsert",
            args.api_token,
            payload,
        )

    print(f"Ingested {len(chunks)} chunks into {args.index}.")


if __name__ == "__main__":
    main()
