import json
import logging
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from browsing import build_live_prompt, retrieve_web_sources
from rag import build_grounded_prompt, retrieve

logger = logging.getLogger("docpilot")
MODEL = "@cf/google/gemma-4-26b-a4b-it"


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path.rstrip("/")
        if request.method == "POST" and path.endswith(("/api/chat", "/api/live-chat")):
            try:
                body = await request.json()
            except (TypeError, ValueError):
                return self._json({"error": "Request body must be valid JSON."}, 400)

            user_message = body.get("message") if isinstance(body, dict) else None
            if not isinstance(user_message, str) or not user_message.strip():
                return self._json({"error": "The 'message' field must be a non-empty string."}, 400)
            if len(user_message) > 8_000:
                return self._json({"error": "The 'message' field is too long."}, 413)

            if path.endswith("/api/live-chat"):
                try:
                    sources, failed_urls = await retrieve_web_sources(
                        self.env.BROWSER, body.get("urls")
                    )
                except ValueError as error:
                    return self._json({"error": str(error)}, 400)
                except Exception as error:
                    request_id = request.headers.get("cf-ray", "unknown")
                    logger.exception(
                        "Live website retrieval failed: request_id=%s error=%s",
                        request_id,
                        error,
                    )
                    return self._json(
                        {
                            "error": (
                                "A website could not be read. The site may be blocking "
                                "automated access or may be temporarily unavailable."
                            ),
                            "request_id": request_id,
                        },
                        502,
                    )
                prompt = build_live_prompt(user_message, sources)
                response_sources = [
                    {"url": source.url, "title": source.title}
                    for source in sources
                ]
                if failed_urls:
                    response_sources.extend(
                        {"url": url, "error": "This URL could not be read."}
                        for url in failed_urls
                    )
            else:
                prompt = None
                response_sources = None

            if prompt is None:
                try:
                    citations = await retrieve(self.env, user_message.strip())
                except Exception as error:
                    request_id = request.headers.get("cf-ray", "unknown")
                    logger.exception(
                        "RAG retrieval failed: request_id=%s error=%s", request_id, error
                    )
                    return self._json(
                        {
                            "error": "Documentation retrieval could not complete this request.",
                            "request_id": request_id,
                        },
                        502,
                    )
                prompt = build_grounded_prompt(user_message, citations)
                response_sources = [
                    {
                        "source": citation.source,
                        "title": citation.title,
                        "section": citation.section,
                        "chunk_id": citation.chunk_id,
                    }
                    for citation in citations
                ]
            try:
                result = await self.env.AI.run(
                    MODEL,
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are DocPilot AI, a helpful documentation assistant. "
                                    "Answer only from the provided documentation context."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "chat_template_kwargs": {"enable_thinking": False},
                    },
                )
            except Exception as error:
                request_id = request.headers.get("cf-ray", "unknown")
                logger.exception(
                    "Workers AI request failed: model=%s request_id=%s error=%s",
                    MODEL,
                    request_id,
                    error,
                )
                return self._json(
                    {
                        "error": "Workers AI could not complete this request.",
                        "request_id": request_id,
                    },
                    502,
                )

            response = self._model_response_text(result)
            if not isinstance(response, str):
                return self._json({"error": "The model returned an invalid response."}, 502)
            return self._json({
                "response": response,
                "sources": response_sources,
            })

        if request.method == "GET" and path.endswith("/health"):
            return self._json({"status": "ok"})

        if request.method == "GET":
            return await self.env.ASSETS.fetch(request)

        return Response("Not found", status=404)

    @staticmethod
    def _json(payload, status=200):
        return Response(
            json.dumps(payload),
            status=status,
            headers={"Content-Type": "application/json"},
        )

    @staticmethod
    def _model_response_text(result):
        if isinstance(result, dict):
            response = result.get("response")
            if isinstance(response, str):
                return response

            choices = result.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    message = first_choice.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            return content

        response = getattr(result, "response", None)
        if isinstance(response, str):
            return response
        return None