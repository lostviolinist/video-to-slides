# Editable Presentation Handoff

Use the installed Presentations skill after the evidence pack validates. This reference adds only video-specific requirements; all presentation authoring, rendering, and overlap rules remain controlled by that skill.

## Authoring contract

- Treat `slide_briefs.json` as the narrative source and `evidence.json` as the factual boundary.
- Treat `visual_dna.json` and the selected design audition as the visual contract. For visually distinctive sources, prefer source-native or editorial-remix composition; reserve a neutral editorial direction for visually weak sources.
- Vary adjacent silhouettes deliberately. Do not repeat a fixed eyebrow-title-divider-split-panel formula or add generic cards, pills, gradients, and rounded frames absent from the source.
- When Paper was used, reconstruct from `paper_handoff.json`, JSX, and computed styles so audience-facing text, shapes, charts, and simple diagrams remain editable. Paper screenshots are QA references, not slide backgrounds.
- Keep text, charts, tables, and simple diagrams editable. The only intentionally rasterized content is an original source frame or an explicitly generated illustration.
- Use a source frame only when it is legible at its final crop and materially clarifies the idea. Add a small timestamp to the image caption.
- Do not reproduce an on-screen chart as new data unless its labels and values are readable and mapped to evidence. Otherwise use the original frame with attribution.
- Keep the title slide minimal and do not expose evidence IDs or process language in visible copy.

## Speaker notes

Every slide needs a `[Sources]` block containing the canonical timestamped video URL or local filename, supporting evidence IDs, transcript segment IDs, and any source-frame IDs.

```text
[Sources]
- https://www.youtube.com/watch?v=VIDEO_ID&t=125s
- Evidence: ev-001
- Transcript: tr-0012, tr-0013
- Frame: fr-0042
[/Sources]
```

## Final QA

Render and inspect every slide individually. Confirm each visible claim against its evidence card, each screenshot against its timestamp, and every image crop at full-slide size. Reject duplicate or blurry source frames. Run the presentation overflow test and the evidence validator before delivery.
