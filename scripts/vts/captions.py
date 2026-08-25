from __future__ import annotations

import html
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .models import TranscriptSegment


TIMECODE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NOISE_RE = re.compile(r"^\s*[\[(].{0,40}[\])\]]\s*$")


def parse_timecode(value: str) -> float:
    clean = value.replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Unsupported timecode: {value}")


def clean_caption_text(text: str) -> str:
    text = html.unescape(TAG_RE.sub(" ", text))
    text = text.replace("\u200b", " ").replace("\ufeff", " ")
    return SPACE_RE.sub(" ", text).strip()


def parse_caption_cues(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    raw: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = TIMECODE_RE.search(lines[index])
        if not match:
            index += 1
            continue
        start = parse_timecode(match.group("start"))
        end = parse_timecode(match.group("end"))
        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index])
            index += 1
        text = clean_caption_text(" ".join(text_lines))
        if text:
            raw.append({"start": start, "end": max(start, end), "text": text})
        index += 1
    return raw


def parse_caption_file(path: Path, source: str = "caption") -> list[TranscriptSegment]:
    return normalize_segments(parse_caption_cues(path), source=source)


def _token_overlap(left: str, right: str, max_tokens: int = 24) -> int:
    a = left.split()
    b = right.split()
    limit = min(len(a), len(b), max_tokens)
    for size in range(limit, 0, -1):
        if [t.casefold() for t in a[-size:]] == [t.casefold() for t in b[:size]]:
            if size > 1 or len(a[-1]) >= 4:
                return size
    return 0


def normalize_segments(
    raw: list[tuple[float, float, str]] | list[dict[str, Any]],
    source: str,
) -> list[TranscriptSegment]:
    merged: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start + float(item.get("duration", 0.0))))
            text = clean_caption_text(str(item.get("text", "")))
            confidence = item.get("confidence")
        else:
            start, end, value = item
            text = clean_caption_text(value)
            confidence = None
        if not text:
            continue
        entry = {
            "start": max(0.0, float(start)),
            "end": max(float(start), float(end)),
            "text": text,
            "confidence": confidence,
        }
        if not merged:
            merged.append(entry)
            continue
        previous = merged[-1]
        close = entry["start"] <= previous["end"] + 3.0
        previous_folded = previous["text"].casefold()
        current_folded = entry["text"].casefold()
        if close and current_folded == previous_folded:
            previous["end"] = max(previous["end"], entry["end"])
            continue
        if close and current_folded.startswith(previous_folded):
            previous["text"] = entry["text"]
            previous["end"] = max(previous["end"], entry["end"])
            continue
        if close and previous_folded.startswith(current_folded):
            previous["end"] = max(previous["end"], entry["end"])
            continue
        overlap = _token_overlap(previous["text"], entry["text"]) if close else 0
        if overlap:
            remainder = " ".join(entry["text"].split()[overlap:])
            if remainder:
                previous["text"] = f"{previous['text']} {remainder}"
            previous["end"] = max(previous["end"], entry["end"])
            continue
        merged.append(entry)

    return [
        TranscriptSegment(
            id=f"tr-{index:05d}",
            start=round(item["start"], 3),
            end=round(item["end"], 3),
            text=item["text"],
            source=source,
            confidence=item["confidence"],
        )
        for index, item in enumerate(merged, start=1)
    ]


def audit_captions(segments: list[TranscriptSegment], duration: float) -> dict[str, Any]:
    if not segments or duration <= 0:
        return {
            "score": 0.0,
            "span_ratio": 0.0,
            "max_gap_seconds": duration,
            "repetition_ratio": 1.0,
            "noise_ratio": 1.0,
            "words_per_minute": 0.0,
            "recommended_full_asr": True,
            "reasons": ["no usable caption segments"],
        }

    ordered = sorted(segments, key=lambda s: (s.start, s.end))
    span_ratio = max(0.0, min(1.0, (ordered[-1].end - ordered[0].start) / duration))
    gaps = [max(0.0, ordered[0].start)]
    gaps.extend(max(0.0, b.start - a.end) for a, b in zip(ordered, ordered[1:]))
    gaps.append(max(0.0, duration - ordered[-1].end))
    max_gap = max(gaps)
    normalized_texts = [SPACE_RE.sub(" ", s.text.casefold()).strip() for s in ordered]
    repetition_ratio = 1.0 - (len(set(normalized_texts)) / len(normalized_texts))
    noise_count = sum(1 for text in normalized_texts if NOISE_RE.match(text))
    noise_ratio = noise_count / len(normalized_texts)
    word_count = sum(len(s.text.split()) for s in ordered)
    speech_minutes = max((ordered[-1].end - ordered[0].start) / 60.0, 1 / 60)
    words_per_minute = word_count / speech_minutes

    span_score = min(1.0, span_ratio / 0.9)
    gap_score = max(0.0, 1.0 - max_gap / max(60.0, duration * 0.2))
    repeat_score = max(0.0, 1.0 - repetition_ratio * 3.0)
    noise_score = max(0.0, 1.0 - noise_ratio * 4.0)
    rate_score = 1.0 if 45 <= words_per_minute <= 240 else 0.55
    score = 0.35 * span_score + 0.25 * gap_score + 0.15 * repeat_score + 0.15 * noise_score + 0.10 * rate_score

    reasons: list[str] = []
    if span_ratio < 0.8:
        reasons.append("captions do not span most of the source")
    if max_gap > max(90.0, duration * 0.15):
        reasons.append("captions contain a large unexplained gap")
    if repetition_ratio > 0.18:
        reasons.append("captions contain excessive repetition")
    if noise_ratio > 0.12:
        reasons.append("captions contain excessive non-speech noise")
    if not 45 <= words_per_minute <= 240:
        reasons.append("caption word rate is implausible")

    return {
        "score": round(score, 4),
        "span_ratio": round(span_ratio, 4),
        "max_gap_seconds": round(max_gap, 3),
        "repetition_ratio": round(repetition_ratio, 4),
        "noise_ratio": round(noise_ratio, 4),
        "words_per_minute": round(words_per_minute, 2),
        "recommended_full_asr": score < 0.78 or bool(reasons),
        "reasons": reasons,
    }


def text_for_range(segments: list[TranscriptSegment], start: float, end: float) -> str:
    return " ".join(s.text for s in segments if s.end >= start and s.start <= end)


def transcript_similarity(left: str, right: str) -> float:
    normalize = lambda value: " ".join(re.findall(r"[\w']+", value.casefold()))
    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()
