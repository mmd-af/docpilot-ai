# DocPilot AI

DocPilot is a Cloudflare Python Worker that answers documentation questions
with retrieval-augmented generation (RAG). It also supports live answers from
up to three public website URLs supplied by the user.

## Architecture

`POST /api/chat` validates the question, embeds it with Workers AI
(`@cf/baai/bge-base-en-v1.5`), queries the `VECTORIZE` binding, and builds a
grounded prompt from the returned metadata. Gemma
(`@cf/google/gemma-4-26b-a4b-it`) generates the answer. The JSON response
contains `response` and a bounded `sources` list (`source`, `title`, `section`,
and `chunk_id`). `GET /health` and static assets remain unchanged.

`POST /api/live-chat` accepts `{ "message": "...", "urls": ["https://..."] }`.
The Worker uses the Cloudflare Browser Run `markdown` Quick Action to render
each URL, then sends bounded excerpts to Workers AI. Configure the `BROWSER`
binding in `wrangler.jsonc`; local development requires remote bindings (for
example `uv run pywrangler dev --remote`). This is URL retrieval, not a
general-purpose web search engine.

Request-time Workers code cannot depend on a local filesystem. Ingestion is
therefore a separate CLI (`scripts/ingest.py`) that reads `docs/*.md`, chunks
Markdown by headings, calls Cloudflare REST APIs, and upserts metadata-bearing
vectors. GitHub Actions runs this CLI automatically before deployment, so
committing documentation is enough to refresh the production index.

## Setup and deployment

```sh
npm install
uv venv && uv sync
npx wrangler vectorize create docpilot-docs --dimensions 768 --metric cosine
npx wrangler dev
```

The Vectorize dimensions must match the embedding model/index. Configure
`AI` and `VECTORIZE` in `wrangler.jsonc`; deploy with `npx wrangler deploy`.
Provide `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` only to the
ingestion environment (the token needs Workers AI and Vectorize write
permissions). The repository workflow supplies these values from GitHub
Secrets; they do not belong in the browser or repository.

## Ingestion

From `app/`, run:

```sh
python scripts/ingest.py --account-id "$CLOUDFLARE_ACCOUNT_ID" \
  --api-token "$CLOUDFLARE_API_TOKEN" --index docpilot-docs --docs docs
```

The script is intentionally stdlib-only and uses documented Cloudflare REST
endpoints. Re-run it after documentation changes. It hashes stable chunk IDs;
upsert is safe to repeat, but stale chunks should be removed when deleting
documents.

## Tests and production checklist

Run `python -m unittest discover -s tests`. Before production, add
authentication/rate limiting, redact sensitive logs, rotate API tokens, pin and
evaluate prompt/model versions, measure recall@k and answer faithfulness, and
monitor latency, errors, token cost, and Vectorize freshness. Treat retrieved
Markdown as untrusted input and keep the model instructed not to follow
instructions inside documents.

## Limitations

This v1 supports Markdown files and a single Vectorize index. It does not yet
delete stale vectors, enforce user authorization, stream responses, or provide
automated evaluation. Vectorize availability and embedding/index dimension
compatibility must be verified in the target Cloudflare account. Live browsing
currently accepts user-supplied public URLs only; it does not crawl an entire
site or search the open web. Browser Run availability, limits, and pricing
must be checked in the target Cloudflare account.
