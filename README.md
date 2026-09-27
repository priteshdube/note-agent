# Lecture Notes Backend

A personal tool that turns lectures/tutorials into organized Notion notes automatically.
Two ingestion paths feed into the same note-generation and Notion-writing logic:

1. **Recorded audio path**: Records browser tab audio → uploads to backend → transcribed by Groq Whisper → summarized into structured notes by a Groq LLM → written to Notion.
2. **YouTube URL path**: User pastes a public YouTube link → sent to backend → Gemini watches the video directly and produces structured notes in one call → written to Notion.

Both paths converge on the same `LectureNotes` Pydantic schema before hitting Notion, so the Notion-writing code has no idea which path produced the notes.

## Tech Stack

- **FastAPI** — backend framework, async throughout
- **uv** — package/environment manager (`pyproject.toml` + `uv.lock`, NOT `requirements.txt`)
- **httpx** — all outbound HTTP calls (Groq, Gemini, Notion), async client
- **Pydantic / pydantic-settings** — data contracts (`models.py`) and env config (`config.py`)
- **Groq API** — Whisper (`whisper-large-v3-turbo`) for transcription, Llama (`llama-3.3-70b-versatile`) for note generation
- **Gemini API** — `gemini-3.5-flash`, used only for the YouTube-URL path
- **Notion API** — raw REST calls via httpx (no SDK)
- **Chrome Extension (Manifest V3)** — thin client (see [Extension](#extension-notes))

## Architecture: Provider Abstraction

All LLM/transcription calls go through abstract interfaces in `providers/base.py`:

- `TranscriptionProvider` — audio bytes → transcript text (currently: Groq)
- `NoteGenProvider` — transcript text → `LectureNotes` (currently: Groq)
- `VideoUrlNotesProvider` — YouTube URL → `LectureNotes` directly (currently: Gemini)

Concrete implementations live in `providers/<name>_provider.py` and are wired up via `providers/factory.py`, which reads `.env` (`TRANSCRIPTION_PROVIDER`, `NOTEGEN_PROVIDER`) to decide which class to instantiate. Route handlers and business logic **never** import a concrete provider directly — always go through the factory functions (`get_transcription_provider()`, `get_notegen_provider()`, `get_video_url_provider()`).

When adding a new model/provider:
1. Implement the relevant abstract base class in a new `providers/<name>_provider.py` file
2. Add one branch to the matching factory function
3. Add a new env var option
Nothing else in the codebase should need to change — if it does, the abstraction has leaked and should be reconsidered.

## Data Contracts (`models.py`)

- `LectureNotes` — universal output shape every provider must produce:
  - `title`: string
  - `sections`: list of `{heading: string, bullets: list[string]}`
  - `key_terms`: list of `{term: string, definition: string}`
- `ProcessResponse` — API response wrapper: `status`, `notes` (`LectureNotes`), `notion_page_url`: string?

## Project Layout

```
lecture-notes-backend/
├── main.py                  # FastAPI app, CORS middleware, router registration
├── config.py                # pydantic-settings, reads .env
├── models.py                # Pydantic schemas (LectureNotes, ProcessResponse, etc.)
├── notion_client.py         # find_or_create_topic_page, create_lecture_page
├── providers/
│   ├── base.py               # abstract interfaces
│   ├── groq_provider.py      # GroqTranscription, GroqNoteGen
│   ├── gemini_provider.py    # GeminiVideoNotes
│   └── factory.py            # env-driven provider selection
├── routes/
│   └── process.py            # POST /process-lecture (audio), POST /process-youtube (URL)
├── .env                      # secrets — NEVER commit
├── pyproject.toml / uv.lock
└── README.md
```

## Environment Variables (`.env`)

Create a `.env` file in the project root with the following:

```env
TRANSCRIPTION_PROVIDER=groq
NOTEGEN_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
NOTION_TOKEN=your_notion_integration_token_here
NOTION_ROOT_PAGE_ID=your_notion_root_page_id_here  # 32-character ID from the page's URL
API_KEY=optional_api_key_for_endpoint_protection  # if set, requires X-API-Key header
```

> **Notion Setup Notes**: The Notion integration must be explicitly connected to the root page via the page's "•••" menu → Connections → add the integration. Creating the integration alone is not enough. `NOTION_ROOT_PAGE_ID` is the 32-character ID from the page's URL, not the page name or the full URL.

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lecture-notes-backend
   ```

2. **Install dependencies using uv**
   ```bash
   uv sync  # installs dependencies into .venv and creates a virtual environment
   ```

3. **Create `.env` file**
   - Copy the example above and fill in your actual keys and IDs.
   - **Never commit `.env` to version control**.

4. **Activate the virtual environment (if needed)**
   ```bash
   source .venv/bin/activate  # on Unix/macOS
   .\.venv\Scripts\activate   # on Windows
   ```

## Running the Backend

```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

## API Endpoints

Both endpoints require authentication if `API_KEY` is set in `.env` (provide `X-API-Key` header).

### Process Lecture (Audio)
```
POST /api/process-lecture
```

**Form Data**
- `audio_file`: file (multipart/form-data) — supported extensions: .mp3, .wav, .ogg, .m4a, .flac, .webm
- `topic_name`: string — name of the topic under which to create/not find a Notion page

**Returns**
```json
{
  "status": "success",
  "notes": {
    "title": "string",
    "sections": [{"heading": "string", "bullets": ["string", ...]}, ...],
    "key_terms": [{"term": "string", "definition": "string"}, ...]
  },
  "notion_page_url": "string or null"
}
```

### Process YouTube
```
POST /api/process-youtube
```

**Form Data**
- `youtube_url`: string — must start with http/https
- `topic_name`: string — name of the topic under which to create/not find a Notion page

**Returns**
Same structure as `/api/process-lecture`.

## Extension Notes

The Chrome Extension (Manifest V3) is a separate project. It should:
- Record tab audio via `chrome.tabCapture` + an offscreen document (since MV3 service workers can't hold a `MediaRecorder` alive)
- Accept a pasted YouTube URL
- Upload to this backend's `/api/process-lecture` (audio) or `/api/process-youtube` (YouTube) endpoints
- Display status to the user
- **Hold NO API keys** — all secrets live server-side in this project's `.env`

> ⚠️ The extension still uses the old direct-to-provider approach from an earlier iteration and needs to be updated to call this backend instead. **Do not re-add API keys to the extension** when doing this.

## Known Constraints

- **Groq free tier**: ~25MB per audio file for Whisper, 30 req/min, 6,000 tokens/min. Long lectures may need audio chunking or rolling summarization (not yet implemented).
- **Gemini free tier**: YouTube video ingestion capped at ~8 hours of video per day. YouTube-URL path only works for public videos, not private/unlisted ones.
- **Notion's `children` array limit**: Capped at 100 blocks per page creation call. Very long note sets need a follow-up `PATCH /v1/blocks/{page_id}/children` call to append the rest (not yet implemented).

## Testing Conventions

- Test every provider standalone with a one-off `uv run python -c "..."` script before wiring it into a route — isolates whether a bug is in the provider, the route, or the extension.
- Test the FastAPI routes with `curl` or the auto-generated `/docs` (Swagger UI) before touching the extension. The extension should be the last thing tested, once the backend is confirmed working end-to-end.

## Current Status

- Backend scaffolding, config, and models done.
- Groq provider (transcription + notegen) implemented and tested standalone.
- Gemini video-URL provider implemented, pending standalone test.
- Notion client implemented.
- Routes wired end-to-end and tested.
- Extension still uses the old direct-to-provider approach and needs updating.

---

**Made with ❤️ for turning lectures into actionable notes.**