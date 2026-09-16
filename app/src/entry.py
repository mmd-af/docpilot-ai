from workers import Response, WorkerEntrypoint
import json

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if request.method == "POST" and "/api/chat" in request.url:
            body = await request.json()
            user_message = body.get("message", "")

            result = await self.env.AI.run(
                "@cf/meta/llama-3.1-8b-instruct",
                {
                    "messages": [
                        {"role": "system", "content": "You are DocPilot AI, a helpful documentation assistant."},
                        {"role": "user", "content": user_message}
                    ]
                }
            )
            return Response(json.dumps({"response": result.response}), headers={"Content-Type": "application/json"})

        return Response("Not found", status=404)