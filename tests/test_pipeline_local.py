from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vts.models import TranscriptSegment, read_json
from vts.pipeline import prepare_project


class LocalPipelineTests(unittest.TestCase):
    @patch("vts.pipeline.discover_ffmpeg", return_value="/fake/ffmpeg")
    @patch("vts.pipeline.extract_candidates", return_value=[])
    @patch("vts.pipeline.build_contact_sheets", return_value=[])
    @patch("vts.pipeline.local_duration", return_value=900.0)
    @patch(
        "vts.pipeline.transcribe_file",
        return_value=[
            TranscriptSegment(
                id="tr-00001",
                start=0,
                end=900,
                text="A complete synthetic transcript",
                source="asr",
                confidence=0.9,
            )
        ],
    )
    def test_local_video_preparation_writes_complete_timeline(
        self,
        _transcribe,
        _duration,
        _sheets,
        _frames,
        _ffmpeg,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.mp4"
            source.touch()
            project = root / "project"
            result = prepare_project(
                str(source),
                project,
                accuracy="adaptive",
                allow_model_download=True,
            )
            timeline = read_json(project / "timeline.json")
            source_record = read_json(project / "source.json")
        self.assertEqual(result["phase"], "prepared")
        self.assertEqual(source_record["kind"], "local-video")
        self.assertEqual(timeline["windows"][0]["start"], 0)
        self.assertEqual(timeline["windows"][-1]["end"], 900)


if __name__ == "__main__":
    unittest.main()
