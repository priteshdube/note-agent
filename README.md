# Lecture Notes Assistant

Lecture Notes Assistant is a local FastAPI backend and Chrome extension that turns learning content into organized Notion notes.

It has two workflows:

- **YouTube:** paste a public YouTube URL. Gemini analyzes the video and creates structured notes.
- **Recorded audio:** record audio from the active browser tab. Groq transcribes the audio, generates notes, and sends them to Notion.

Both workflows create a Notion topic page when necessary and then create a lecture page beneath it.

## How It Works

The Chrome extension is only a client. It does not store API keys. It sends requests to the local backend at `http://localhost:8000`.

For YouTube processing:

1. The extension sends the YouTube URL and topic name to `POST /api/process-youtube`.
2. The backend sends the public video URL to Gemini.
3. Gemini returns a title, sections, bullet points, and key terms.
4. The backend creates the corresponding pages in Notion.
5. The extension opens the generated Notion page when processing succeeds.

For audio processing, the backend uses Groq for transcription and note generation before writing the result to Notion.

## Requirements

Install the following before setting up the project:

- macOS, Linux, or Windows
- Python 3.13 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Google Chrome or another Chromium-based browser
- A Gemini API key
- A Notion integration and a Notion root page
- A Groq API key if you plan to use audio recording

## Local Setup

Run these commands from the project root:

```bash
uv sync
```

Create a file named `.env` in the project root. Do not commit this file or put these values in the Chrome extension.

```env
TRANSCRIPTION_PROVIDER=groq
NOTEGEN_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
NOTION_TOKEN=your_notion_integration_token
NOTION_ROOT_PAGE_ID=your_notion_root_page_id
```

`GROQ_API_KEY` is needed for the audio workflow. `GEMINI_API_KEY` is needed for the YouTube workflow. The backend currently expects all required settings to exist when it starts.

### Create The Notion Integration

1. Create an internal integration in Notion and copy its token into `NOTION_TOKEN`.
2. Create or choose the page that should contain your generated notes.
3. Open that page's **Connections** menu and connect the integration.
4. Copy the root page ID from the Notion page URL into `NOTION_ROOT_PAGE_ID`.

The root page ID is the long identifier in the page URL. It may be displayed with or without hyphens. Do not use the page title or the complete URL.

If the integration is not connected to the root page, Notion will usually return an `object_not_found` or permissions error.

## Start The Backend

Start the local API server:

```bash
uv run uvicorn main:app --reload
```

The backend runs at `http://localhost:8000`. Verify it before testing the extension:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"healthy"}
```

You can also open `http://localhost:8000/docs` to view and test the FastAPI endpoints in Swagger UI.

If port 8000 is already in use, first open the health URL. The backend may already be running, so you do not need to start a second server.

## Load The Chrome Extension

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select this project's `extension` folder, not the project root.
5. Click the extension's reload button whenever you change extension files.
6. Pin the extension to the Chrome toolbar for easier access.

The extension popup contains controls for YouTube processing and tab-audio recording. The extension does not need the Gemini, Groq, or Notion keys because those are used only by the backend.

## Test The YouTube Workflow

YouTube is the easiest workflow to test because it does not require browser audio capture.

1. Make sure the backend is running and `/health` returns `{"status":"healthy"}`.
2. Reload the unpacked extension in `chrome://extensions`.
3. Open the extension popup.
4. Enter a topic name, for example `Operating Systems`.
5. Paste a public YouTube URL.
6. Click **Process YouTube Video**.
7. Wait while Gemini analyzes the video and Notion creates the pages.

The topic name is required by the backend. Use a public video that Gemini can access; private, restricted, or unavailable videos may fail.

The request is sent as multipart form data:

```text
POST http://localhost:8000/api/process-youtube
youtube_url=<public YouTube URL>
topic_name=<Notion topic name>
```

On success, the extension displays a success message and opens the generated Notion page.

## Test The Audio Workflow

1. Open a browser tab that is playing a short lecture or other audio.
2. Open the extension popup and enter a topic name.
3. Click **Start Recording**.
4. Play the content you want to capture.
5. Click **Stop Recording**.
6. Wait for Groq transcription, note generation, and Notion creation to finish.

The extension records the active tab using Chrome's `tabCapture` permission. Very long recordings may exceed provider file-size or rate limits. Start with a short clip while testing.

## Troubleshooting

### The popup buttons do nothing

Reload the extension from `chrome://extensions`. Confirm that `extension/popup.html` loads `popup.js`. To inspect JavaScript errors, open the extension details and select **Inspect views** for the popup or service worker.

### Backend error 422

The request is missing a required form field. For YouTube, enter both a public URL and a topic name. The backend requires both `youtube_url` and `topic_name`.

### Backend error 401

This means backend API-key protection is enabled. The current local extension does not send an `X-API-Key` header. Remove `API_KEY` from `.env` for local testing, or update the extension and backend configuration together before enabling that protection.

### Backend error 500

Read the Uvicorn terminal output for the detailed exception. Common causes are an invalid Gemini key, an unavailable video, missing Notion credentials, or Notion permissions.

### Notion says the object was not found

Check that `NOTION_ROOT_PAGE_ID` is correct and that the Notion integration is connected to the root page through **Connections**. Creating an integration alone does not grant it access to pages.

### The request stays on "Sending YouTube URL to backend"

Confirm that `http://localhost:8000/health` responds. Then inspect the service worker console for the extension and the terminal running Uvicorn. The backend may be waiting for Gemini or Notion, or it may have returned an error that is shown in the console.

## API Endpoints

| Endpoint | Purpose | Required fields |
| --- | --- | --- |
| `GET /health` | Check that the backend is running | None |
| `POST /api/process-youtube` | Generate notes from a YouTube URL | `youtube_url`, `topic_name` |
| `POST /api/process-lecture` | Generate notes from an audio upload | `audio_file`, `topic_name` |

Both processing endpoints return a `ProcessResponse` containing the processing status, generated `LectureNotes`, and the Notion page URL.

## Project Structure

```text
main.py                  FastAPI application and middleware
config.py                Environment settings
models.py                Pydantic request and response models
routes/process.py        YouTube and audio endpoints
providers/base.py        Provider interfaces
providers/gemini_provider.py  YouTube note generation
providers/groq_provider.py     Audio transcription and note generation
providers/factory.py     Provider selection
notion_client.py         Notion page creation
extension/               Chrome Manifest V3 extension
tests/                   Backend tests
```

Keep API keys in `.env` only. The Chrome extension should remain a thin client that communicates with the backend.