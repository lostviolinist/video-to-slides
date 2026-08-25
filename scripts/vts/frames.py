from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


PTS_RE = re.compile(r"pts_time:(?P<value>-?\d+(?:\.\d+)?)")


def discover_ffmpeg() -> str:
    explicit = os.environ.get("VTS_FFMPEG")
    if explicit and Path(explicit).is_file():
        return explicit
    candidate = shutil.which("ffmpeg")
    if candidate:
        return candidate
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("FFmpeg is unavailable; run scripts/setup.sh") from exc


def run_ffmpeg(arguments: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [discover_ffmpeg(), "-hide_banner"] + arguments
    return subprocess.run(
        command,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def extract_frame(source: Path, timestamp: float, output: Path, width: int = 1920) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-loglevel",
            "error",
            "-ss",
            f"{max(0, timestamp):.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:-2:force_original_aspect_ratio=decrease",
            "-q:v",
            "2",
            "-y",
            str(output),
        ]
    )
    if not output.is_file():
        raise FileNotFoundError(f"FFmpeg did not produce {output}")
    return output


def _heartbeat_frames(source: Path, destination: Path, interval: float) -> list[dict[str, Any]]:
    template = destination / "heartbeat_%06d.jpg"
    run_ffmpeg(
        [
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            f"fps=1/{interval},scale=960:-2:force_original_aspect_ratio=decrease",
            "-q:v",
            "3",
            "-y",
            str(template),
        ]
    )
    return [
        {
            "timestamp": round((index - 1) * interval, 3),
            "signal": "heartbeat",
            "path": str(path),
        }
        for index, path in enumerate(sorted(destination.glob("heartbeat_*.jpg")), start=1)
    ]


def _scene_frames(source: Path, destination: Path, threshold: float) -> list[dict[str, Any]]:
    template = destination / "scene_%06d.jpg"
    filter_value = (
        f"select=gt(scene\\,{threshold}),showinfo,"
        "scale=960:-2:force_original_aspect_ratio=decrease"
    )
    result = run_ffmpeg(
        [
            "-loglevel",
            "info",
            "-i",
            str(source),
            "-vf",
            filter_value,
            "-fps_mode",
            "vfr",
            "-q:v",
            "3",
            "-y",
            str(template),
        ]
    )
    timestamps = [float(match.group("value")) for match in PTS_RE.finditer(result.stderr)]
    files = sorted(destination.glob("scene_*.jpg"))
    return [
        {
            "timestamp": round(timestamps[index] if index < len(timestamps) else 0.0, 3),
            "signal": "scene-change",
            "path": str(path),
        }
        for index, path in enumerate(files)
    ]


