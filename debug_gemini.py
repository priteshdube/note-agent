import httpx
import json
import asyncio
from config import settings

async def debug():
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gemini-3.8-flash",
        "input": [
            {
                "type": "text",
                "text": "Watch this video and produce study notes. Respond with ONLY valid JSON, no markdown fences, matching exactly:\n\n{\n  \"title\": \"short descriptive title\",\n  \"sections\": [{ \"heading\": \"...\", \"bullets\": [\"...\", \"...\"] }],\n  \"key_terms\": [{ \"term\": \"...\", \"definition\": \"...\" }]\n}\n\nTranscript:\n\"\"\"This is a test.\"\"\"",
            },
            {
                "type": "video",
                "uri": "https://www.youtube.com/watch?v=vo6gQz5lYRI&list=PLKnIA16_RmvZo7fp5kkIth6nRTeQQsjfX&index=4",
            },
        ],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            print("Status:", resp.status_code)
            print("Response text:", resp.text)
            # Try to parse JSON
            data = resp.json()
            print("Parsed JSON:", json.dumps(data, indent=2))
        except Exception as e:
            print("Error:", e)
            if 'resp' in locals():
                print("Response status:", resp.status_code)
                print("Response text:", resp.text)

if __name__ == "__main__":
    asyncio.run(debug())