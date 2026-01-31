import httpx
import os
import json
# from groq import Groq;


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# client = Groq(api_key=GROQ_API_KEY)

async def call_ai(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post("https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
            },)

        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def stream_ai(prompt: str):
    async with httpx.AsyncClient() as client:

        async with client.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-oss-120b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            },
        ) as response:
            # 🔴 Handle HTTP errors first
            if response.status_code != 200:
                body = await response.aread()
                raise RuntimeError(
                    f"Groq API error {response.status_code}: {body.decode()}"
                )

            async for line in response.aiter_lines():
                if not line:
                    continue

                # Stop condition
                if line.strip() == "data: [DONE]":
                    yield "\n"
                    break

                # # Remove SSE prefix
                if not line.startswith("data: "):
                    continue

                payload = json.loads(line.replace("data: ", ""))
                
                choices = payload.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})

                # ✅ ONLY send assistant content (not reasoning)
                content = delta.get("content")
                if content:
                    yield content