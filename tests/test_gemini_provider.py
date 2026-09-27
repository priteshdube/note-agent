import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from models import LectureNotes
from providers.gemini_provider import GeminiVideoNotesProvider


class GeminiProviderTest(unittest.TestCase):
    def test_generate_notes_from_url(self):
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

        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response

            mock_client_context = AsyncMock()
            mock_client_context.__aenter__.return_value = mock_client

            with patch("httpx.AsyncClient", return_value=mock_client_context) as mock_async_client:
                provider = GeminiVideoNotesProvider(api_key="test_api_key")
                notes = await provider.generate_notes_from_url("https://www.youtube.com/watch?v=test")

                mock_async_client.assert_called_once()
                mock_client.post.assert_awaited_once()
                args, kwargs = mock_client.post.await_args
                self.assertEqual(args[0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent")
                self.assertEqual(kwargs["headers"]["x-goog-api-key"], "test_api_key")
                self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
                self.assertEqual(kwargs["json"]["contents"][0]["parts"][1]["file_data"]["mime_type"], "video/*")
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