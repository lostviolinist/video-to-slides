from __future__ import annotations

import unittest

from vts.models import TranscriptSegment
from vts.timeline import make_windows, rank_evidence, weighted_score


class TimelineTests(unittest.TestCase):
    def test_hour_video_has_complete_overlapping_windows(self) -> None:
        segments = [
            TranscriptSegment(
                id=f"tr-{index:05d}",
                start=index * 60,
                end=index * 60 + 45,
                text=f"minute {index}",
                source="caption",
            )
            for index in range(60)
        ]
        windows = make_windows(3600, segments)
        self.assertEqual(windows[0].start, 0)
        self.assertEqual(windows[-1].end, 3600)
        self.assertGreater(len(windows), 8)
        for left, right in zip(windows, windows[1:]):
            self.assertAlmostEqual(left.end - right.start, 30)

    def test_weighted_score_matches_contract(self) -> None:
        scores = {
            "thesis_relevance": 4,
            "evidence_strength": 5,
            "uniqueness": 4,
            "visual_value": 3,
            "structural_importance": 4,
        }
        self.assertEqual(weighted_score(scores), 4.15)

    def test_ranking_uses_score_then_timestamp(self) -> None:
        base = {
            "scores": {
                "thesis_relevance": 5,
                "evidence_strength": 5,
                "uniqueness": 5,
                "visual_value": 5,
                "structural_importance": 5,
            }
        }
        ranked = rank_evidence([
            {**base, "id": "late", "start": 20},
            {**base, "id": "early", "start": 10},
        ])
        self.assertEqual([card["id"] for card in ranked], ["early", "late"])


if __name__ == "__main__":
    unittest.main()
