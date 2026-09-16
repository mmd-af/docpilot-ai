import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint


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

            result = await self.env.AI.run(
                "@cf/meta/llama-3.1-8b-instruct",
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
                    ]
                },
            )
            response = result.get("response") if isinstance(result, dict) else None
            if not isinstance(response, str):
                return self._json({"error": "The model returned an invalid response."}, 502)
            return self._json({"response": response})

        if request.method == "GET" and path.endswith("/health"):
            return self._json({"status": "ok"})

        return Response("Not found", status=404)

    @staticmethod
    def _json(payload, status=200):
        return Response(
            json.dumps(payload),
            status=status,
            headers={"Content-Type": "application/json"},
        )