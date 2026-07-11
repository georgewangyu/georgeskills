# Parallel Asset Lanes

Use as many independent lanes as available, but keep one owner per output file.

## Lane A — Social receipts

Objective: capture named posts, replies, profile history, and matching cross-platform posts.

Return:

- tightly cropped screenshots
- source URL and capture time
- visible metrics
- any mismatch with the script

Stop after one primary path and one fallback. Do not install a browser runtime.

## Lane B — Evidence receipts

Objective: capture official announcements, articles, benchmarks, pricing, product UI, and claims.

Prefer primary sources, then reputable reporting. A benchmark crop must preserve column names and nearby comparison rows. Never replace a blocked source with an unsourced graphic.

## Lane C — Beat map and fact check

Objective: map the script to provisional filenames while collection runs.

Return:

- beat table
- claim corrections
- live-data qualifiers
- missing visual opportunities
- first timed shot sequence

This lane should not write image files.

## Lane D — Visual opportunity scout

Objective: identify no more than three beats where custom motion, a screen recording, an official promo excerpt, or generated media would outperform a screenshot.

For each idea, return value, production path, estimated burden, provenance risk, and whether approval is required. Invoke `video-visual-assets-ops` only for selected beats.

## Lane E — QA evaluator

Objective: independently inspect the completed folder and manifest.

Check source fidelity, legibility, file signatures, filename collisions, temporal qualifiers, and whether every important spoken beat has either a visual or an intentional A-roll decision.

## Worker Contract

Every worker receives:

- one bounded objective
- exact output directory
- reserved filenames
- allowed source URLs or search lane
- a no-install/no-fabrication rule
- a short completion format: files, sources, dimensions, blockers

The parent merges results and remains responsible for final visual QA.
