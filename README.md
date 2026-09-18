# DocPilot AI

DocPilot AI is an open-source documentation assistant built as an applied AI
engineering project. It is designed to answer questions from a controlled
documentation corpus rather than relying only on a language model's general
knowledge.

The project is intentionally being developed as a learning project and as a
portfolio-quality reference implementation. It demonstrates how a modern
retrieval-augmented generation (RAG) application is structured: documents are
ingested, split into useful sections, converted into embeddings, stored in a
vector database, retrieved for a user's question, and supplied to an LLM as
grounding context.

The current implementation uses Cloudflare Workers, Cloudflare Workers AI, and
Cloudflare Vectorize. The application is small enough to understand while
following the same architectural boundaries used in larger AI products.

## Why this project exists

An LLM can produce fluent answers without having access to a project's private
or changing documentation. That is useful for general conversation, but it is
not sufficient for a reliable documentation assistant. A production system
needs a way to connect answers to a known source of truth, reduce unsupported
answers, and show users where the answer came from.

DocPilot AI explores that problem from end to end. The goal is not to create
another generic chatbot. The goal is to demonstrate the engineering work around
an AI system:

- document ingestion and normalization;
- chunking and metadata design;
- embedding generation;
- vector search and retrieval;
- prompt construction and grounding;
- citations and answer traceability;
- testing and evaluation;
- observability, security, and operational limits.

## How it works

At request time, the application follows this flow:

```text
User
  |
  | POST /api/chat
  v
Cloudflare Worker
  |
  | 1. Validate the request
  | 2. Generate an embedding for the question
  v
Workers AI embedding model
  |
  | 3. Search for similar document chunks
  v
Cloudflare Vectorize
  |
  | 4. Return relevant text and metadata
  v
Grounded prompt
  |
  | 5. Generate an answer using retrieved context
  v
Workers AI chat model
  |
  v
Answer and source metadata
```

The document pipeline runs separately from the request path:

```text
Markdown files in app/docs/
  -> heading-aware chunking
  -> metadata such as source, section, and chunk ID
  -> Workers AI embeddings
  -> Cloudflare Vectorize
```

This separation is important. The running Worker should not read the
repository's local filesystem or re-process every document for every request.
Ingestion is an offline operation, while retrieval is a request-time operation.

## Current status

The project currently includes:

- a Python Cloudflare Worker;
- a static browser interface;
- `POST /api/chat`;
- `GET /health`;
- Cloudflare Workers AI chat generation;
- Markdown-aware chunking;
- an offline ingestion script;
- Workers AI embedding generation;
- Cloudflare Vectorize retrieval;
- grounded prompts;
- source metadata in API responses;
- unit tests for core RAG helpers;
- deployment and troubleshooting documentation.

The project is still evolving. The current RAG implementation is a focused
v1 intended to make the architecture understandable. It does not yet claim to
be a complete production service. Authentication, rate limiting, automated
evaluation, stale-vector cleanup, advanced observability, and a polished user
experience remain part of the hardening roadmap.

## Repository structure

```text
.
├── app/
│   ├── docs/                 # Markdown source documents
│   ├── public/               # Browser interface served as static assets
│   ├── scripts/
│   │   └── ingest.py         # Offline Markdown-to-Vectorize ingestion
│   ├── src/
│   │   ├── entry.py          # Worker routes and model orchestration
│   │   ├── rag.py            # Chunking, retrieval, prompts, and citations
│   │   └── submodule.py      # Starter project example
│   ├── tests/
│   │   └── test_rag.py       # Offline RAG unit tests
│   ├── pyproject.toml        # Python Workers development dependencies
│   ├── package.json          # Wrangler scripts and dependencies
│   └── wrangler.jsonc       # Worker, AI, Vectorize, and asset bindings
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI deployment workflow
├── Dockerfile                # Optional development container
└── docker-compose.yml        # Optional local container configuration
```

## Technology choices

### Cloudflare Workers

The Worker provides the HTTP API and static asset delivery without requiring a
traditional server. This keeps the first deployment simple and lets the
project focus on application and AI engineering rather than server
administration.

### Workers AI

Workers AI provides the embedding model used during ingestion and the chat
model used to generate answers. The current chat model is:

```text
@cf/google/gemma-4-26b-a4b-it
```

The embedding model is:

```text
@cf/baai/bge-base-en-v1.5
```

Model availability, limits, and pricing can change. Always check the current
Cloudflare documentation and account usage before treating the service as
free or unlimited.

### Cloudflare Vectorize

Vectorize stores document embeddings and their metadata. At request time, the
Worker embeds the user's question, performs a similarity search, and places
the most relevant chunks into the model prompt.

### Python

Python is used for the Worker and the ingestion logic because it is widely used
in AI engineering, data processing, evaluation, and backend systems. The
project deliberately keeps platform-specific code small and separates it from
the RAG logic.

## Local development

### Requirements

- Python 3.12 or newer;
- Node.js 16.17 or newer;
- npm;
- `uv`;
- a Cloudflare account for Workers AI and Vectorize development.

Install `uv` by following the official instructions:

<https://docs.astral.sh/uv/getting-started/installation/>

### Install dependencies

From the `app` directory:

```sh
cd app
uv venv
uv sync
npm install
```

### Run the Worker locally

```sh
cd app
uv run pywrangler dev
```

Wrangler may ask you to authenticate with Cloudflare. Workers AI requests made
during local development can use the Cloudflare account and may count toward
account usage.

The local application is normally available at:

```text
http://localhost:8787
```

Check the health endpoint:

