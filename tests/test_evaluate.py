from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from vts.evaluate import evaluate_and_write, evaluate_project
from vts.models import read_json, write_json


class EvaluateTests(unittest.TestCase):
    def _make_project(self, root: Path) -> None:
        write_json(root / "source.json", {"slides": "auto", "duration": 120, "kind": "local-video"})
        write_json(
            root / "normalized_transcript.json",
            {"segments": [{"id": "tr-00001", "start": 0, "end": 120, "text": "evidence"}]},
        )
        write_json(root / "caption_audit.json", {"analysis_mode": "multimodal"})
        write_json(
            root / "timeline.json",
            {
                "duration": 120,
                "windows": [
                    {
                        "id": "win-0001",
                        "start": 0,
                        "end": 120,
                        "transcript_segment_ids": ["tr-00001"],
                    }
                ],
            },
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
                "window_reviews": [
                    {
                        "window_id": "win-0001",
                        "decision": "selected",
                        "evidence_ids": ["ev-001"],
                    }
                ],
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
                            if index == 8
                            else "body"
                        ),
                        "title": f"Slide {index}",
                        "message": "Supported message",
                        "visible_content": ["One", "Two", "Three"] if index == 2 else ["Point"],
                        "evidence_ids": ["ev-001"],
                        "visual": {
                            "kind": "source-frame" if index == 2 else "none",
                            "frame_id": "fr-00001" if index == 2 else None,
                            "evidence_ids": ["ev-001"] if index == 2 else [],
                            "instruction": "Show the supported moment" if index == 2 else "",
                        },
                    }
                    for index in range(1, 9)
                ]
            },
        )

    def _make_pptx_package(self, path: Path, slides: int, source_notes: int) -> None:
        with zipfile.ZipFile(path, "w") as package:
            for index in range(1, slides + 1):
                package.writestr(f"ppt/slides/slide{index}.xml", "<slide/>")
                note = "[Sources]source[/Sources]" if index <= source_notes else "notes"
                package.writestr(
                    f"ppt/notesSlides/notesSlide{index}.xml",
                    f'<p:notes xmlns:p="p" xmlns:a="a"><a:t>{note}</a:t></p:notes>',
                )

    def test_traceability_eval_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            result = evaluate_project(root)
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(result["ready_for_semantic_review"])

    def test_eval_report_is_saved_in_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            pptx = root / "deck.pptx"
            self._make_pptx_package(pptx, slides=8, source_notes=8)
            result = evaluate_and_write(root, pptx)
            saved = read_json(root / "eval.json")
        self.assertEqual(saved, result)
        self.assertTrue(saved["ok"], saved["errors"])

    def test_every_window_must_be_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            evidence = read_json(root / "evidence.json")
            evidence["window_reviews"] = []
            write_json(root / "evidence.json", evidence)
            result = evaluate_project(root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("not reviewed" in error for error in result["errors"]))

    def test_screenshot_must_match_visual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            second = root / "frames" / "selected" / "fr-00002.jpg"
            second.write_bytes(b"second jpeg fixture")
            manifest = read_json(root / "frames" / "frame_manifest.json")
            manifest["frames"].append(
                {
                    "id": "fr-00002",
                    "timestamp": 80,
                    "selected_path": "frames/selected/fr-00002.jpg",
                }
            )
            write_json(root / "frames" / "frame_manifest.json", manifest)
            briefs = read_json(root / "slide_briefs.json")
            briefs["slides"][1]["visual"]["frame_id"] = "fr-00002"
            write_json(root / "slide_briefs.json", briefs)
            result = evaluate_project(root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("source frame is not linked" in error for error in result["errors"]))

    def test_diagram_needs_explicit_grounding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            briefs = read_json(root / "slide_briefs.json")
            briefs["slides"][2]["visual"] = {
                "kind": "editable-diagram",
                "evidence_ids": [],
                "instruction": "",
            }
            write_json(root / "slide_briefs.json", briefs)
            result = evaluate_project(root)
        self.assertFalse(result["ok"])
        self.assertTrue(any("diagram needs" in error for error in result["errors"]))

    def test_pptx_needs_source_notes_on_every_slide(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._make_project(root)
            pptx = root / "deck.pptx"
            self._make_pptx_package(pptx, slides=8, source_notes=7)
            result = evaluate_project(root, pptx)
        self.assertFalse(result["ok"])
        self.assertTrue(any("[Sources]" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
