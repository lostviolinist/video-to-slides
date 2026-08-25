#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path


def main() -> int:
    required = ["yt_dlp", "imageio_ffmpeg", "mlx_whisper", "PIL", "imagehash", "pydantic"]
    modules = {name: importlib.util.find_spec(name) is not None for name in required}
    ffmpeg = None
    if modules["imageio_ffmpeg"]:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    mlx_runtime = False
    mlx_runtime_error = None
    if modules["mlx_whisper"]:
        try:
            import mlx_whisper  # noqa: F401

            mlx_runtime = True
        except Exception as exc:
            mlx_runtime_error = str(exc)
    result = {
        "ok": all(modules.values()) and bool(ffmpeg and Path(ffmpeg).is_file()),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "modules": modules,
        "ffmpeg": ffmpeg,
        "mlx_runtime": mlx_runtime,
        "mlx_runtime_error": mlx_runtime_error,
        "note": (
            "MLX requires an approved unsandboxed prepare command to access Metal."
            if modules["mlx_whisper"] and not mlx_runtime
            else None
        ),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
