import io
import json
import httpx
from models import LectureNotes
from providers.base import NotesProvider, TranscriptionProvider

try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    PYDUB_AVAILABLE = True
except Exception:  # pydub or its dependencies not available
    PYDUB_AVAILABLE = False


class GroqTranscriptionProvider(TranscriptionProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        # If audio is small enough, transcribe directly
        MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB (leaving buffer for 25 MB limit)
        if len(audio_bytes) <= MAX_SIZE_BYTES:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": (filename, audio_bytes)},
                    data={"model": "whisper-large-v3-turbo", "response_format": "text"},
                )
                resp.raise_for_status()
                return resp.text

        # Audio is too large, need to chunk
        if not PYDUB_AVAILABLE:
            raise RuntimeError(
                "Audio chunking requires pydub. Please install it with `uv add pydub` "
                "and ensure ffmpeg is available in your system."
            )

        # Guess audio format from filename
        ext = "mp3"  # default
        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()

        # Load audio segment from bytes
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=ext)

        # Compute bytes per second to determine safe chunk duration
        bytes_per_second = (
            audio_segment.frame_rate
            * audio_segment.channels
            * audio_segment.sample_width
        )
        if bytes_per_second == 0:
            # Fallback to fixed duration if we cannot compute
            chunk_length_ms = 30 * 1000  # 30 seconds
        else:
            # Target chunk size: 18 MB to be safe
            target_chunk_bytes = 18 * 1024 * 1024
            chunk_length_ms = int((target_chunk_bytes / bytes_per_second) * 1000)
            # Ensure at least 1 second and at most 60 seconds
            chunk_length_ms = max(1000, min(chunk_length_ms, 60 * 1000))

        # Split audio into chunks of chunk_length_ms milliseconds
        chunks = [
            audio_segment[i : i + chunk_length_ms]
            for i in range(0, len(audio_segment), chunk_length_ms)
        ]

        # Transcribe each chunk
        transcripts = []
        for i, chunk in enumerate(chunks):
            # Skip empty chunks
            if len(chunk) == 0:
                continue
            # Export chunk to bytes
            out_io = io.BytesIO()
            chunk.export(out_io, format=ext)
            chunk_bytes = out_io.getvalue()

            # Transcribe this chunk
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": (f"chunk_{i}.{ext}", chunk_bytes)},
                    data={"model": "whisper-large-v3-turbo", "response_format": "text"},
                )
                resp.raise_for_status()
                transcript = resp.text
                transcripts.append(transcript)

        # Combine transcripts with a space (or newline) between chunks
        return " ".join(transcripts).strip()


class GroqNotesProvider(NotesProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_notes(self, transcript: str) -> LectureNotes:
        prompt = f"""You are a note-taking assistant. Read the transcript and produce
study notes. Respond with ONLY valid JSON, no markdown fences, matching exactly:

{{
  "title": "short descriptive title",
  "sections": [{{ "heading": "...", "bullets": ["...", "..."] }}],
  "key_terms": [{{ "term": "...", "definition": "..." }}]
}}

Transcript:
\"\"\"{transcript}\"\"\""""

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            data = json.loads(content)
            return LectureNotes(**data)