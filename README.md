# video-to-slides

Turn any YouTube video into a PowerPoint deck that you can flip through easily and quickly. The skill watches any video, identifies its most important points, and turns it into an informational PPT deck.

I made this skill for myself because I want to learn from the many YouTube videos out there, but I don't have the attention span to listen for an hour straight!

## What it produces

- An editable `.pptx` deck, normally 8–16 slides and never more than 20 automatically
- Timestamped raw and normalized transcripts
- Selected high-resolution source frames
- Evidence cards and claim-to-source mappings
- Slide briefs with `[Sources]` blocks for speaker notes
- Optional source-aware art direction through Paper

## Install

Clone the repository into your Codex skills directory:

```bash
git clone https://github.com/lostviolinist/video-to-slides.git ~/.codex/skills/video-to-slides
```

Then restart Codex so it discovers the skill. Its Python environment and media-analysis dependencies can be prepared with:

```bash
bash ~/.codex/skills/video-to-slides/scripts/setup.sh
```

## Use

Ask Codex naturally:

```text
Turn this video into slides: https://youtu.be/VIDEO_ID
```

Useful options include:

```text
--accuracy adaptive|deep|fast
--purpose briefing|study|action
--slides auto|N
--output-language <code>
--review-outline
--design auto|paper|native
--design-mode auto|source-native|editorial-remix|independent
--review-design
--style <description>
--output <path>
--keep-media
```

## Design philosophy

The default workflow is source-aware rather than template-first. It extracts a video's visual DNA—palette, typography, composition, recurring graphic language, pacing, and image treatment—and uses that to select a coherent deck direction. When Paper is available, the skill creates and reviews a small design audition before reconstructing the chosen system as editable PowerPoint elements.

## Accuracy and source handling

- Complete manual captions are preferred when reliable.
- Adaptive mode audits caption coverage and runs distributed speech-recognition spot checks.
- Full transcription is used when captions are absent, incomplete, noisy, or materially inconsistent.
- Long videos are processed hierarchically across the entire timeline, not just the opening.
- Screenshots are retained only when they materially improve fidelity; charts and diagrams are recreated only when their values and relationships are supported.
- Users are responsible for having permission to download, analyze, and reuse source media.

## Development

Run the test suite with:

```bash
bash tests/run_tests.sh
```

The implementation is Mac-optimized and uses a packaged FFmpeg path, avoiding a Homebrew requirement.
