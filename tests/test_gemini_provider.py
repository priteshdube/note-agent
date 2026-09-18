import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from models import LectureNotes
from providers.gemini_provider import GeminiVideoNotesProvider


class GeminiProviderTest(unittest.TestCase):
    def test_generate_notes_from_url(self):
        # Mock response from Gemini API
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "title": "Test Video",
                                        "sections": [
                                            {
                                                "heading": "Introduction",
                                                "bullets": ["This is a test bullet."]
                                            }
                                        ],
                                        "key_terms": [
                                            {
                                                "term": "Test",
                                                "definition": "A test term."
                                            }
                                        ]
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

        # We'll test the async method by running it in an event loop
        async def run_test():
            # Create a mock response object (regular Mock, not AsyncMock)
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None

            # Create a mock client (AsyncMock because we await its post method)
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response

            # Make the AsyncClient constructor return a context manager that yields mock_client
            mock_client_context = AsyncMock()
            mock_client_context.__aenter__.return_value = mock_client

            # Patch httpx.AsyncClient to return our context manager
            with patch("httpx.AsyncClient", return_value=mock_client_context):
                provider = GeminiVideoNotesProvider(api_key="test_api_key")
                notes = await provider.generate_notes_from_url("https://www.youtube.com/watch?v=test")
                return notes

        notes = asyncio.run(run_test())

        self.assertIsInstance(notes, LectureNotes)
        self.assertEqual(notes.title, "Test Video")
        self.assertEqual(len(notes.sections), 1)
        self.assertEqual(notes.sections[0].heading, "Introduction")
        self.assertEqual(notes.sections[0].bullets, ["This is a test bullet."])
        self.assertEqual(len(notes.key_terms), 1)
        self.assertEqual(notes.key_terms[0].term, "Test")
        self.assertEqual(notes.key_terms[0].definition, "A test term.")


if __name__ == "__main__":
    unittest.main()