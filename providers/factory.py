"""
Factory for creating provider instances based on environment configuration.
"""
from config import settings
from providers.base import (
    TranscriptionProvider,
    NotesProvider,
    VideoUrlNotesProvider,
)
from providers.groq_provider import (
    GroqTranscriptionProvider,
    GroqNotesProvider,
)
from providers.gemini_provider import GeminiVideoNotesProvider


def get_transcription_provider() -> TranscriptionProvider:
    """Get the transcription provider based on TRANSCRIPTION_PROVIDER setting."""
    if settings.transcription_provider == "groq":
        return GroqTranscriptionProvider(api_key=settings.groq_api_key)
    # Future providers can be added here:
    # elif settings.transcription_provider == "other":
    #     return OtherTranscriptionProvider(api_key=settings.other_api_key)
    else:
        raise ValueError(
            f"Unknown transcription provider: {settings.transcription_provider}"
        )


def get_notegen_provider() -> NotesProvider:
    """Get the note generation provider based on NOTEGEN_PROVIDER setting."""
    if settings.notegen_provider == "groq":
        return GroqNotesProvider(api_key=settings.groq_api_key)
    # Future providers can be added here:
    # elif settings.notegen_provider == "other":
    #     return OtherNotesProvider(api_key=settings.other_api_key)
    else:
        raise ValueError(
            f"Unknown note generation provider: {settings.notegen_provider}"
        )


def get_video_url_provider() -> VideoUrlNotesProvider:
    """Get the video URL notes provider.

    Currently only Gemini is implemented for video URL processing.
    """
    return GeminiVideoNotesProvider(api_key=settings.gemini_api_key)