from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from .captions import normalize_segments
from .frames import discover_ffmpeg, run_ffmpeg
from .models import TranscriptSegment


TURBO_MODEL = "mlx-community/whisper-large-v3-turbo"
DEEP_MODEL = "mlx-community/whisper-large-v3-mlx"


def model_cache_root() -> Path:
    configured = os.environ.get("HF_HOME")
    if configured:
        return Path(configured).expanduser().resolve() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def model_is_cached(model: str) -> bool:
    slug = "models--" + model.replace("/", "--")
    root = model_cache_root() / slug
    snapshots = root / "snapshots"
    return snapshots.is_dir() and any(snapshots.iterdir())


def require_model_permission(model: str, allow_download: bool) -> None:
    if model_is_cached(model) or allow_download:
        return
    raise PermissionError(
        f"Transcription requires {model}, which is not cached. "
        "Obtain user approval for the model download, then rerun with --allow-model-download."
    )


def transcribe_file(
    audio: Path,
    model: str,
    allow_download: bool,
    source: str = "asr",
) -> list[TranscriptSegment]:
    require_model_permission(model, allow_download)
    try:
        import mlx_whisper
    except ImportError as exc:
        if "No Metal device available" in str(exc):
            raise RuntimeError(
                "MLX cannot access Metal in the current sandbox. Rerun prepare as an approved unsandboxed command."
            ) from exc
        raise RuntimeError("mlx-whisper is unavailable; run scripts/setup.sh") from exc

    # mlx-whisper invokes `ffmpeg` by name. Make the skill-bundled binary
    # discoverable for that subprocess without requiring Homebrew or a
    # machine-wide PATH change.
    original_path = os.environ.get("PATH")
    with tempfile.TemporaryDirectory(prefix="vts-tools-") as tool_directory:
        ffmpeg_alias = Path(tool_directory) / "ffmpeg"
        ffmpeg_alias.symlink_to(discover_ffmpeg())
        os.environ["PATH"] = os.pathsep.join(
            part for part in (tool_directory, original_path or "") if part
        )
        try:
            result: dict[str, Any] = mlx_whisper.transcribe(
                str(audio),
                path_or_hf_repo=model,
                word_timestamps=True,
                condition_on_previous_text=True,
                verbose=False,
            )
        finally:
            if original_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = original_path
    raw = [
        {
            "start": segment.get("start", 0.0),
            "end": segment.get("end", segment.get("start", 0.0)),
            "text": segment.get("text", ""),
            "confidence": _segment_confidence(segment),
        }
        for segment in result.get("segments", [])
    ]
    return normalize_segments(raw, source=source)


def _segment_confidence(segment: dict[str, Any]) -> float | None:
    average_logprob = segment.get("avg_logprob")
    if average_logprob is None:
        return None
    value = max(0.0, min(1.0, 1.0 + float(average_logprob)))
    return round(value, 4)


def transcribe_sample(
    audio: Path,
    start: float,
    length: float,
    model: str,
    allow_download: bool,
) -> str:
    with tempfile.TemporaryDirectory(prefix="vts-sample-") as temporary:
        clip = Path(temporary) / "sample.wav"
        run_ffmpeg(
            [
                "-loglevel",
                "error",
                "-ss",
                f"{max(0, start):.3f}",
                "-t",
                f"{length:.3f}",
                "-i",
                str(audio),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-y",
                str(clip),
            ]
        )
        segments = transcribe_file(clip, model, allow_download, source="asr-spot-check")
        return " ".join(segment.text for segment in segments)
