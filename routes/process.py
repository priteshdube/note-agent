from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from models import LectureNotes, ProcessResponse
from notion_client import find_or_create_topic_page, create_lecture_page
from providers.factory import get_transcription_provider, get_notegen_provider, get_video_url_provider

router = APIRouter()

# Configuration
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm"}
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

def _validate_audio_file(upload_file: UploadFile) -> None:
    """Validate uploaded audio file: extension and size (approx)."""
    if upload_file.filename:
        ext = "." + upload_file.filename.lower().split(".")[-1] if "." in upload_file.filename else ""
        if ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{ext}'. Allowed audio types: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
            )
    # Note: actual size check will be done after reading bytes; we also could check headers but skip for simplicity.

@router.post("/process-lecture", response_model=ProcessResponse)
async def process_lecture(
    audio_file: UploadFile = File(...),
    topic_name: str = Form(...),
):
    """
    Process an audio file: transcribe, generate notes, and write to Notion.
    """
    try:
        _validate_audio_file(audio_file)
        # Read the audio file
        audio_bytes = await audio_file.read()
        # Enforce size limit after reading (could also check Content-Length header)
        if len(audio_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB.",
            )
        filename = audio_file.filename or "audio.mp3"

        # Get providers
        transcription_provider = get_transcription_provider()
        notegen_provider = get_notegen_provider()

        # Transcribe
        transcript = await transcription_provider.transcribe(audio_bytes, filename)

        # Generate notes
        notes = await notegen_provider.generate_notes(transcript)

        # Find or create topic page in Notion
        topic_page_id = await find_or_create_topic_page(topic_name)

        # Create lecture page under the topic page
        notion_page_url = await create_lecture_page(topic_page_id, notes)
        # Notion page URL format: https://www.notion.so/{workspace_id}/{page_id_without_dashes}
        # We'll construct it from the page ID (which is a string with dashes)
        notion_page_url = f"https://www.notion.so/{notion_page_url.replace('-', '')}"

        return ProcessResponse(
            status="success",
            notes=notes,
            notion_page_url=notion_page_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Log the exception here if desired
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/process-youtube", response_model=ProcessResponse)
async def process_youtube(
    youtube_url: str = Form(...),
    topic_name: str = Form(...),
):
    """
    Process a YouTube URL: generate notes directly from the URL and write to Notion.
    """
    try:
        # Basic URL validation
        if not youtube_url.startswith("http"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid YouTube URL. Must start with http or https.",
            )
        # Get video URL provider
        video_provider = get_video_url_provider()

        # Generate notes from YouTube URL
        notes = await video_provider.generate_notes_from_url(youtube_url)

        # Find or create topic page in Notion
        topic_page_id = await find_or_create_topic_page(topic_name)

        # Create lecture page under the topic page
        notion_page_url = await create_lecture_page(topic_page_id, notes)
        notion_page_url = f"https://www.notion.so/{notion_page_url.replace('-', '')}"

        return ProcessResponse(
            status="success",
            notes=notes,
            notion_page_url=notion_page_url,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))