import json
import logging
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

logger = logging.getLogger("docpilot")
MODEL = "@cf/google/gemma-4-26b-a4b-it"


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path.rstrip("/")
        if request.method == "POST" and path.endswith("/api/chat"):
            try:
                body = await request.json()
            except (TypeError, ValueError):
                return self._json({"error": "Request body must be valid JSON."}, 400)

            user_message = body.get("message") if isinstance(body, dict) else None
            if not isinstance(user_message, str) or not user_message.strip():
                return self._json({"error": "The 'message' field must be a non-empty string."}, 400)
            if len(user_message) > 8_000:
                return self._json({"error": "The 'message' field is too long."}, 413)

            try:
                result = await self.env.AI.run(
                    MODEL,
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are DocPilot AI, a helpful documentation assistant. "
                                    "If the answer is not supported by the provided context, say so."
                                ),
                            },
                            {"role": "user", "content": user_message.strip()},
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
            return self._json({"response": response})

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
                message = choices[0].get("message")
                if isinstance(message, dict):
                    return message.get("content")

        response = getattr(result, "response", None)
        return response if isinstance(response, str) else None