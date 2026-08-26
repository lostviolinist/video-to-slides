# Evidence-First Workflow

## Preflight and setup

Set `VTS_SKILL_DIR` to this skill's absolute directory. Run:

```bash
"$VTS_SKILL_DIR/.venv/bin/python" "$VTS_SKILL_DIR/scripts/check_env.py"
```

If the environment is missing, call `load_workspace_dependencies`, set `VTS_PYTHON` to its bundled Python executable, and run `bash "$VTS_SKILL_DIR/scripts/setup.sh"`; then repeat the check. Python 3.10+ is required. Setup installs a skill-local toolchain and does not download Whisper weights. A captioned YouTube video can run without those weights; the first operation that genuinely needs local transcription stops unless `--allow-model-download` is passed after user approval.

Create the project under a writable, conversation-specific work directory. Keep only final deliverables in the host output directory.

YouTube acquisition requires network access, and MLX transcription requires Apple Metal access. Run `prepare` as an approved unsandboxed command whenever either applies. This approval covers only the explicit skill command and project/source paths; it does not authorize browser-cookie access.

## Prepare

```bash
"$VTS_SKILL_DIR/.venv/bin/python" "$VTS_SKILL_DIR/scripts/video_to_slides.py" prepare \
  "<source>" --project "<absolute-project-dir>" \
  --accuracy adaptive --purpose briefing --slides auto --transcription auto
```

Add `--output-language`, `--keep-media`, or `--allow-model-download` only when applicable. Preparation writes source metadata, raw and normalized transcripts, seven-minute timeline windows with 30-second overlap, candidate-frame metadata, and five-minute contact sheets.

### Transcription modes

- `auto` (default): use structurally sound YouTube captions without downloading a model. If the MLX model is already cached or approved, use it for distributed spot checks. Require transcription only when captions are absent or structurally unreliable.
- `captions`: never use or download a local model. Continue with manual or automatic captions and preserve the caption audit so downstream evidence can reflect lower confidence. Stop when the source has no usable captions.
- `local`: force full MLX Whisper transcription. `deep` accuracy also requires local transcription.

There is no cloud transcription provider in this release. Captionless local files and captionless YouTube videos therefore need the approved local model or a separately supplied transcript.

## Analyze every window

Read `timeline.json`. For each window:

1. Read the linked normalized transcript segments.
2. Inspect the window's contact sheet; open promising frames individually at original candidate resolution.
3. Record claims, evidence, examples, caveats, conclusions, and useful visuals as evidence cards.
4. Mark uncertainty explicitly. Preserve exact numbers and proper nouns only when visible or spoken clearly.

After all windows, cluster semantic duplicates and rank the surviving cards using the schema weights. Enforce coverage of every major topic cluster, the strongest supporting evidence, material limitations or disagreement, and the ending conclusion. Chapters may influence boundaries but never replace whole-video analysis.

For sparse speech, describe only what the visible sequence supports and set `analysis_mode` to `visual-storyboard` with lower confidence.

## Select high-resolution frames

Write an array of selected candidate frame IDs to `selected_frame_ids.json`, then run:

```bash
"$VTS_SKILL_DIR/.venv/bin/python" "$VTS_SKILL_DIR/scripts/video_to_slides.py" extract-selected \
  --project "<absolute-project-dir>" --ids-file "<absolute-project-dir>/selected_frame_ids.json"
```

For YouTube sources, the helper attempts short targeted clips at up to 1080p and falls back to the scouting media. For local sources it extracts directly without modifying the original.

## Validate, evaluate, and clean

Before deck authoring, run `validate`. Run it again after updating slide briefs or selected frames. After the final PPTX has passed presentation rendering and overflow checks, run `eval`; it saves `eval.json` in the project. Complete the visual review in `evals/rubric.md` and save `semantic_eval.json`. Fix and rerun both checks until they pass, then run `cleanup`; it removes only project-owned scout media, rejected candidates, contact sheets, and temporary clips.
