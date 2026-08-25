# Troubleshooting

## Setup

- Missing `.venv`: run `scripts/setup.sh`.
- Incompatible system Python: call `load_workspace_dependencies` and pass its Python executable as `VTS_PYTHON` when running setup.
- Missing FFmpeg: rerun setup; `imageio-ffmpeg` supplies the skill-local executable.
- Whisper model not cached: obtain approval, then repeat `prepare` with `--allow-model-download`.
- `No Metal device available`: the environment is installed, but transcription is sandboxed. Rerun the explicit `prepare` command with unsandboxed approval.

## YouTube acquisition

- Login, age, geo, membership, or private-video errors: request a local file. Use browser cookies only after explicit authorization and never persist copied cookies in the evidence pack.
- No requested subtitle language: preparation selects a source-language manual caption, then an automatic caption, then ASR.
- Targeted high-resolution extraction failure: keep the logged warning and use the timestamp-matched scout frame.

## Transcript quality

- Large caption gaps, high repetition, implausible word rate, or poor distributed spot-check agreement trigger full ASR in adaptive mode.
- Music, silence, or visual-only material triggers `visual-storyboard` analysis. Do not manufacture a spoken thesis.
- Preserve raw captions and ASR results when sources disagree; record the disagreement as uncertainty.

## Validation

- Missing evidence references: repair `slide_briefs.json`; never remove the requirement.
- Missing selected frame: run `extract-selected` for the referenced frame ID or change the slide visual.
- More than 20 automatically generated slides: consolidate repeated themes. Exceed 20 only when the user explicitly supplied a larger count.
