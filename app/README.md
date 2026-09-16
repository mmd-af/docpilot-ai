# DocPilot AI

DocPilot AI is a small Cloudflare Python Worker that provides a documentation
assistant over an HTTP API. The current milestone is a reliable LLM baseline;
retrieval-augmented generation (RAG) is the next milestone.

## Local development

You can run the Worker with `wrangler dev` in this directory. This starts a
local HTTP server and lets you iterate without restarting the Worker.

The project includes a `pyproject.toml` with the Cloudflare Workers runtime
types for editor autocomplete. Install `uv` from
https://docs.astral.sh/uv/getting-started/installation/, then run:

```sh
uv venv
uv sync
npm install
uv run pywrangler dev
```

Test the API:

```sh
curl -X POST http://localhost:8787/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How do I configure this project?"}'
```

The AI binding must be available in the Cloudflare account used for deployment.
Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` in GitHub Actions secrets.

## Engineering roadmap

1. **Baseline (current):** validate requests, call an LLM, return explicit errors,
   and expose `/health` for deployment checks.
2. **Ingestion:** load Markdown/PDF documentation, normalize it, chunk it with
   stable document and section metadata, and make ingestion repeatable.
3. **RAG:** generate embeddings, store vectors in Cloudflare Vectorize, retrieve
   top-k chunks, and include citations in every grounded answer.
4. **Evaluation:** add a versioned question set, retrieval metrics (recall@k),
   answer faithfulness checks, latency, and token/cost measurements.
5. **Production quality:** authentication and rate limiting, structured logs,
   tracing, prompt/version management, CI tests, and a documented threat model.

Keep retrieval, prompting, and model calls behind separate modules as RAG is
introduced. That separation makes the project easier to test and demonstrates
the core AI engineering skills this sample is intended to showcase.
