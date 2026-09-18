import asyncio
from config import settings
from providers.factory import get_transcription_provider, get_notegen_provider, get_video_url_provider
from notion_client import find_or_create_topic_page, create_lecture_page
from models import LectureNotes

async def test_groq_notes():
    print("Testing Groq provider (transcription + note generation) with dummy transcript...")
    # We don't have an audio file, so we skip transcription and directly test note generation.
    # But to test the full flow, we need an audio file. We'll skip transcription test for now.
    # Instead, we test the note generation provider directly.
    notegen_provider = get_notegen_provider()
    dummy_transcript = """
    This is a dummy transcript for testing purposes.
    We will discuss the importance of unit testing in software development.
    Unit testing helps to ensure that each part of the program works correctly.
    It also helps to catch bugs early in the development process.
    """
    print("Generating notes from dummy transcript...")
    notes = await notegen_provider.generate_notes(dummy_transcript)
    print(f"Generated notes: {notes.json()}")
    return notes

async def test_gemini_notes(youtube_url: str):
    print(f"Testing Gemini provider with YouTube URL: {youtube_url}")
    video_provider = get_video_url_provider()
    print("Generating notes from YouTube URL...")
    notes = await video_provider.generate_notes_from_url(youtube_url)
    print(f"Generated notes: {notes.json()}")
    return notes

async def create_notion_page(topic_name: str, notes: LectureNotes, source: str):
    print(f"Creating Notion page for topic: {topic_name} (source: {source})")
    # Find or create topic page
    topic_page_id = await find_or_create_topic_page(topic_name)
    print(f"Topic page ID: {topic_page_id}")
    # Create lecture page under the topic page
    notion_page_url = await create_lecture_page(topic_page_id, notes)
    # Construct the full Notion URL
    full_url = f"https://www.notion.so/{notion_page_url.replace('-', '')}"
    print(f"Lecture page created at: {full_url}")
    return full_url

async def main():
    # Test Groq note generation (without transcription)
    groq_notes = await test_groq_notes()
    # Test Gemini note generation (requires valid API key and YouTube URL)
    # We'll use a public YouTube video. If the API key is not set, this will fail.
    youtube_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # First YouTube video, 19 seconds
    try:
        gemini_notes = await test_gemini_notes(youtube_url)
    except Exception as e:
        print(f"Gemini provider failed (likely due to missing or invalid API key): {e}")
        print("Skipping Gemini test.")
        gemini_notes = None

    # Create Notion pages for each successful note generation
    if groq_notes:
        await create_notion_page("Groq Test Lecture", groq_notes, "Groq (dummy transcript)")
    if gemini_notes:
        await create_notion_page("Gemini Test Lecture", gemini_notes, "Gemini (YouTube)")

if __name__ == "__main__":
    asyncio.run(main())