---
name: video-to-slides
description: Turn one YouTube URL or local video/audio file into an evidence-backed editable PowerPoint with source-aware art direction by analyzing captions or speech, scene changes, and important on-screen visuals. Use when the user asks to watch, summarize, study, brief, or extract slides from a video. Do not use for downloading media without analysis or for editing an existing deck.
---

# Video to Slides

Create a faithful editable deck from the complete video, not from captions alone. Default to a one-shot 8–16-slide briefing for an informed general audience, preserve the source language, and keep the result at or below 20 slides unless the user explicitly asks otherwise.

## Inputs

Accept one public/accessibly unlisted YouTube URL or one local video/audio file.

Parse these optional controls from the request:

- `--accuracy adaptive|deep|fast` (default `adaptive`)
- `--purpose briefing|study|action` (default `briefing`)
- `--slides auto|N` (default `auto`)
- `--output-language CODE` (default source language)
- `--review-outline`
- `--design auto|paper|native` (default `auto`)
- `--design-mode auto|source-native|editorial-remix|independent` (default `auto`)
- `--review-design`
- `--style DESCRIPTION`
- `--output PATH`
- `--keep-media`

If a new presentation's audience or purpose is not stated, use the defaults above without asking. Ask only when a missing choice would materially alter a specialized deliverable.

## Required Workflow

1. Read [references/workflow.md](references/workflow.md) and run the preflight command it specifies.
2. Prepare the source project with `scripts/video_to_slides.py prepare`. This gathers metadata, audits captions against audio when appropriate, transcribes when required, samples the whole visual timeline, deduplicates frames, and creates timestamped contact sheets.
3. Inspect every contact sheet and every transcript window. Write `evidence.json` and `slide_briefs.json` using [references/evidence-schema.md](references/evidence-schema.md). Do not infer claims, numbers, names, or causal relationships absent from the evidence.
4. Extract only the selected source frames at high resolution with `scripts/video_to_slides.py extract-selected`.
5. If `--review-outline` was requested, show the slide titles, messages, and evidence timestamps, then pause before authoring.
6. Read [references/design-handoff.md](references/design-handoff.md). Derive `visual_dna.json` from representative source frames before choosing layouts. When Paper is connected and `--design` is `auto` or `paper`, use Paper for the design board and three-slide audition; otherwise use the native source-aware route. If `--review-design` was requested, show the audition and pause before building the complete deck.
7. Read [references/presentation-handoff.md](references/presentation-handoff.md), use the installed Presentations skill to reconstruct the selected direction as an editable PPTX, and put timestamped provenance in `[Sources]` speaker-note blocks. Do not flatten Paper artboards into full-slide screenshots.
8. Run `scripts/video_to_slides.py validate`, render every slide, inspect each full-size render, and fix all accuracy, crop, overflow, overlap, repetitive-layout, and source-style fidelity defects.
9. After successful delivery, run `scripts/video_to_slides.py cleanup` unless `--keep-media` was requested. Retain the deck, normalized evidence pack, visual DNA, selected Paper design exports, and selected frames; never modify or remove a user-provided local source.

## Accuracy Rules

- Prefer complete manual captions, but do not assume captions are accurate.
- In `adaptive`, audit caption coverage and compare three distributed audio samples. Run full MLX Whisper transcription when captions are absent, incomplete, noisy, or materially disagree.
- In `deep`, always transcribe the complete audio and compare it with captions.
- In `fast`, use available captions and sparse visual sampling; if no transcript exists, transcription remains necessary.
- Before a first transcription model download, report the model and purpose and obtain approval. Pass `--allow-model-download` only after approval.
- Treat chapters as hints, not importance labels. Analyze the complete duration in bounded windows so long videos are not biased toward the opening.
- Prefer frames showing diagrams, charts, equations, code, UI states, demonstrations, examples, or consequential on-screen text. Reject blurry transitions, duplicate slides, generic B-roll, and non-substantive sponsor material.
- A clean slide is not permission to simplify away material caveats, disagreement, or the conclusion.
- Paper or another design tool may change composition and styling, but it must not introduce unsupported claims, quantities, diagrams, or relationships.

## Failures

For a restricted YouTube source, ask for a local file or explicit authorization before accessing browser cookies. If speech is sparse, switch to a visual-storyboard analysis and lower confidence. If `--design paper` was explicit and Paper is unavailable, stop at the design phase and report the exact connection failure; in `auto`, use the native source-aware fallback and disclose it. If setup, acquisition, transcription, design handoff, or validation fails, read [references/troubleshooting.md](references/troubleshooting.md), preserve the project for diagnosis, and report the exact blocking phase.
