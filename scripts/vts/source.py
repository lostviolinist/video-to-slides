from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}


def is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and parsed.hostname in YOUTUBE_HOSTS


def youtube_video_id(value: str) -> str | None:
    if not is_youtube_url(value):
        return None
    parsed = urlparse(value)
    if parsed.hostname == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
        candidate = parsed.path.strip("/").split("/")[1]
    else:
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    return candidate if re.fullmatch(r"[A-Za-z0-9_-]{6,20}", candidate or "") else None


def classify_source(value: str) -> tuple[str, Path | None]:
    if is_youtube_url(value):
        return "youtube", None
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Local source does not exist: {path}")
    suffix = path.suffix.casefold()
    if suffix in VIDEO_SUFFIXES:
        return "local-video", path
    if suffix in AUDIO_SUFFIXES:
        return "local-audio", path
    raise ValueError(f"Unsupported local media type: {path.suffix}")


def run_checked(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def yt_dlp_base() -> list[str]:
    command = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-warnings"]
    try:
        import imageio_ffmpeg

        command.extend(["--ffmpeg-location", imageio_ffmpeg.get_ffmpeg_exe()])
    except Exception:
        # Metadata and simple downloads may still work without post-processing.
        # Operations that require FFmpeg will surface yt-dlp's concrete error.
        pass
    return command


def youtube_metadata(url: str) -> dict[str, Any]:
    result = run_checked(yt_dlp_base() + ["--dump-single-json", "--skip-download", url])
    return json.loads(result.stdout)


def choose_caption(metadata: dict[str, Any], requested_language: str = "auto") -> tuple[str, str] | None:
    manual = metadata.get("subtitles") or {}
    automatic = metadata.get("automatic_captions") or {}
    language = requested_language if requested_language != "auto" else str(metadata.get("language") or "")

    def pick(mapping: dict[str, Any]) -> str | None:
        if language and language in mapping:
            return language
        if language:
            prefix = language.split("-")[0]
            for key in mapping:
                if key.split("-")[0] == prefix:
                    return key
        for preferred in ("en", "en-US", "en-GB"):
            if preferred in mapping:
                return preferred
        return next(iter(mapping), None)

    selected = pick(manual)
    if selected:
        return "manual-caption", selected
    selected = pick(automatic)
    if selected:
        return "automatic-caption", selected
    return None


def download_caption(url: str, destination: Path, kind: str, language: str) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    option = "--write-subs" if kind == "manual-caption" else "--write-auto-subs"
    template = str(destination / "caption.%(ext)s")
    command = yt_dlp_base() + [
        option,
        "--sub-langs",
        language,
        "--sub-format",
        "vtt",
        "--skip-download",
        "-o",
        template,
        url,
    ]
    run_checked(command)
    candidates = sorted(destination.glob("caption*.vtt"))
    if not candidates:
        raise FileNotFoundError(f"yt-dlp did not produce a VTT caption for {language}")
    return candidates[0]


def download_scout(url: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    command = yt_dlp_base() + [
        "-f",
        "bv*[height<=360]/b[height<=360]/worst",
        "--print",
        "after_move:filepath",
        "-o",
        str(destination / "scout.%(ext)s"),
        url,
    ]
    result = run_checked(command)
    path = Path(result.stdout.strip().splitlines()[-1]).resolve()
    if not path.is_file():
        candidates = sorted(destination.glob("scout.*"))
        if not candidates:
            raise FileNotFoundError("yt-dlp did not produce scouting media")
        path = candidates[0]
    return path


def download_audio(url: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    command = yt_dlp_base() + [
        "-x",
        "--audio-format",
        "wav",
        "--print",
        "after_move:filepath",
        "-o",
        str(destination / "audio.%(ext)s"),
        url,
    ]
    result = run_checked(command)
    path = Path(result.stdout.strip().splitlines()[-1]).resolve()
    if not path.is_file():
        candidates = sorted(destination.glob("audio.*"))
        if not candidates:
            raise FileNotFoundError("yt-dlp did not produce audio media")
        path = candidates[0]
    return path


def download_section(url: str, destination: Path, start: float, end: float) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = yt_dlp_base() + [
        "--download-sections",
        f"*{max(0, start):.3f}-{max(start + 0.25, end):.3f}",
        "--force-keyframes-at-cuts",
        "-f",
        "bv*[height<=1080]+ba/b[height<=1080]",
        "--merge-output-format",
        "mp4",
        "--print",
        "after_move:filepath",
        "-o",
        str(destination.with_suffix(".%(ext)s")),
        url,
    ]
    result = run_checked(command)
    path = Path(result.stdout.strip().splitlines()[-1]).resolve()
    if not path.is_file():
        raise FileNotFoundError("yt-dlp did not produce the requested clip")
    return path


def local_duration(ffmpeg: str, source: Path) -> float:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(source)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise ValueError(f"Could not determine duration for {source}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
