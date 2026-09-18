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
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                headers={
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gemini-3.8-flash",
                    "input": [
                        {
                            "type": "text",
                            "text": prompt,
                        },
                        {
                            "type": "video",
                            "uri": video_url,
                        },
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Extract the text from the model_output step
            text = None
            for step in data.get("steps", []):
                if step.get("type") == "model_output":
                    for part in step.get("content", []):
                        if part.get("type") == "text":
                            text = part.get("text")
                            break
                if text is not None:
                    break
            if text is None:
                # Fallback: try the old format (in case the API changes back)
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Gemini sometimes wraps JSON in ```json fences despite instructions — strip defensively
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(text)
            return LectureNotes(**parsed)