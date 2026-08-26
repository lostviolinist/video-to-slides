from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .models import read_json, write_json
from .validate import validate_project


IMPORTANT_ROLES = {"thesis", "caveat", "conclusion"}
WINDOW_DECISIONS = {"selected", "covered", "omitted"}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _pptx_metrics(path: Path) -> dict[str, Any]:
    slide_pattern = re.compile(r"^ppt/slides/slide\d+\.xml$")
    notes_pattern = re.compile(r"^ppt/notesSlides/notesSlide\d+\.xml$")
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        slide_names = [name for name in names if slide_pattern.match(name)]
        notes_names = [name for name in names if notes_pattern.match(name)]
        source_blocks = 0
        for name in notes_names:
            root = ElementTree.fromstring(package.read(name))
            text = "".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
            decoded = html.unescape(text)
            if "[Sources]" in decoded and "[/Sources]" in decoded:
                source_blocks += 1
    return {
        "slides": len(slide_names),
        "notes_slides": len(notes_names),
        "source_note_blocks": source_blocks,
        "source_note_coverage": _ratio(source_blocks, len(slide_names)),
    }


def evaluate_project(project: Path, pptx: Path | None = None) -> dict[str, Any]:
    project = project.resolve()
    validation = validate_project(project)
    if not validation.get("ok"):
        return {
            "ok": False,
            "ready_for_semantic_review": False,
            "errors": ["evidence pack validation failed", *validation.get("errors", [])],
            "warnings": validation.get("warnings", []),
            "criteria": {},
            "metrics": {},
        }

    source = read_json(project / "source.json")
    transcript = read_json(project / "normalized_transcript.json")
    timeline = read_json(project / "timeline.json")
    evidence = read_json(project / "evidence.json")
    briefs = read_json(project / "slide_briefs.json")
    frame_manifest = read_json(project / "frames" / "frame_manifest.json")

    errors: list[str] = []
    warnings = list(validation.get("warnings", []))
    cards = evidence.get("cards", [])
    card_by_id = {str(card.get("id")): card for card in cards if card.get("id")}
    frame_by_id = {
        str(frame.get("id")): frame
        for frame in frame_manifest.get("frames", [])
        if frame.get("id")
    }
    windows = timeline.get("windows", [])
    window_by_id = {str(window.get("id")): window for window in windows if window.get("id")}

    reviews = evidence.get("window_reviews", [])
    review_by_id: dict[str, dict[str, Any]] = {}
    for review in reviews:
        window_id = str(review.get("window_id", ""))
        if not window_id:
            errors.append("window review is missing window_id")
            continue
        if window_id in review_by_id:
            errors.append(f"duplicate window review: {window_id}")
        review_by_id[window_id] = review
        if window_id not in window_by_id:
            errors.append(f"window review references unknown window: {window_id}")
        decision = review.get("decision")
        if decision not in WINDOW_DECISIONS:
            errors.append(f"{window_id}: invalid review decision {decision!r}")
        review_evidence = set(review.get("evidence_ids", []))
        unknown_evidence = review_evidence - set(card_by_id)
        if unknown_evidence:
            errors.append(f"{window_id}: unknown evidence IDs {sorted(unknown_evidence)}")
        if decision == "selected" and not review_evidence:
            errors.append(f"{window_id}: selected review has no evidence IDs")
        if decision == "omitted" and not str(review.get("reason", "")).strip():
            errors.append(f"{window_id}: omitted review needs a reason")

    missing_reviews = sorted(set(window_by_id) - set(review_by_id))
    if missing_reviews:
        errors.append(f"timeline windows were not reviewed: {missing_reviews}")

    reviewed_window_ids = set(window_by_id) & set(review_by_id)
    reviewed_transcript_ids = {
        segment_id
        for window_id in reviewed_window_ids
        for segment_id in window_by_id[window_id].get("transcript_segment_ids", [])
    }
    all_transcript_ids = {
        str(segment.get("id"))
        for segment in transcript.get("segments", [])
        if segment.get("id")
    }
    transcript_review_coverage = _ratio(
        len(reviewed_transcript_ids & all_transcript_ids), len(all_transcript_ids)
    )
    if all_transcript_ids and transcript_review_coverage < 1:
        errors.append("reviewed timeline windows do not cover every transcript segment")

    slides = briefs.get("slides", [])
    used_evidence = {
        str(evidence_id)
        for slide in slides
        for evidence_id in slide.get("evidence_ids", [])
    }
    important_evidence = {
        card_id
        for card_id, card in card_by_id.items()
        if card.get("role") in IMPORTANT_ROLES or float(card.get("weighted_score", 0)) >= 3.5
    }
    important_point_coverage = _ratio(
        len(important_evidence & used_evidence), len(important_evidence)
    )
    if important_point_coverage < 1:
        missing = sorted(important_evidence - used_evidence)
        errors.append(f"important evidence is missing from the slide briefs: {missing}")

    screenshot_total = 0
    screenshot_aligned = 0
    diagram_total = 0
    diagram_grounded = 0
    for slide in slides:
        number = slide.get("number")
        slide_evidence = set(slide.get("evidence_ids", []))
        visual = slide.get("visual") or {"kind": "none"}
        visual_evidence = set(visual.get("evidence_ids", []))
        kind = visual.get("kind", "none")
        if visual_evidence - slide_evidence:
            errors.append(f"slide {number}: visual evidence must also support the slide")
        if kind == "source-frame":
            screenshot_total += 1
            frame_id = str(visual.get("frame_id", ""))
            linked_frames = {
                str(frame)
                for evidence_id in visual_evidence
                for frame in card_by_id.get(str(evidence_id), {}).get("frame_ids", [])
            }
            if frame_id in frame_by_id and frame_id in linked_frames and visual_evidence:
                screenshot_aligned += 1
            else:
                errors.append(
                    f"slide {number}: source frame is not linked to the evidence chosen for the visual"
                )
        elif kind == "editable-diagram":
            diagram_total += 1
            instruction = str(visual.get("instruction", "")).strip()
            if instruction and visual_evidence and visual_evidence <= slide_evidence:
                diagram_grounded += 1
            else:
                errors.append(
                    f"slide {number}: diagram needs an instruction and explicit supporting evidence"
                )

    duration = float(source.get("duration", timeline.get("duration", 0)) or 0)
    body_evidence = {
        evidence_id
        for slide in slides
        if slide.get("role") == "body"
        for evidence_id in slide.get("evidence_ids", [])
    }
    first_third = {
        evidence_id
        for evidence_id in body_evidence
        if evidence_id in card_by_id
        and (
            float(card_by_id[evidence_id].get("start", 0))
            + float(card_by_id[evidence_id].get("end", 0))
        )
        / 2
        < duration / 3
    }
    opening_share = _ratio(len(first_third), len(body_evidence))
    if duration >= 1800 and len(body_evidence) >= 6 and opening_share > 0.6:
        warnings.append(
            "more than 60% of body-slide evidence comes from the first third of a long source"
        )

    pptx_metrics = None
    if pptx is not None:
        pptx_metrics = _pptx_metrics(pptx.resolve())
        if pptx_metrics["slides"] != len(slides):
            errors.append(
                f"PPTX has {pptx_metrics['slides']} slides but slide_briefs.json has {len(slides)}"
            )
        if pptx_metrics["source_note_coverage"] < 1:
            errors.append("not every PPTX slide has a complete [Sources] notes block")

    criteria = {
        "1_transcript_review_and_point_extraction": {
            "pass": not missing_reviews and transcript_review_coverage == 1,
            "window_review_coverage": _ratio(len(reviewed_window_ids), len(window_by_id)),
            "transcript_segment_coverage": transcript_review_coverage,
            "semantic_judge_required": True,
        },
        "2_slides_reflect_important_points": {
            "pass": important_point_coverage == 1,
            "important_point_coverage": important_point_coverage,
            "semantic_judge_required": True,
        },
        "3_screenshots_match_points": {
            "pass": screenshot_total == screenshot_aligned,
            "aligned": screenshot_aligned,
            "total": screenshot_total,
            "semantic_judge_required": screenshot_total > 0,
        },
        "4_diagrams_match_points": {
            "pass": diagram_total == diagram_grounded,
            "grounded": diagram_grounded,
            "total": diagram_total,
            "semantic_judge_required": diagram_total > 0,
        },
    }

    return {
        "ok": not errors and all(item["pass"] for item in criteria.values()),
        "ready_for_semantic_review": not errors,
        "errors": errors,
        "warnings": warnings,
        "criteria": criteria,
        "metrics": {
            "important_evidence_cards": len(important_evidence),
            "used_evidence_cards": len(used_evidence),
            "long_video_opening_share": opening_share,
            "pptx": pptx_metrics,
        },
        "semantic_review": {
            "required": True,
            "rubric": "evals/rubric.md",
            "note": "Automated checks prove traceability, not whether the chosen point, screenshot, or diagram is semantically correct.",
        },
    }


def evaluate_and_write(
    project: Path,
    pptx: Path,
    report: Path | None = None,
) -> dict[str, Any]:
    """Run the automated deck eval and keep its report in the evidence pack."""
    result = evaluate_project(project, pptx)
    write_json(report or project / "eval.json", result)
    return result
