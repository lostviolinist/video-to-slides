# Video-to-slides eval rubric

Use this rubric after the automated eval passes. Review the normalized transcript, every window review, the evidence cards, slide briefs, selected frames, and final slide renders. Score each criterion from 0 to 4. A deck passes when every applicable criterion scores at least 3 and there are no critical factual errors.

## 1. Full transcript review and important-point extraction

- **4:** Every transcript window was reviewed. The evidence cards capture the thesis, major supporting ideas, strongest examples, material caveats, and conclusion. Repetition, sponsors, and weak tangents are excluded with sensible reasons.
- **3:** Complete review with only a minor missed point that would not change the deck's usefulness.
- **2:** Some windows were processed mechanically, or one major idea, caveat, or conclusion is missing.
- **1:** The evidence is heavily biased toward the opening or captions alone and misses substantial sections.
- **0:** Large parts of the source were not reviewed.

## 2. Slides reflect the important points

- **4:** The deck's emphasis matches the source's real emphasis. Every major point appears, minor ideas stay minor, the first content slide gives an executive summary of the complete video, and the conclusion accurately synthesizes it.
- **3:** The major points are present with small issues in ordering or emphasis.
- **2:** The deck contains mostly correct material but overweights minor points or omits one major point.
- **1:** Several important points are absent, distorted, or buried.
- **0:** The deck does not represent what the video is mainly saying.

## 3. Screenshots match the points

- **4:** Every screenshot comes from the cited moment, visibly shows the exact object, feature, demonstration, or state claimed by the slide, is sharp and readable, and is the best available frame for the point.
- **3:** Screenshots are correct and readable, with only a slightly weaker crop or frame choice.
- **2:** One or more screenshots are related but do not clearly prove or explain the point.
- **1:** Several screenshots are generic, mistimed, blurry, duplicated, or attached to the wrong point.
- **0:** Screenshots are misleading or unrelated.

If the deck legitimately uses no source screenshots, mark this criterion `N/A` rather than inventing a need for them.

## 4. Diagrams match the points

- **4:** Every diagram represents only relationships supported by the evidence, uses the correct direction and labels, and makes the point easier to understand without adding invented structure or values.
- **3:** Diagrams are correct with only small clarity or labeling issues.
- **2:** The general idea is right, but an important relationship, direction, label, or scope is ambiguous.
- **1:** Several diagrams imply unsupported relationships or use a generic process that does not match the source.
- **0:** A diagram materially changes or contradicts the source.

If no diagram is needed, mark this criterion `N/A`. Do not reward a deck for adding unnecessary diagrams.

## Eval record

For each run, save the visual review as `semantic_eval.json` in the project directory. Include:

- Source and options used.
- Skill commit and model configuration.
- Generated project directory and PPTX.
- Automated eval JSON.
- Four rubric scores with one or two sentences of evidence for each.
- Total time, model/API cost when available, and whether Paper was used.
- Any failure that should become a regression case.

A run passes only when `eval.json` reports `ok: true`, every applicable score here is at least 3, and there are no critical factual errors. Fix the deck or evidence pack and rerun both checks after any failure.
