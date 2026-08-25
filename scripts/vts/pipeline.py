from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .captions import (
    audit_captions,
    parse_caption_cues,
    parse_caption_file,
    text_for_range,
    transcript_similarity,
)
from .frames import build_contact_sheets, discover_ffmpeg, extract_candidates, extract_frame
from .models import TranscriptSegment, read_json, write_json
from .source import (
    classify_source,
    choose_caption,
    download_audio,
    download_caption,
    download_scout,
    download_section,
    local_duration,
    youtube_metadata,
    youtube_video_id,
)
from .timeline import make_windows
from .transcribe import DEEP_MODEL, TURBO_MODEL, transcribe_file, transcribe_sample


def _relative(project: Path, path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(candidate.resolve())


def _chapters(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for chapter in metadata.get("chapters") or []:
        result.append(
            {
                "title": str(chapter.get("title") or "Untitled chapter"),
                "start_time": float(chapter.get("start_time", 0)),
                "end_time": float(chapter.get("end_time", metadata.get("duration", 0))),
            }
        )
    return result


def _segments_payload(segments: list[TranscriptSegment]) -> dict[str, Any]:
    return {"segments": [segment.to_dict() for segment in segments]}


def _sample_positions(duration: float, sample_length: float = 45.0) -> list[float]:
    if duration <= sample_length:
        return [0.0]
    values = [max(0.0, min(duration - sample_length, duration * ratio - sample_length / 2)) for ratio in (0.15, 0.5, 0.85)]
    unique: list[float] = []
    for value in values:
        rounded = round(value, 3)
        if all(abs(rounded - prior) > sample_length / 2 for prior in unique):
            unique.append(rounded)
    return unique


def _spot_checks(
    audio: Path,
    captions: list[TranscriptSegment],
    duration: float,
    allow_model_download: bool,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for start in _sample_positions(duration):
        length = min(45.0, max(1.0, duration - start))
        asr_text = transcribe_sample(
            audio,
            start=start,
            length=length,
            model=TURBO_MODEL,
            allow_download=allow_model_download,
        )
        caption_text = text_for_range(captions, start, start + length)
        similarity = transcript_similarity(caption_text, asr_text) if caption_text else 0.0
        checks.append(
            {
                "start": start,
                "end": round(start + length, 3),
                "caption_text": caption_text,
                "asr_text": asr_text,
                "similarity": round(similarity, 4),
            }
        )
    return checks


def prepare_project(
    source_value: str,
    project: Path,
    accuracy: str = "adaptive",
    purpose: str = "briefing",
    slides: str = "auto",
    output_language: str = "auto",
    keep_media: bool = False,
    allow_model_download: bool = False,
) -> dict[str, Any]:
    project = project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    source_kind, local_path = classify_source(source_value)
    existing_source = project / "source.json"
    if existing_source.is_file():
        previous = read_json(existing_source)
        previous_value = previous.get("url") or previous.get("local_path")
        normalized_value = source_value if source_kind == "youtube" else str(local_path)
        if previous_value != normalized_value:
            raise ValueError("Project already belongs to a different source")

    raw_dir = project / "raw"
    media_dir = project / "media"
    frames_dir = project / "frames"
    raw_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    caption_segments: list[TranscriptSegment] = []
    raw_caption_cues: list[dict[str, Any]] = []
    caption_kind: str | None = None
    caption_language: str | None = None
    scout_path: Path | None = None
    audio_path: Path | None = None

    if source_kind == "youtube":
        metadata = youtube_metadata(source_value)
        duration = float(metadata.get("duration") or 0)
        if duration <= 0:
            raise ValueError("YouTube metadata did not contain a positive duration")
        chapters = _chapters(metadata)
        # Analyze the source-language captions. Output-language translation belongs
        # in slide authoring so it cannot erase or distort the underlying evidence.
        caption_choice = choose_caption(metadata, "auto")
        if caption_choice:
            caption_kind, caption_language = caption_choice
            caption_path = download_caption(source_value, raw_dir, caption_kind, caption_language)
            raw_caption_cues = parse_caption_cues(caption_path)
            caption_segments = parse_caption_file(caption_path, source=caption_kind)
        scout_candidates = sorted(media_dir.glob("scout.*"))
        scout_path = scout_candidates[0] if scout_candidates else download_scout(source_value, media_dir)
        title = str(metadata.get("title") or youtube_video_id(source_value) or "YouTube video")
        channel = str(metadata.get("channel") or metadata.get("uploader") or "")
        detected_language = str(metadata.get("language") or caption_language or "")
    else:
        assert local_path is not None
        duration = local_duration(discover_ffmpeg(), local_path)
        chapters = []
        title = local_path.stem
        channel = ""
        detected_language = ""
        if source_kind == "local-video":
            scout_path = local_path
        audio_path = local_path

    audit = audit_captions(caption_segments, duration)
    spot_checks: list[dict[str, Any]] = []
    full_asr = source_kind.startswith("local") or accuracy == "deep" or not caption_segments
    full_asr_reasons: list[str] = []
    if full_asr:
        full_asr_reasons.append("local source, deep mode, or captions unavailable")

    if source_kind == "youtube" and accuracy in {"adaptive", "deep"}:
        audio_candidates = sorted(media_dir.glob("audio.*"))
        audio_path = audio_candidates[0] if audio_candidates else download_audio(source_value, media_dir)
    if accuracy == "adaptive" and caption_segments and audio_path:
        spot_checks = _spot_checks(audio_path, caption_segments, duration, allow_model_download)
        average_similarity = sum(check["similarity"] for check in spot_checks) / max(1, len(spot_checks))
        if audit["recommended_full_asr"]:
            full_asr = True
            full_asr_reasons.extend(audit["reasons"])
        if average_similarity < 0.62:
            full_asr = True
            full_asr_reasons.append("distributed audio checks materially disagree with captions")
    if accuracy == "fast" and caption_segments:
        full_asr = False

    asr_segments: list[TranscriptSegment] = []
    selected_segments = caption_segments
    transcript_source = caption_kind or "none"
    if full_asr:
        if audio_path is None and source_kind == "youtube":
            audio_path = download_audio(source_value, media_dir)
        if audio_path is None:
            raise RuntimeError("Transcription was required but no audio source was available")
        model = DEEP_MODEL if accuracy == "deep" else TURBO_MODEL
        asr_segments = transcribe_file(audio_path, model, allow_model_download, source="asr")
        if asr_segments:
            selected_segments = asr_segments
            transcript_source = "asr"

    if raw_caption_cues:
        write_json(project / "caption_transcript.json", {"source": caption_kind, "segments": raw_caption_cues})
    if asr_segments:
        write_json(project / "asr_transcript.json", _segments_payload(asr_segments))
    raw_payload: dict[str, Any]
    if transcript_source == "asr":
        raw_payload = _segments_payload(asr_segments)
    else:
        raw_payload = {"source": caption_kind, "segments": raw_caption_cues}
    write_json(project / "raw_transcript.json", raw_payload)
    write_json(project / "normalized_transcript.json", _segments_payload(selected_segments))

    analysis_mode = "multimodal" if selected_segments else "visual-storyboard"
    caption_audit = {
        "caption_kind": caption_kind,
        "caption_language": caption_language,
        "structural": audit,
        "spot_checks": spot_checks,
        "full_asr_used": bool(asr_segments),
        "full_asr_reasons": sorted(set(full_asr_reasons)),
        "selected_transcript_source": transcript_source,
        "analysis_mode": analysis_mode,
    }
    write_json(project / "caption_audit.json", caption_audit)

    source_record = {
        "kind": source_kind,
        "url": source_value if source_kind == "youtube" else None,
        "video_id": youtube_video_id(source_value) if source_kind == "youtube" else None,
        "local_path": str(local_path) if local_path else None,
        "title": title,
        "channel": channel,
        "duration": round(duration, 3),
        "detected_language": detected_language,
        "output_language": output_language if output_language != "auto" else detected_language or "source",
        "chapters": chapters,
        "accuracy": accuracy,
        "purpose": purpose,
        "slides": slides,
        "keep_media": keep_media,
        "scout_path": _relative(project, scout_path),
        "audio_path": _relative(project, audio_path),
    }
    write_json(project / "source.json", source_record)

    frames: list[dict[str, Any]] = []
    sheets: list[dict[str, Any]] = []
    if scout_path is not None and source_kind != "local-audio":
        candidates_dir = frames_dir / "candidates"
        frames = extract_candidates(scout_path, candidates_dir, duration, chapters, accuracy)
        for frame in frames:
            frame["path"] = _relative(project, frame["path"])
        sheets = build_contact_sheets(
            [{**frame, "path": str(project / frame["path"])} for frame in frames],
            project / "contact_sheets",
        )
        for sheet in sheets:
            sheet["path"] = _relative(project, sheet["path"])
    write_json(frames_dir / "frame_manifest.json", {"frames": frames, "contact_sheets": sheets})

    windows = make_windows(
        duration=duration,
        segments=selected_segments,
        chapters=chapters,
        frames=frames,
        contact_sheets=sheets,
    )
    write_json(
        project / "timeline.json",
        {
            "duration": round(duration, 3),
            "window_seconds": 420,
            "overlap_seconds": 30,
            "windows": [window.to_dict() for window in windows],
        },
    )
    manifest = {
        "phase": "prepared",
        "analysis_mode": analysis_mode,
        "transcript_segments": len(selected_segments),
        "timeline_windows": len(windows),
        "candidate_frames": len(frames),
        "contact_sheets": len(sheets),
        "next": "Inspect every timeline window and contact sheet, then write evidence.json and slide_briefs.json.",
    }
    write_json(project / "analysis_manifest.json", manifest)
    return manifest


def _resolve_project_path(project: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else project / path


def extract_selected(project: Path, frame_ids: list[str]) -> dict[str, Any]:
    project = project.resolve()
    source = read_json(project / "source.json")
    manifest_path = project / "frames" / "frame_manifest.json"
    manifest = read_json(manifest_path)
    frames = {frame["id"]: frame for frame in manifest.get("frames", [])}
    unknown = sorted(set(frame_ids) - set(frames))
    if unknown:
        raise ValueError(f"Unknown frame IDs: {', '.join(unknown)}")
    selected_dir = project / "frames" / "selected"
    clips_dir = project / "media" / "clips"
    selected_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    for frame_id in frame_ids:
        frame = frames[frame_id]
        timestamp = float(frame["timestamp"])
        output = selected_dir / f"{frame_id}.jpg"
        if source["kind"] == "youtube":
            clip_start = max(0.0, timestamp - 2.0)
            try:
                clip = download_section(source["url"], clips_dir / frame_id, clip_start, timestamp + 2.0)
                extract_frame(clip, timestamp - clip_start, output, width=1920)
            except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as exc:
                warnings.append(f"{frame_id}: targeted extraction failed ({exc}); used scout media")
                scout = _resolve_project_path(project, source.get("scout_path"))
                if scout is None:
                    raise RuntimeError("Scout media is unavailable for fallback") from exc
                extract_frame(scout, timestamp, output, width=1920)
        else:
            local = Path(source["local_path"])
            extract_frame(local, timestamp, output, width=1920)
        frame["selected_path"] = _relative(project, output)

    manifest["frames"] = list(frames.values())
    write_json(manifest_path, manifest)
    return {"selected": len(frame_ids), "warnings": warnings}


def cleanup_project(project: Path) -> dict[str, Any]:
    project = project.resolve()
    source = read_json(project / "source.json")
    if source.get("keep_media"):
        return {"removed": [], "reason": "keep_media is enabled"}
    removable = [
        project / "media" / "clips",
        project / "frames" / "candidates",
        project / "contact_sheets",
    ]
    if source.get("kind") == "youtube":
        scout = _resolve_project_path(project, source.get("scout_path"))
        audio = _resolve_project_path(project, source.get("audio_path"))
        if scout:
            removable.append(scout)
        if audio:
            removable.append(audio)
    removed: list[str] = []
    for target in removable:
        try:
            target.resolve().relative_to(project)
        except ValueError:
            continue
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(str(target.relative_to(project)))
        elif target.is_file():
            target.unlink()
            removed.append(str(target.relative_to(project)))
    return {"removed": removed}
