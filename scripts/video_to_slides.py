#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
os.environ["PATH"] = str(Path(sys.executable).resolve().parent) + os.pathsep + os.environ.get("PATH", "")

from vts.models import read_json
from vts.evaluate import evaluate_and_write
from vts.pipeline import cleanup_project, extract_selected, prepare_project
from vts.validate import validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and validate multimodal evidence for an editable video-derived deck."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Acquire and prepare transcript and visual evidence")
    prepare.add_argument("source")
    prepare.add_argument("--project", type=Path, required=True)
    prepare.add_argument("--accuracy", choices=["adaptive", "deep", "fast"], default="adaptive")
    prepare.add_argument("--purpose", choices=["briefing", "study", "action"], default="briefing")
    prepare.add_argument("--slides", default="auto")
    prepare.add_argument("--output-language", default="auto")
    prepare.add_argument(
        "--transcription",
        choices=["auto", "captions", "local"],
        default="auto",
        help="Use usable captions without a model when possible, require captions, or force local MLX Whisper",
    )
    prepare.add_argument("--keep-media", action="store_true")
    prepare.add_argument("--allow-model-download", action="store_true")

    selected = subparsers.add_parser("extract-selected", help="Extract selected frames at high resolution")
    selected.add_argument("--project", type=Path, required=True)
    group = selected.add_mutually_exclusive_group(required=True)
    group.add_argument("--ids", nargs="+")
    group.add_argument("--ids-file", type=Path)

    validate = subparsers.add_parser("validate", help="Validate the evidence pack and slide briefs")
    validate.add_argument("--project", type=Path, required=True)

    evaluate = subparsers.add_parser("eval", help="Evaluate evidence coverage and deck traceability")
    evaluate.add_argument("--project", type=Path, required=True)
    evaluate.add_argument("--pptx", type=Path, required=True)
    evaluate.add_argument(
        "--report",
        type=Path,
        help="Report path; defaults to <project>/eval.json",
    )

    cleanup = subparsers.add_parser("cleanup", help="Remove project-owned temporary media")
    cleanup.add_argument("--project", type=Path, required=True)
    return parser


def _ids_from_file(path: Path) -> list[str]:
    data = read_json(path)
    if isinstance(data, list):
        return [str(value) for value in data]
    if isinstance(data, dict) and isinstance(data.get("frame_ids"), list):
        return [str(value) for value in data["frame_ids"]]
    raise ValueError("IDs file must be a JSON array or an object with frame_ids")


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        result = prepare_project(
            source_value=args.source,
            project=args.project,
            accuracy=args.accuracy,
            purpose=args.purpose,
            slides=args.slides,
            output_language=args.output_language,
            transcription=args.transcription,
            keep_media=args.keep_media,
            allow_model_download=args.allow_model_download,
        )
    elif args.command == "extract-selected":
        frame_ids = args.ids if args.ids else _ids_from_file(args.ids_file)
        result = extract_selected(args.project, frame_ids)
    elif args.command == "validate":
        result = validate_project(args.project)
    elif args.command == "eval":
        result = evaluate_and_write(args.project, args.pptx, args.report)
    elif args.command == "cleanup":
        result = cleanup_project(args.project)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
