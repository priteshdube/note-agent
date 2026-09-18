import asyncio
import os
import unittest
from pathlib import Path

from dotenv import load_dotenv

from models import LectureNotes
from providers.groq_provider import (
    GroqNotesProvider,
    GroqTranscriptionProvider,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TEST_AUDIO_FILE = os.getenv("TEST_AUDIO_FILE")


class GroqProviderIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        GROQ_API_KEY,
        "Set GROQ_API_KEY in .env to run the live notes-provider test",
    )
    def test_generate_notes(self):
        async def run_test():
            provider = GroqNotesProvider(GROQ_API_KEY)
            notes = await provider.generate_notes(
                "Python async functions use async and await to perform network "
                "operations without blocking the event loop."
            )

            self.assertIsInstance(notes, LectureNotes)
            self.assertTrue(notes.title)
            self.assertGreater(len(notes.sections), 0)
            self.assertGreater(len(notes.key_terms), 0)

        asyncio.run(run_test())

    @unittest.skipUnless(
        GROQ_API_KEY and TEST_AUDIO_FILE,
        "Set GROQ_API_KEY and TEST_AUDIO_FILE in .env to run the live transcription test",
    )
    def test_transcribe_audio(self):
        audio_path = PROJECT_ROOT / TEST_AUDIO_FILE
        self.assertTrue(audio_path.is_file(), f"Audio file not found: {audio_path}")

        async def run_test():
            provider = GroqTranscriptionProvider(GROQ_API_KEY)
            transcript = await provider.transcribe(
                audio_bytes=audio_path.read_bytes(),
                filename=audio_path.name,
            )

            self.assertIsInstance(transcript, str)
            self.assertTrue(transcript.strip())

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
