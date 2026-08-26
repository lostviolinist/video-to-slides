# Evidence Pack Contract

All paths are relative to the project directory unless explicitly marked absolute. JSON must be UTF-8, two-space indented, and free of comments.

## Generated preparation files

- `source.json`: source kind, URL or immutable local path, title, duration, language, channel, chapters, acquisition details, and `keep_media`.
- `raw_transcript.json`: unaltered caption or ASR segments.
- `normalized_transcript.json`: cleaned timestamped segments with stable IDs.
- `caption_audit.json`: structural metrics, spot-check comparisons, selected transcript source, and the reason full ASR was or was not used.
- `timeline.json`: complete-duration windows and their transcript segment IDs, chapters, candidate frame IDs, and contact sheet paths.
- `frames/frame_manifest.json`: every accepted candidate's timestamp, source signal, perceptual hash, sharpness, and selected path when extracted.
- `visual_dna.json`: source-derived palette, typography, composition, image treatment, prohibited patterns, supporting frame IDs, and design-mode confidence.
- `paper_handoff.json`: optional Paper artboard, JSX, computed-style, and design-audition mappings used to reconstruct the editable PPTX.

## `evidence.json`

```json
{
  "analysis_mode": "multimodal",
  "cards": [
    {
      "id": "ev-001",
      "topic": "Stable topic label",
      "role": "thesis|claim|evidence|example|caveat|conclusion",
      "summary": "Faithful concise statement",
      "start": 125.4,
      "end": 171.2,
      "transcript_segment_ids": ["tr-0012"],
      "frame_ids": ["fr-0042"],
      "confidence": 0.92,
      "scores": {
        "thesis_relevance": 4,
        "evidence_strength": 5,
        "uniqueness": 4,
        "visual_value": 3,
        "structural_importance": 4
      },
      "weighted_score": 4.2,
      "uncertainty": null
    }
  ]
}
```

Each component score is an integer from 0–5. Compute `weighted_score` as 35% thesis relevance, 25% evidence strength, 20% uniqueness, 10% visual value, and 10% structural importance. Penalize sponsor material, repetition, and weakly supported interpretation by lowering the applicable components; do not hide them in the formula.

## `slide_briefs.json`

```json
{
  "deck_title": "Source-faithful title",
  "purpose": "briefing",
  "audience": "informed general viewer",
  "output_language": "en",
  "visual_direction": "source-native mathematical explainer",
  "slides": [
    {
      "number": 1,
      "role": "title|introduction|body|conclusion",
      "title": "Answer-first slide title",
      "message": "One main audience-facing message",
      "evidence_ids": ["ev-001"],
      "visual": {
        "kind": "source-frame|editable-chart|editable-diagram|generated|none",
        "frame_id": "fr-0042",
        "instruction": "How the visual supports the message"
      },
      "visible_content": ["Short supported point"],
      "speaker_notes": "Optional context, not hidden unsupported claims"
    }
  ]
}
```

Every substantive slide must reference at least one evidence card. Title and closing slides may reuse source-level metadata but must still cite the source URL in notes. Source frames must exist in `frames/selected/`. Never invent values to make a chart look complete.

## Required narrative bookends

Use these slide roles and order:

1. `title`: a minimal source-faithful title slide.
2. `introduction`: a dedicated executive summary of what the video is really saying. State the central thesis and map the three to five ideas the audience should carry through the deck. Ground it in the strongest thesis and conclusion evidence; do not make it an agenda, teaser, motivational quote, hype statement, or generic “why this matters” slide.
3. `body`: the evidence-backed argument, examples, tools, caveats, or demonstrations.
4. `conclusion`: a final synthesis that answers the video's main question and gives the audience closure. Distill the overall answer, the most important implication or practical use, and any material caveat. Do not introduce new claims, end on the final chronological topic, or use a generic thank-you or inspirational slogan.

The introduction and conclusion count toward the requested slide total. Visually distinguish both from ordinary body slides so the beginning and ending are clear without turning them into decorative section dividers.
