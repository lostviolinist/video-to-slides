#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SKILL_DIR/.venv"

PYTHON_BIN="${VTS_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    candidate_path="$(command -v "$candidate" || true)"
    if [[ -n "$candidate_path" ]] && "$candidate_path" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
      PYTHON_BIN="$candidate_path"
      break
    fi
  done
fi
if [[ -z "$PYTHON_BIN" ]] || [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.10+ is required. In Codex, set VTS_PYTHON to the bundled Python path from load_workspace_dependencies." >&2
  exit 1
fi
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
  echo "VTS_PYTHON must point to Python 3.10 or newer." >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
elif ! "$VENV_DIR/bin/python" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
  echo "Existing $VENV_DIR uses an incompatible Python. Move it aside and rerun setup." >&2
  exit 1
fi

"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check --upgrade pip
"$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt"

FFMPEG_PATH="$("$VENV_DIR/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
ln -sfn "$FFMPEG_PATH" "$VENV_DIR/bin/ffmpeg"

"$VENV_DIR/bin/python" "$SCRIPT_DIR/check_env.py"
echo "Setup complete. Whisper model weights download only when transcription is first approved."
