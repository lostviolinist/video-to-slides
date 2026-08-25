from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vts.source import classify_source, is_youtube_url, youtube_video_id


class SourceTests(unittest.TestCase):
    def test_youtube_variants(self) -> None:
        self.assertTrue(is_youtube_url("https://youtu.be/abc123XYZ_-"))
        self.assertEqual(youtube_video_id("https://youtu.be/abc123XYZ_-"), "abc123XYZ_-")
        self.assertEqual(
            youtube_video_id("https://www.youtube.com/watch?v=abc123XYZ_-&t=3"),
            "abc123XYZ_-",
        )
        self.assertFalse(is_youtube_url("https://example.com/watch?v=abc123XYZ_-"))

    def test_local_source_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.mp4"
            path.touch()
            kind, resolved = classify_source(str(path))
        self.assertEqual(kind, "local-video")
        self.assertEqual(resolved, path.resolve())


if __name__ == "__main__":
    unittest.main()
