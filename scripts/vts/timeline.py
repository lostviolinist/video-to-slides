from __future__ import annotations

from typing import Any

from .models import TimelineWindow, TranscriptSegment


WEIGHTS = {
    "thesis_relevance": 0.35,
    "evidence_strength": 0.25,
    "uniqueness": 0.20,
    "visual_value": 0.10,
    "structural_importance": 0.10,
}


def make_windows(
    duration: float,
    segments: list[TranscriptSegment],
    chapters: list[dict[str, Any]] | None = None,
    frames: list[dict[str, Any]] | None = None,
    contact_sheets: list[dict[str, Any]] | None = None,
    window_seconds: float = 420.0,
    overlap_seconds: float = 30.0,
) -> list[TimelineWindow]:
    if duration <= 0:
        return []
    if overlap_seconds >= window_seconds:
        raise ValueError("overlap must be shorter than window")
    chapters = chapters or []
    frames = frames or []
    contact_sheets = contact_sheets or []
    windows: list[TimelineWindow] = []
    start = 0.0
    index = 1
    while start < duration:
        end = min(duration, start + window_seconds)
        transcript_ids = [s.id for s in segments if s.end >= start and s.start <= end]
        chapter_titles = [
            str(c.get("title", ""))
            for c in chapters
            if float(c.get("end_time", c.get("end", duration))) >= start
            and float(c.get("start_time", c.get("start", 0))) <= end
            and c.get("title")
        ]
        frame_ids = [f["id"] for f in frames if start <= float(f.get("timestamp", 0)) <= end]
        sheets = [
            str(sheet["path"])
            for sheet in contact_sheets
            if float(sheet.get("end", 0)) >= start and float(sheet.get("start", 0)) <= end
        ]
        windows.append(
            TimelineWindow(
                id=f"win-{index:04d}",
                start=round(start, 3),
                end=round(end, 3),
                transcript_segment_ids=transcript_ids,
                chapter_titles=chapter_titles,
                frame_ids=frame_ids,
                contact_sheets=sheets,
            )
        )
        if end >= duration:
            break
        start = end - overlap_seconds
        index += 1
    return windows


def weighted_score(scores: dict[str, Any]) -> float:
    total = 0.0
    for key, weight in WEIGHTS.items():
        value = float(scores.get(key, 0))
        if not 0 <= value <= 5:
            raise ValueError(f"{key} must be between 0 and 5")
        total += value * weight
    return round(total, 4)


def rank_evidence(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for card in cards:
        updated = dict(card)
        updated["weighted_score"] = weighted_score(card.get("scores", {}))
        ranked.append(updated)
    return sorted(
        ranked,
        key=lambda card: (
            -float(card["weighted_score"]),
            float(card.get("start", 0)),
            str(card.get("id", "")),
        ),
    )


def coverage_roles(cards: list[dict[str, Any]]) -> set[str]:
    return {str(card.get("role", "")) for card in cards if card.get("role")}
