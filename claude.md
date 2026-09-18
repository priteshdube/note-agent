# Lecture Notes Backend — Project Context

## What this project does

A personal tool that turns lectures/tutorials into organized Notion notes automatically.
Two ingestion paths feed into the same note-generation and Notion-writing logic:

1. **Recorded audio path**: a Chrome extension records a browser tab's audio →
   uploads it to this backend → transcribed by Groq Whisper → summarized into
   structured notes by a Groq LLM → written to Notion.
2. **YouTube URL path**: user pastes a public YouTube link → sent to this backend →
   Gemini watches the video directly and produces structured notes in one call →
   written to Notion.

Both paths converge on the same `LectureNotes` Pydantic schema before hitting Notion,
so the Notion-writing code has no idea which path produced the notes.

## Tech stack

- **FastAPI** — backend framework, async throughout
- **uv** — package/environment manager (project-based: `pyproject.toml` + `uv.lock`,
  NOT `requirements.txt`). Use `uv add <pkg>` to add dependencies, `uv run <cmd>` to run
  anything inside the project's venv. Never manually create/activate a venv here.
- **httpx** — all outbound HTTP calls (Groq, Gemini, Notion), async client
- **Pydantic / pydantic-settings** — data contracts (`models.py`) and env config
  (`config.py`)
- **Groq API** — Whisper (`whisper-large-v3-turbo`) for transcription, Llama
  (`llama-3.3-70b-versatile`) for note generation from transcripts. Free tier.
- **Gemini API** — `gemini-3.5-flash`, used only for the YouTube-URL path (video
  understanding: pass a YouTube URL directly, no download/transcription step)
- **Notion API** — raw REST calls via httpx (no SDK), creates a topic page (if it
  doesn't exist) then a lecture sub-page nested under it
- **Chrome Extension (Manifest V3)** — thin client only. Records tab audio via
  `chrome.tabCapture` + an offscreen document (MV3 service workers can't hold a
  `MediaRecorder` alive on their own), or accepts a pasted YouTube URL. Uploads to this
  backend and displays status. Holds NO API keys — all secrets live server-side in
  this project's `.env`.

## Architecture principle: provider abstraction (model-agnostic by design)

All LLM/transcription calls go through abstract interfaces in `providers/base.py`:

- `TranscriptionProvider` — audio bytes → transcript text (currently: Groq)
- `NoteGenProvider` — transcript text → `LectureNotes` (currently: Groq)
- `VideoUrlNotesProvider` — YouTube URL → `LectureNotes` directly (currently: Gemini,
  since Groq has no video-URL ingestion capability)

Concrete implementations live in `providers/<name>_provider.py` and are wired up via
`providers/factory.py`, which reads `.env` (`TRANSCRIPTION_PROVIDER`,
`NOTEGEN_PROVIDER`) to decide which class to instantiate. Route handlers and business
logic NEVER import a concrete provider directly — always go through the factory
functions (`get_transcription_provider()`, `get_notegen_provider()`,
`get_video_url_provider()`).

**When adding a new model/provider:** implement the relevant abstract base class in a
new `providers/<name>_provider.py` file, add one branch to the matching factory
function, and add a new env var option. Nothing else in the codebase should need to
change — if it does, the abstraction has leaked and should be reconsidered.

## Data contracts (`models.py`)

- `LectureNotes` — the universal output shape every provider must produce:
  `title`, `sections` (list of `{heading, bullets}`), `key_terms` (list of
  `{term, definition}`)
- `ProcessResponse` — API response wrapper: `status`, `notes`, `notion_page_url`

Both ingestion paths are required to return `LectureNotes` — this is what lets the
Notion-writing code stay ingestion-agnostic.

## Project layout

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
└── pyproject.toml / uv.lock
```

## Environment variables (`.env`)

```
TRANSCRIPTION_PROVIDER=groq
NOTEGEN_PROVIDER=groq
GROQ_API_KEY=...
GEMINI_API_KEY=...
NOTION_TOKEN=...
NOTION_ROOT_PAGE_ID=...
```

## Notion setup notes (easy to forget, causes "Object not found" errors)

The Notion integration must be explicitly connected to the root page via the page's
"•••" menu → Connections → add the integration — creating the integration alone is not
enough. `NOTION_ROOT_PAGE_ID` is the 32-character ID from the page's URL, not the page
name or the full URL.

## Testing conventions

- Test every provider standalone with a one-off `uv run python -c "..."` script before
  wiring it into a route — isolates whether a bug is in the provider, the route, or the
  extension.
- Test the FastAPI routes with `curl` or the auto-generated `/docs` (Swagger UI) before
  touching the extension. The extension should be the last thing tested, once the
  backend is confirmed working end-to-end.

## Known constraints

- Groq free tier: ~25MB per audio file for Whisper, 30 req/min, 6,000 tokens/min. Long
  lectures may need audio chunking (not yet implemented) or rolling summarization for
  the notegen step if transcripts get long.
- Gemini free tier: YouTube video ingestion capped at ~8 hours of video per day.
  YouTube-URL path only works for public videos, not private/unlisted ones.
- Notion's `children` array on page creation is capped at 100 blocks — very long note
  sets need a follow-up `PATCH /v1/blocks/{page_id}/children` call to append the rest
  (not yet implemented).

## Current status

Backend scaffolding, config, and models done. Groq provider (transcription + notegen)
implemented and tested standalone. Gemini video-URL provider implemented, pending
standalone test. Notion client implemented. Routes not yet wired end-to-end. Extension
still uses the old direct-to-provider approach from an earlier iteration and needs to
be updated to call this backend instead — DO NOT re-add API keys to the extension when
doing this.