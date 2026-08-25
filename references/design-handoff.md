# Source-Aware Design Handoff

Use this stage after the evidence pack and selected frames are stable. It controls art direction, not factual selection.

## Build `visual_dna.json`

Inspect representative title cards, diagrams, transitions, and dense explanatory frames. Record:

- `design_mode`: `source-native`, `editorial-remix`, or `independent`
- `palette`: colors with semantic roles and frame-derived rationale
- `typography`: serif/sans/mono categories, weight, casing, scale, and spacing
- `background`: color, texture, and contrast behavior
- `shape_language`: lines, grids, arrows, handwriting, photography, UI, or other recurring forms
- `composition`: alignment, asymmetry, density, whitespace, and dominant visual-to-text ratio
- `image_treatment`: crop, bleed, border, caption, and screenshot integration
- `motion_translation`: useful keyframe sequences or progressive-build ideas to express statically
- `prohibited_patterns`: generic treatments absent from the source, such as card grids, pills, gradient blobs, or repeated split panels
- `confidence`: visual-style confidence and the frames supporting each decision

Choose `source-native` when the source has a distinctive and reusable visual system. Choose `editorial-remix` when the source is recognizable but needs stronger slide hierarchy. Choose `independent` for visually weak sources such as plain talking-head recordings. In `auto`, make this decision from the evidence rather than defaulting to a generic house style.

## Paper route

Paper is optional. It is a connected design canvas used to audition art direction before the chosen system is reconstructed as editable PowerPoint objects; it is not the deck renderer or an installation requirement.

When Paper MCP is connected:

1. Read Paper's full `paper-mcp-instructions` guide before other Paper operations.
2. Call `get_basic_info`, inspect the current selection when relevant, and verify planned font families with `get_font_family_info`.
3. Before mutating the canvas, show the user Paper's concise design brief: mood candidates, chosen mood, 5–6 role-based colors, type scale, and one-sentence direction.
4. Create a dedicated Paper file or page. Build a design board followed by three 16:9 audition artboards: title, concept, and dense evidence/example.
5. Work incrementally. Keep information directly on the canvas, use source imagery as evidence, and avoid component-library styling unless it belongs to the source.
6. Capture and critique screenshots after each representative artboard for spacing, typography, contrast, alignment, fit, and repetition. Make targeted fixes.
7. Retrieve JSX and computed styles from the selected artboards. Save the useful exports and a `paper_handoff.json` mapping layout, typography, palette, and asset treatment back to the slide briefs.
8. Call `finish_working_on_nodes` when the Paper work is complete.

Paper is a design source, not the final PowerPoint renderer. Reconstruct text, shapes, charts, and simple diagrams as editable PowerPoint objects. Use Paper screenshots only for QA; never place a full-slide Paper screenshot into the delivered deck. Original video frames and explicitly generated illustrations may remain rasterized.

If `--review-design` is active, pause after the three-slide audition. Otherwise select the direction that best matches the visual DNA and remains legible as a deck.

## Native fallback

When Paper is unavailable in `auto`, create the same design brief and three-slide audition with the Presentations workflow. Preserve `visual_dna.json` and the same QA checks. Do not silently revert to a fixed dark consulting theme or a generic editorial template. Mention the native fallback in the final handoff, but do not treat the missing optional MCP as an error.

## Design QA

Reject or revise the deck when:

- three consecutive slides share substantially the same silhouette;
- decorative cards, pills, or borders outnumber content-driven surfaces;
- the deck's dominant palette or typography category conflicts with high-confidence visual DNA;
- screenshots are repeatedly boxed when full-bleed or canvas-integrated treatment is source-native;
- generated visuals look factual but lack evidence;
- the deck could plausibly fit any unrelated video with only the words swapped.
