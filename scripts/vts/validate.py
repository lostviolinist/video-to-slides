from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import read_json
from .timeline import coverage_roles, weighted_score


REQUIRED_FILES = [
    "source.json",
    "normalized_transcript.json",
    "caption_audit.json",
    "timeline.json",
    "frames/frame_manifest.json",
    "evidence.json",
    "slide_briefs.json",
]
ALLOWED_ROLES = {"thesis", "claim", "evidence", "example", "caveat", "conclusion"}
ALLOWED_VISUALS = {"source-frame", "editable-chart", "editable-diagram", "generated", "none"}
ALLOWED_SLIDE_ROLES = {"title", "introduction", "body", "conclusion"}


def validate_project(project: Path) -> dict[str, Any]:
    project = project.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (project / relative).is_file():
            errors.append(f"missing required file: {relative}")
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}

    source = read_json(project / "source.json")
    transcript = read_json(project / "normalized_transcript.json")
    timeline = read_json(project / "timeline.json")
    frame_manifest = read_json(project / "frames" / "frame_manifest.json")
    evidence = read_json(project / "evidence.json")
    briefs = read_json(project / "slide_briefs.json")

    transcript_ids = {segment.get("id") for segment in transcript.get("segments", [])}
    frame_by_id = {frame.get("id"): frame for frame in frame_manifest.get("frames", [])}
    cards = evidence.get("cards", [])
    card_by_id: dict[str, dict[str, Any]] = {}
    for index, card in enumerate(cards, start=1):
        card_id = card.get("id")
        if not card_id:
            errors.append(f"evidence card {index} has no id")
            continue
        if card_id in card_by_id:
            errors.append(f"duplicate evidence id: {card_id}")
        card_by_id[card_id] = card
        if card.get("role") not in ALLOWED_ROLES:
            errors.append(f"{card_id}: invalid role {card.get('role')!r}")
        if not 0 <= float(card.get("confidence", -1)) <= 1:
            errors.append(f"{card_id}: confidence must be between 0 and 1")
        missing_transcript = set(card.get("transcript_segment_ids", [])) - transcript_ids
        if missing_transcript:
            errors.append(f"{card_id}: unknown transcript IDs {sorted(missing_transcript)}")
        missing_frames = set(card.get("frame_ids", [])) - set(frame_by_id)
        if missing_frames:
            errors.append(f"{card_id}: unknown frame IDs {sorted(missing_frames)}")
        try:
            expected = weighted_score(card.get("scores", {}))
            if abs(float(card.get("weighted_score", expected)) - expected) > 0.011:
                errors.append(f"{card_id}: weighted_score must be {expected}")
        except (TypeError, ValueError) as exc:
            errors.append(f"{card_id}: invalid scores ({exc})")

    slides = briefs.get("slides", [])
    requested = str(source.get("slides", "auto"))
    if requested == "auto" and len(slides) > 20:
        errors.append("automatic deck exceeds the 20-slide hard cap")
    if requested == "auto" and not 8 <= len(slides) <= 16:
        warnings.append(f"automatic deck has {len(slides)} slides; expected 8–16 when content supports it")
    seen_numbers: set[int] = set()
    used_topics: set[str] = set()
    for index, slide in enumerate(slides, start=1):
        number = int(slide.get("number", index))
        if number in seen_numbers:
            errors.append(f"duplicate slide number: {number}")
        seen_numbers.add(number)
        evidence_ids = slide.get("evidence_ids", [])
        if not evidence_ids:
            errors.append(f"slide {number}: no evidence_ids")
        unknown_cards = set(evidence_ids) - set(card_by_id)
        if unknown_cards:
            errors.append(f"slide {number}: unknown evidence IDs {sorted(unknown_cards)}")
        slide_role = slide.get("role")
        if slide_role not in ALLOWED_SLIDE_ROLES:
            errors.append(f"slide {number}: invalid or missing slide role {slide_role!r}")
        for evidence_id in evidence_ids:
            if evidence_id in card_by_id:
                used_topics.add(str(card_by_id[evidence_id].get("topic", "")))
        visual = slide.get("visual") or {"kind": "none"}
        visual_kind = visual.get("kind", "none")
        if visual_kind not in ALLOWED_VISUALS:
            errors.append(f"slide {number}: invalid visual kind {visual_kind!r}")
        if visual_kind == "source-frame":
            frame_id = visual.get("frame_id")
            frame = frame_by_id.get(frame_id)
            if not frame:
                errors.append(f"slide {number}: unknown source frame {frame_id!r}")
            else:
                selected = frame.get("selected_path")
                selected_path = project / selected if selected and not Path(selected).is_absolute() else Path(selected or "")
                if not selected or not selected_path.is_file():
                    errors.append(f"slide {number}: source frame {frame_id} was not extracted")

    if len(slides) < 3:
        errors.append("deck must include separate title, introduction, and conclusion slides")
    else:
        if slides[0].get("role") != "title":
            errors.append("first slide must have role 'title'")
        if slides[1].get("role") != "introduction":
            errors.append("second slide must have role 'introduction'")
        if slides[-1].get("role") != "conclusion":
            errors.append("final slide must have role 'conclusion'")
        intro_points = slides[1].get("visible_content", [])
        if not 3 <= len(intro_points) <= 5:
            warnings.append("introduction should map three to five evidence-backed takeaways")

    all_topics = {str(card.get("topic", "")) for card in cards if card.get("topic")}
    missing_topics = sorted(all_topics - used_topics)
    if missing_topics:
        warnings.append(f"evidence topics omitted from slide briefs: {missing_topics}")
    roles = coverage_roles(cards)
    if "conclusion" not in roles:
        warnings.append("evidence pack has no conclusion card")
    if "caveat" not in roles:
        warnings.append("evidence pack has no caveat card; confirm the source truly contains none")
    windows = timeline.get("windows", [])
    if windows and float(windows[0].get("start", -1)) != 0:
        errors.append("timeline does not start at zero")
    if windows and float(windows[-1].get("end", 0)) < float(timeline.get("duration", 0)):
        errors.append("timeline does not cover the complete duration")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "transcript_segments": len(transcript_ids),
            "timeline_windows": len(windows),
            "frames": len(frame_by_id),
            "evidence_cards": len(cards),
            "slides": len(slides),
        },
    }
