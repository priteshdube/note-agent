import asyncio
import httpx
import json
from models import LectureNotes
from providers.base import VideoUrlNotesProvider


class GeminiVideoNotesProvider(VideoUrlNotesProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_notes_from_url(self, video_url: str) -> LectureNotes:
        prompt = """Watch this video and produce study notes. Respond with ONLY valid
JSON, no markdown fences, matching exactly:

{
  "title": "short descriptive title",
  "sections": [{ "heading": "...", "bullets": ["...", "..."] }],
  "key_terms": [{ "term": "...", "definition": "..." }]
}"""
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"file_data": {"mime_type": "video/*", "file_uri": video_url}},
                    ],
                }
            ]
        }
        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    resp = await client.post(
                        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
                        headers={
                            "x-goog-api-key": self.api_key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    if resp.status_code in {429, 500, 502, 503, 504}:
                        last_error = RuntimeError(f"Gemini transient error: {resp.status_code} {resp.text}")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                            continue
                    resp.raise_for_status()
                    data = resp.json()

                    text = None
                    for candidate in data.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            if isinstance(part, dict) and "text" in part:
                                text = part["text"]
                                break
                        if text is not None:
                            break

                    if text is None:
                        raise ValueError("Gemini response did not include a text part.")

                    # Gemini sometimes wraps JSON in ```json fences despite instructions — strip defensively
                    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = json.loads(text)
                    return LectureNotes(**parsed)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        if last_error is not None:
            raise last_error

        raise RuntimeError("Gemini request failed without a response.")