```sh
curl http://localhost:8787/health
```

The expected response is:

```json
{"status": "ok"}
```

## Vectorize setup

The Worker expects a Vectorize index named `docpilot-docs` with dimensions
matching the embedding model. Create the index from the `app` directory:

```sh
npx wrangler vectorize create docpilot-docs \
  --dimensions 768 \
  --metric cosine
```

The deployment workflow also checks for this index and creates it
automatically when it is missing. The `CLOUDFLARE_API_TOKEN` used by GitHub
Actions therefore needs permission to manage Workers AI and Vectorize indexes,
not only to deploy Worker scripts. If the workflow cannot create the index,
create it once manually with the command above or grant the token the required
Vectorize permission.

The Worker binding is configured in `app/wrangler.jsonc`:

```jsonc
"ai": {
  "binding": "AI"
},
"vectorize": [
  {
    "binding": "VECTORIZE",
    "index_name": "docpilot-docs"
  }
]
```

## Ingest documentation

Markdown files under `app/docs/` are the source of truth. Add or update
documentation there, then run the ingestion script from the `app` directory:

```sh
python scripts/ingest.py \
  --account-id "$CLOUDFLARE_ACCOUNT_ID" \
  --api-token "$CLOUDFLARE_API_TOKEN" \
  --index docpilot-docs \
  --docs docs
```

On Windows PowerShell, use:

```powershell
python scripts/ingest.py `
  --account-id $env:CLOUDFLARE_ACCOUNT_ID `
  --api-token $env:CLOUDFLARE_API_TOKEN `
  --index docpilot-docs `
  --docs docs
```

The token should be provided through an environment variable or a secret
manager. Do not commit it to the repository. It needs permission to call
Workers AI and write to Vectorize.

In the GitHub Actions deployment workflow, this process runs automatically
after the index check and before the Worker deployment. Therefore, the normal
content workflow is: add or update a Markdown file under `app/docs/`, commit
it, and push to `main`. GitHub Actions then:

1. Finds Markdown files recursively.
2. Splits content at Markdown headings.
3. Creates bounded chunks with overlap.
4. Adds source, title, section, and stable chunk metadata.
5. Generates embeddings in batches.
6. Upserts vectors and metadata into Vectorize.

Re-run ingestion whenever documentation changes. The current version performs
safe upserts for stable chunk IDs, but stale vectors from deleted documents
still need an explicit cleanup workflow.

## API

### Health

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

### Chat

```http
POST /api/chat
Content-Type: application/json
```

Request:

```json
{
  "message": "How does document retrieval work?"
}
```

Successful response:

```json
{
  "response": "The answer generated from the retrieved documentation.",
  "sources": [
    {
      "source": "docs/overview.md",
      "title": "overview.md",
      "section": "How it works",
      "chunk_id": "..."
    }
  ]
}
```

The model is instructed to answer from retrieved documentation only. If the
retrieved context does not support an answer, it should say so rather than
inventing a response.

## Testing

Run the unit tests from the `app` directory:

```sh
python -m unittest discover -s tests -v
```

The current tests cover the deterministic parts of the system, including:

- Markdown heading and metadata preservation;
- chunking behavior;
- grounded prompt construction.

The next testing layer should use a fixed evaluation dataset containing
questions, expected source documents, and expected answer properties.

## Production engineering roadmap

The project is organized around the following progression:

### 1. Reliable baseline

Validate input, return explicit errors, expose health checks, and keep model
calls observable. This stage is implemented.

### 2. Document ingestion

Treat Markdown as a versioned source of truth, preserve metadata, make
ingestion repeatable, and track changes. The first version is implemented.

### 3. Retrieval-augmented generation

Use embeddings and vector search to select relevant context, then ground the
LLM response in those excerpts. The first Vectorize-backed version is
implemented.

### 4. Evaluation

Build a versioned question set and measure:

- retrieval recall@k;
- source-document accuracy;
- answer faithfulness;
- answer relevance;
- unsupported-answer rate;
- latency;
- token usage and cost.

### 5. Production hardening

Add authentication, rate limiting, abuse prevention, structured logging,
request tracing, secret rotation, stale-vector cleanup, model and prompt
versioning, and operational alerts.

### 6. Portability

After the Cloudflare implementation is understood and documented, the same
interfaces can be implemented on a VPS using a conventional API service,
PostgreSQL with pgvector, object storage, and an external or self-hosted model.
That should be a second deployment target, not a replacement for understanding
the current system.

## Security and operational notes

This application accepts public requests when deployed publicly. Before using
it as a production service:

- add authentication or an access policy;
- add rate limiting and request quotas;
- enforce message and context size limits;
- never expose API tokens in frontend code;
- keep ingestion credentials outside the repository;
- avoid logging document contents or user secrets;
- treat retrieved documents as untrusted input;
- instruct the model not to follow commands contained inside documents;
- monitor AI and Vectorize usage;
- review Cloudflare pricing and account limits.

RAG improves grounding, but it does not automatically make an application
secure or factually correct. Retrieval quality, document quality, prompt
design, and evaluation all matter.

## Contributing

Contributions should preserve the separation between:

- document source files;
- offline ingestion;
- request-time retrieval;
- prompt construction;
- model invocation;
- HTTP and presentation concerns.

When changing retrieval or prompting behavior, add or update a test and explain
the expected quality or behavior change. Do not commit credentials, generated
environment files, or local dependency directories.

## License

No license has been selected for this project yet. Until a license is added,
the repository should not be assumed to grant permission to reuse, modify, or
redistribute the code.
