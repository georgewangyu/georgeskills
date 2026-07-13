# Visual Coverage QA Rubric

Use these as review heuristics, not automatic style laws. Judge the rendered pixels, spoken beat, and audience task together.

## Measurements

| Check | Measure | Flag candidate | Required when |
|---|---|---|---|
| Claim-bearing visual gap | Time in a sourced or technical claim with no relevant proof or explanatory visual | More than 3 seconds in the hook or 6 seconds later without a meaningful supporting change | The narration presents a precise external fact as demonstrated but the render supplies no readable support |
| Screenshot hold | Visible time from usable first frame to usable last frame | Shorter than `max(1.5 seconds, visible words / 3 + 0.5 seconds)` or longer than 5 seconds without crop, highlight, or narration-driven reason | The key text cannot be read at normal phone playback speed |
| Repeated static asset | Reappearance of the same image or effectively identical crop | More than twice, or again within 10 seconds without a new purpose | Reuse implies the same receipt supports a materially different claim when it does not |
| Dense table or UI | Simultaneously visible rows, cells, controls, labels, and small text | More than six competing items with no zoom, crop, highlight, cursor, or callout | The narration depends on a value or rank that is unreadable or ambiguous |
| Caption collision | Caption box overlap with a face, proof text, source/date label, CTA, or platform safe zone | Any overlap that competes with the intended focal point | The collision hides or changes the meaning of required evidence |
| Evidence mismatch | Difference between narration and visible source, metric, date, entity, or claim strength | Any adjacent-but-not-equivalent evidence | The visual contradicts, materially overstates, or falsely attributes the spoken claim |
| Product-demo purity | Correct product UI/action, orientation, visible people, creator branding, baked subtitles, and playback-size readability | Unrelated creator/room footage, unclear product action, filler, or UI too small to understand | The brief requires product-only footage, or the visible material misrepresents what the product does |
| Motion boundary integrity | First, middle, final, and transition-adjacent frames | Blank, black, dim, reset, corrupt-alpha, duplicated-state, or one-frame block | Any corrupt frame interrupts or obscures required content |
| Unused prepared asset | Manifested or prepared asset absent from the rendered timeline | Report when a prepared asset covers a currently flagged beat | Never required solely because it was prepared |

For screenshot timing, count only the words the viewer must read, not every
visible word in the source. If the calculated readable hold exceeds five
seconds, prefer a tighter crop, progressive reveal, or callout sequence over a
single longer static card.

## Coverage Accounting

Use one consistent timebase and avoid double counting overlapping layers.

- `claim-bearing covered time`: duration where a factual or technical spoken beat has a relevant, readable visual treatment
- `flagged gap time`: duration of claim-bearing intervals with no relevant or readable treatment
- `intentional A-roll-only time`: delivery-led intervals where the face, emotion, or pause is the intended visual
- `visual coverage rate`: `covered / (covered + flagged gaps)` for claim-bearing intervals only

Report the numerator and denominator with the rate. Do not score the entire video by the percentage of non-A-roll frames.

## Frame Sampling

Inspect:

1. the first frame, 0.5 seconds, 1.5 seconds, and each visual change inside the hook
2. the first, middle, and final usable frame of every overlay
3. every caption-layout change and every frame where proof text approaches the caption area
4. one frame immediately before and after each proposed edit boundary
5. every frame around a suspected one-frame corruption or alpha/compositing
   defect until the clean boundary is proved

When sampling misses an animated collision or fast transition, inspect a short local sequence rather than relying on one still.

## Finding Format

Use one row per actionable interval:

| Severity | Current time | Observation | Audience cost | Exact fix | Proposed time | Asset | Confidence |
|---|---|---|---|---|---|---|---|
| high leverage | 00:12.4–00:17.8 | Full leaderboard is static; narrated rank is not marked | Viewer must search a dense table | Punch to the relevant row, add one restrained highlight, then return to A-roll | 00:12.6–00:16.2 | `04_leaderboard.png` | high |

Tie every required finding to visible evidence or a transcript/source mismatch. Label subjective recommendations as optional taste.

## Repair Priority

Order work by:

1. factual integrity and source readability
2. hook comprehension
3. caption or focal-point collisions
4. unexplained dense visuals
5. long claim-bearing gaps
6. repeated assets and optional motion polish

After a new export, rerun the affected intervals and the hook. Do not mark a metadata change as fixed until it is visible in the render.
