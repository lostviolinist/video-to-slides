from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vts.models import write_json
from vts.validate import validate_project


class ValidateTests(unittest.TestCase):
    def _make_project(self, root: Path, slide_count: int = 8) -> None:
        write_json(root / "source.json", {"slides": "auto", "duration": 120, "kind": "local-video"})
        write_json(
            root / "normalized_transcript.json",
            {"segments": [{"id": "tr-00001", "start": 0, "end": 120, "text": "evidence"}]},
        )
        write_json(root / "caption_audit.json", {"analysis_mode": "multimodal"})
        write_json(
            root / "timeline.json",
            {"duration": 120, "windows": [{"id": "win-0001", "start": 0, "end": 120}]},
        )
        selected = root / "frames" / "selected" / "fr-00001.jpg"
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_bytes(b"jpeg fixture")
        write_json(
            root / "frames" / "frame_manifest.json",
            {
                "frames": [
                    {
                        "id": "fr-00001",
                        "timestamp": 20,
                        "selected_path": "frames/selected/fr-00001.jpg",
                    }
                ]
            },
        )
        write_json(
            root / "evidence.json",
            {
                "analysis_mode": "multimodal",
                "cards": [
                    {
                        "id": "ev-001",
                        "topic": "Topic",
                        "role": "conclusion",
                        "summary": "Supported conclusion",
                        "start": 0,
                        "end": 120,
                        "transcript_segment_ids": ["tr-00001"],
                        "frame_ids": ["fr-00001"],
                        "confidence": 0.9,
                        "scores": {
                            "thesis_relevance": 4,
                            "evidence_strength": 4,
                            "uniqueness": 4,
                            "visual_value": 4,
                            "structural_importance": 4,
                        },
                        "weighted_score": 4.0,
                    }
                ],
            },
        )
        write_json(
            root / "slide_briefs.json",
            {
                "slides": [
                    {
                        "number": index,
                        "role": (
                            "title"
                            if index == 1
                            else "introduction"
                            if index == 2
                            else "conclusion"
                            if index == slide_count
                            else "body"
                        ),
                        "title": f"Slide {index}",
                        "message": "Supported message",
                        "visible_content": ["One", "Two", "Three"] if index == 2 else ["Supported point"],
                        "evidence_ids": ["ev-001"],
                        "visual": {
                            "kind": "source-frame" if index == 2 else "none",
                            "frame_id": "fr-00001" if index == 2 else None,
                        },
                    }
                    for index in range(1, slide_count + 1)
                ]
            },
        )

    def test_valid_pack_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            result = validate_project(root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["counts"]["slides"], 8)

    def test_unknown_evidence_and_hard_cap_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root, slide_count=21)
            briefs = __import__("json").loads((root / "slide_briefs.json").read_text())
            briefs["slides"][0]["evidence_ids"] = ["missing"]
            write_json(root / "slide_briefs.json", briefs)
            result = validate_project(root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("hard cap" in error for error in result["errors"]))
        self.assertTrue(any("unknown evidence" in error for error in result["errors"]))

    def test_missing_narrative_bookends_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            briefs = __import__("json").loads((root / "slide_briefs.json").read_text())
            briefs["slides"][1]["role"] = "body"
            briefs["slides"][-1]["role"] = "body"
            write_json(root / "slide_briefs.json", briefs)
            result = validate_project(root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("second slide" in error for error in result["errors"]))
        self.assertTrue(any("final slide" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