def _chapter_frames(
    source: Path, destination: Path, chapters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for index, chapter in enumerate(chapters, start=1):
        timestamp = float(chapter.get("start_time", chapter.get("start", 0)))
        path = destination / f"chapter_{index:06d}.jpg"
        try:
            extract_frame(source, timestamp + 0.35, path, width=960)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        frames.append(
            {
                "timestamp": round(timestamp + 0.35, 3),
                "signal": "chapter-boundary",
                "chapter_title": chapter.get("title"),
                "path": str(path),
            }
        )
    return frames


def _image_features(path: Path) -> tuple[str, str, float]:
    from PIL import Image, ImageFilter, ImageStat
    import imagehash

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        perceptual_hash = str(imagehash.phash(rgb))
        color_hash = str(imagehash.colorhash(rgb))
        edges = rgb.convert("L").filter(ImageFilter.FIND_EDGES)
        sharpness = float(ImageStat.Stat(edges).stddev[0])
    return perceptual_hash, color_hash, round(sharpness, 4)


def _hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def deduplicate_frames(
    candidates: list[dict[str, Any]],
    hash_distance: int = 6,
    color_hash_distance: int = 4,
    sharpness_floor: float = 4.0,
) -> list[dict[str, Any]]:
    priority = {"chapter-boundary": 0, "scene-change": 1, "heartbeat": 2}
    enriched: list[dict[str, Any]] = []
    for item in candidates:
        path = Path(item["path"])
        if not path.is_file():
            continue
        image_hash, color_hash, sharpness = _image_features(path)
        enriched.append(
            {
                **item,
                "perceptual_hash": image_hash,
                "color_hash": color_hash,
                "sharpness": sharpness,
            }
        )
    enriched.sort(key=lambda item: (float(item["timestamp"]), priority.get(item["signal"], 9)))

    kept: list[dict[str, Any]] = []
    for candidate in enriched:
        if candidate["sharpness"] < sharpness_floor:
            continue
        duplicate_index = next(
            (
                index
                for index, prior in enumerate(kept)
                if _hamming(candidate["perceptual_hash"], prior["perceptual_hash"])
                <= hash_distance
                and _hamming(candidate["color_hash"], prior["color_hash"])
                <= color_hash_distance
            ),
            None,
        )
        if duplicate_index is None:
            kept.append(candidate)
            continue
        prior = kept[duplicate_index]
        candidate_priority = priority.get(candidate["signal"], 9)
        prior_priority = priority.get(prior["signal"], 9)
        if candidate_priority < prior_priority or candidate["sharpness"] > prior["sharpness"] * 1.35:
            kept[duplicate_index] = candidate

    kept.sort(key=lambda item: float(item["timestamp"]))
    return [
        {
            **item,
            "id": f"fr-{index:05d}",
            "path": str(Path(item["path"])),
            "selected_path": None,
        }
        for index, item in enumerate(kept, start=1)
    ]


def extract_candidates(
    source: Path,
    destination: Path,
    duration: float,
    chapters: list[dict[str, Any]],
    accuracy: str,
) -> list[dict[str, Any]]:
    destination.mkdir(parents=True, exist_ok=True)
    interval = 40.0 if accuracy == "fast" else 20.0
    threshold = 0.36 if accuracy == "fast" else 0.28
    candidates = _heartbeat_frames(source, destination, interval)
    candidates.extend(_scene_frames(source, destination, threshold))
    candidates.extend(_chapter_frames(source, destination, chapters))
    candidates = [item for item in candidates if float(item["timestamp"]) <= duration + 1]
    return deduplicate_frames(candidates)


def build_contact_sheets(
    frames: list[dict[str, Any]],
    destination: Path,
    bucket_seconds: float = 300.0,
    cells_per_sheet: int = 12,
) -> list[dict[str, Any]]:
    from PIL import Image, ImageDraw, ImageOps

    destination.mkdir(parents=True, exist_ok=True)
    buckets: dict[int, list[dict[str, Any]]] = {}
    for frame in frames:
        bucket = int(float(frame["timestamp"]) // bucket_seconds)
        buckets.setdefault(bucket, []).append(frame)

    records: list[dict[str, Any]] = []
    cell_width, cell_height, label_height = 360, 210, 28
    columns, rows = 3, 4
    for bucket, items in sorted(buckets.items()):
        for page, offset in enumerate(range(0, len(items), cells_per_sheet), start=1):
            page_items = items[offset : offset + cells_per_sheet]
            canvas = Image.new("RGB", (columns * cell_width, rows * (cell_height + label_height)), "white")
            draw = ImageDraw.Draw(canvas)
            frame_ids: list[str] = []
            for cell, item in enumerate(page_items):
                row, column = divmod(cell, columns)
                x, y = column * cell_width, row * (cell_height + label_height)
                with Image.open(item["path"]) as image:
                    thumb = ImageOps.contain(image.convert("RGB"), (cell_width, cell_height))
                    image_x = x + (cell_width - thumb.width) // 2
                    image_y = y + (cell_height - thumb.height) // 2
                    canvas.paste(thumb, (image_x, image_y))
                timestamp = float(item["timestamp"])
                minutes, seconds = divmod(int(timestamp), 60)
                label = f"{item['id']}  {minutes}:{seconds:02d}  {item['signal']}"
                draw.rectangle((x, y + cell_height, x + cell_width, y + cell_height + label_height), fill="white")
                draw.text((x + 6, y + cell_height + 6), label, fill="black")
                frame_ids.append(item["id"])
            path = destination / f"contact_{bucket:04d}_{page:02d}.jpg"
            canvas.save(path, quality=90)
            records.append(
                {
                    "id": f"sheet-{len(records) + 1:04d}",
                    "start": bucket * bucket_seconds,
                    "end": (bucket + 1) * bucket_seconds,
                    "path": str(path),
                    "frame_ids": frame_ids,
                }
            )
    return records
