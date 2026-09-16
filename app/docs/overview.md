# DocPilot AI overview

DocPilot AI is a documentation assistant built with Cloudflare Workers.
The project uses Cloudflare Workers AI and the Google Gemma model for chat generation.
The application exposes a health endpoint at GET /health and a question endpoint at POST /api/chat.
The project is designed to answer questions using documentation context instead of guessing.
The long-term architecture includes ingestion, chunking, embeddings, and retrieval augmented generation.
The project should keep a clear separation between document loading, retrieval, and LLM prompting.

## AI engineering roadmap

The AI engineering roadmap starts with a working LLM app, then adds a documentation store.
Next steps include loading Markdown files, splitting them into chunks, generating embeddings, and storing vectors.
A retrieval step selects the most relevant chunks for a user question and sends them to the model as context.
The final answer should cite the source sections and state when the answer is not supported by the documents.
Production quality also requires monitoring, rate limiting, testing, and evaluation metrics.
