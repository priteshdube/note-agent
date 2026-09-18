import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestRoutes(unittest.TestCase):
    def test_process_lecture(self):
        # Mock the providers and notion client
        with patch("routes.process.get_transcription_provider") as mock_transcription_provider, \
             patch("routes.process.get_notegen_provider") as mock_notegen_provider, \
             patch("routes.process.find_or_create_topic_page") as mock_find_topic, \
             patch("routes.process.create_lecture_page") as mock_create_lecture:

            # Setup mocks
            mock_transcription_provider.return_value.transcribe = AsyncMock(return_value="test transcript")
            mock_notegen_provider.return_value.generate_notes = AsyncMock(return_value={
                "title": "Test Lecture",
                "sections": [{"heading": "Introduction", "bullets": ["This is a test."]}],
                "key_terms": [{"term": "Test", "definition": "A test term."}]
            })
            mock_find_topic.return_value = "topic_page_id"
            mock_create_lecture.return_value = "12345678-90ab-cdef-1234-567890abcdef"  # page ID with dashes

            # Make the request
            response = client.post(
                "/api/process-lecture",
                files={"audio_file": ("test.mp3", b"fake audio data", "audio/mpeg")},
                data={"topic_name": "Test Topic"}
            )

            # Assertions
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["notes"]["title"], "Test Lecture")
            self.assertEqual(
                data["notion_page_url"],
                "https://www.notion.so/1234567890abcdef1234567890abcdef",
                f"Expected notion_page_url to be 'https://www.notion.so/1234567890abcdef1234567890abcdef', but got {data['notion_page_url']}"
            )

    def test_process_youtube(self):
        # Mock the providers and notion client
        with patch("routes.process.get_video_url_provider") as mock_video_provider, \
             patch("routes.process.find_or_create_topic_page") as mock_find_topic, \
             patch("routes.process.create_lecture_page") as mock_create_lecture:

            # Setup mocks
            mock_video_provider.return_value.generate_notes_from_url = AsyncMock(return_value={
                "title": "Test Video",
                "sections": [{"heading": "Introduction", "bullets": ["This is a test."]}],
                "key_terms": [{"term": "Test", "definition": "A test term."}]
            })
            mock_find_topic.return_value = "topic_page_id"
            mock_create_lecture.return_value = "12345678-90ab-cdef-1234-567890abcdef"  # page ID with dashes

            # Make the request
            response = client.post(
                "/api/process-youtube",
                data={"youtube_url": "https://www.youtube.com/watch?v=test", "topic_name": "Test Topic"}
            )

            # Assertions
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["notes"]["title"], "Test Video")
            self.assertEqual(
                data["notion_page_url"],
                "https://www.notion.so/1234567890abcdef1234567890abcdef",
                f"Expected notion_page_url to be 'https://www.notion.so/1234567890abcdef1234567890abcdef', but got {data['notion_page_url']}"
            )

if __name__ == "__main__":
    unittest.main()