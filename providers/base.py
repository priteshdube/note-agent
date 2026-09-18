from abc import ABC, abstractmethod

from models import LectureNotes

class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        ...


class NotesProvider(ABC):
    @abstractmethod
    async def generate_notes(self, transcript: str) -> LectureNotes:
        """Return structured lecture notes generated from ``transcript``."""
        ...


class VideoUrlNotesProvider(ABC):
    @abstractmethod
    async def generate_notes_from_url(self, video_url:str)-> LectureNotes:
        """Return structured lecture notes generated from ``video_url``."""
        ...
