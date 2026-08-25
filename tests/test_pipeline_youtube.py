from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vts.models import TranscriptSegment, read_json
from vts.pipeline import prepare_project


class YouTubePipelineTests(unittest.TestCase):
    def _captions(self) -> list[TranscriptSegment]:
        return [
            TranscriptSegment(
                id=f"tr-{index:05d}",
                start=float((index - 1) * 10),
                end=float(index * 10),
                text=(
                    f"segment {index} provides clear caption evidence with enough distinct words "
                    "for a reliable structural transcript audit"
                ),
                source="manual-caption",
                confidence=None,
            )
            for index in range(1, 13)
        ]

    def test_adaptive_uses_sound_captions_without_local_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            scout = root / "scout.mp4"
            scout.touch()
            with (
                patch("vts.pipeline.youtube_metadata", return_value={
                    "duration": 120,
                    "title": "Captioned source",
                    "channel": "Example",
                    "language": "en",
                    "subtitles": {"en": [{"ext": "vtt"}]},
                }),
                patch("vts.pipeline.choose_caption", return_value=("manual-caption", "en")),
                patch("vts.pipeline.download_caption", return_value=root / "caption.vtt"),
                patch("vts.pipeline.parse_caption_cues", return_value=[]),
                patch("vts.pipeline.parse_caption_file", return_value=self._captions()),
                patch("vts.pipeline.download_scout", return_value=scout),
                patch("vts.pipeline.extract_candidates", return_value=[]),
                patch("vts.pipeline.build_contact_sheets", return_value=[]),
                patch("vts.pipeline.model_is_cached", return_value=False),
                patch("vts.pipeline.download_audio") as download_audio,
                patch("vts.pipeline.transcribe_file") as transcribe_file,
            ):
                result = prepare_project(
                    "https://youtu.be/wjZofJX0v4M",
                    project,
                    accuracy="adaptive",
                    transcription="auto",
                )
            audit = read_json(project / "caption_audit.json")

        self.assertEqual(result["phase"], "prepared")
        self.assertEqual(audit["selected_transcript_source"], "manual-caption")
        self.assertEqual(audit["spot_check_status"], "skipped-no-local-model")
        self.assertFalse(audit["full_asr_used"])
        download_audio.assert_not_called()
        transcribe_file.assert_not_called()

    def test_captions_mode_rejects_captionless_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scout = root / "scout.mp4"
            scout.touch()
            with (
                patch("vts.pipeline.youtube_metadata", return_value={
                    "duration": 120,
                    "title": "Captionless source",
                    "channel": "Example",
                    "language": "en",
                    "subtitles": {},
                    "automatic_captions": {},
                }),
                patch("vts.pipeline.choose_caption", return_value=None),
                patch("vts.pipeline.download_scout", return_value=scout),
                patch("vts.pipeline.extract_candidates", return_value=[]),
                patch("vts.pipeline.build_contact_sheets", return_value=[]),
            ):
                with self.assertRaisesRegex(RuntimeError, "no usable captions"):
                    prepare_project(
                        "https://youtu.be/wjZofJX0v4M",
                        root / "project",
                        transcription="captions",
                    )


if __name__ == "__main__":
    unittest.main()
