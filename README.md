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

## Example output

This sample comes from [3Blue1Brown's *Transformers, the tech behind LLMs*](https://youtu.be/wjZofJX0v4M), using adaptive accuracy and the optional Paper design route.

[Download the editable sample deck](examples/wjZofJX0v4M/transformers-paper-redesign.pptx)

![Montage of the 13-slide sample deck](examples/wjZofJX0v4M/preview.png)

This is the expected shape of the result: a concise visual briefing, selective source frames, editable explanatory elements, and timestamped evidence in the speaker notes.

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
--transcription auto|captions|local
--review-outline
--design auto|paper|native
--design-mode auto|source-native|editorial-remix|independent
--review-design
--style <description>
--output <path>
--keep-media
```

### Without a local Whisper model

The default `--transcription auto` mode now uses structurally sound YouTube captions without downloading Whisper weights. If the model is already cached—or you explicitly approve its download—the skill can additionally run distributed speech-recognition checks.

Use `--transcription captions` to guarantee a model-free run. This works with manual or automatic YouTube captions; captionless videos and local media still require local transcription or a separately supplied transcript. `--transcription local` forces MLX Whisper, and `--accuracy deep` always requires it.

Setup installs the transcription software but not its large model weights.

## Paper design route (optional)

Paper is an optional design canvas: the skill uses it to audition the deck's palette, typography, and layouts before rebuilding the chosen direction as editable PowerPoint elements.

To connect Paper to Codex:

1. [Install Paper Desktop](https://paper.design/downloads), sign in, and open any Paper file. Opening a file starts Paper's local MCP server.
2. In Codex, open **Settings → MCP Servers**, add a **Streamable HTTP** server named `paper`, and use `http://127.0.0.1:29979/mcp` as the URL.
3. Save, restart Codex, and verify the connection by asking: “Create a red rectangle in Paper.”
4. Generate with `--design paper`, or leave the default `--design auto` so the skill uses Paper when connected and the native source-aware presentation workflow when it is not.

See [Paper's MCP documentation](https://paper.design/docs/mcp) for plugin installation and troubleshooting.

## Design philosophy

The default workflow is source-aware rather than template-first. It extracts a video's visual DNA—palette, typography, composition, recurring graphic language, pacing, and image treatment—and uses that to select a coherent deck direction. When Paper is available, the skill creates and reviews a small design audition before reconstructing the chosen system as editable PowerPoint elements. Paper is never required: `--design auto` falls back to the same source-aware design brief and QA process natively.

## Accuracy and source handling

- Complete manual captions are preferred when reliable.
- Adaptive mode audits caption coverage and runs distributed speech-recognition spot checks only when the local model is already present or approved.
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
