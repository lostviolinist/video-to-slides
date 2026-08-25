from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vts.captions import audit_captions, parse_caption_file, parse_timecode, transcript_similarity


class CaptionTests(unittest.TestCase):
    def test_parse_timecode_formats(self) -> None:
        self.assertAlmostEqual(parse_timecode("01:02.500"), 62.5)
        self.assertAlmostEqual(parse_timecode("01:01:02,250"), 3662.25)

    def test_rolling_youtube_captions_are_collapsed(self) -> None:
        content = """WEBVTT

00:00.000 --> 00:02.000
hello

00:01.500 --> 00:03.000
hello world

00:03.100 --> 00:05.000
world from codex
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "captions.vtt"
            path.write_text(content, encoding="utf-8")
            segments = parse_caption_file(path, source="automatic-caption")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text, "hello world from codex")
        self.assertEqual(segments[0].source, "automatic-caption")

    def test_audit_flags_large_gaps(self) -> None:
        content = """WEBVTT

00:00.000 --> 00:10.000
opening content with several useful words for the transcript

00:09:40.000 --> 00:10:00.000
closing content after a very large unexplained gap
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "captions.vtt"
            path.write_text(content, encoding="utf-8")
            segments = parse_caption_file(path)
        audit = audit_captions(segments, 600)
        self.assertTrue(audit["recommended_full_asr"])
        self.assertGreater(audit["max_gap_seconds"], 500)

    def test_transcript_similarity_is_case_and_punctuation_tolerant(self) -> None:
        score = transcript_similarity("Hello, World!", "hello world")
        self.assertGreater(score, 0.95)


if __name__ == "__main__":
    unittest.main()
