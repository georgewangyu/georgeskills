# Reel Candidate Scale

Score the positive factors first, then subtract explicit risks. Use only the
listed anchor values. Preserve every component and deduction in the candidate
register so another operator can reproduce the total.

## Positive score: 100 points

| Factor | Points | Question |
| --- | ---: | --- |
| Hook strength | 20 | Does the opening create specific, truthful curiosity in the first thought? |
| Standalone coherence | 15 | Can a new viewer follow it without the long-form chapter? |
| Payoff and utility | 15 | Does the reel deliver a useful mechanism, lesson, proof, or reframe? |
| Visual-proof potential | 15 | Is there a real screen, diagram, receipt, comparison, or meaningful animation? |
| Source delivery | 10 | Is the original performance clear, energetic, and vertically crop-friendly? |
| Novelty and specificity | 10 | Is this more distinctive than generic AI or career advice? |
| Edit feasibility | 10 | Can it become a clean short without deceptive joins or major reconstruction? |
| Strategic fit | 5 | Does it reinforce the intended topic, series, audience, or funnel? |

## Required factor anchors

Choose the highest anchor whose complete description is supported. When the
evidence falls between anchors, use the lower one.

| Factor | Allowed scores | Anchor definitions from lowest to highest |
| --- | --- | --- |
| Hook strength | `0/5/10/15/20` | no usable opening / generic topic / clear claim / specific tension / immediate truthful curiosity plus stakes |
| Standalone coherence | `0/4/8/12/15` | fragment / major missing context / understandable after added setup / clear with a light trim / fully self-contained now |
| Payoff and utility | `0/4/8/12/15` | no payoff / vague conclusion / useful observation / concrete lesson / memorable mechanism, proof, or reframe |
| Visual-proof potential | `0/4/8/12/15` | none / decorative only / useful illustration / real or strong explanatory asset / legible real proof or multi-state teaching visual |
| Source delivery | `0/3/5/8/10` | unusable / weak audio or crop / serviceable / clear and energetic / exceptional delivery with clean crop and audio |
| Novelty and specificity | `0/3/5/8/10` | generic / familiar framing / some specificity / distinctive example / ownable, concrete insight |
| Edit feasibility | `0/3/5/8/10` | deceptive or impractical / major reconstruction / several difficult joins / one clean join or minor repair / clean contiguous cut |
| Strategic fit | `0/1/3/4/5` | conflicts / weakly adjacent / relevant / strong series fit / central to the intended audience and promise |

## Risk deductions

Subtract only when the risk is present; explain every deduction.

| Risk | Deduction |
| --- | ---: |
| Material privacy or security exposure | `-10` if a synthetic recreation is required; `-20` if risky raw screens/audio need extensive redaction; `-30` if the candidate directly contains credentials, private locations, workplace/client data, or non-consenting participants |
| Unsupported factual claim or fake metric pressure | `-5` if a visible qualifier is enough; `-10` if a pickup or substantive correction is required; `-20` if the central payoff is unsupported |
| Depends heavily on missing earlier context | `-5` if one setup line repairs it; `-10` if a structural rewrite is needed; `-15` if it is not standalone without changing the claim |
| Awkward source seam, weak audio, or unusable vertical crop | `-3` for one clean repairable seam; `-6` for multiple repairs or weak source; `-10` if original-source production is currently unusable |
| Repeats a stronger candidate without a new promise | `-3` for partial overlap; `-6` when most of the lesson repeats; `-10` for a functional duplicate |
| Payoff requires a product demo or receipt that is unavailable | `-3` if proof is optional; `-6` if viewers reasonably expect proof; `-10` if the payoff depends on missing proof |

Apply each risk category at most once. Add the eight positive factors, subtract
the selected risk deductions, and clamp the final score to `0-100`:

`final = max(0, min(100, positive subtotal - total risk deductions))`

A mandatory privacy exclusion is not merely a low score: remove it from the
publishable list and record the exclusion separately.

## Ranking tie-breakers

When two candidates have the same score, prefer in order:

1. the more specific and falsifiable promise;
2. the cleaner raw-source remap;
3. the stronger on-camera delivery;
4. the more legible real proof asset;
5. the candidate that adds topic diversity to the batch.

Do not rank by transcript position or existing animation polish alone.

## Source mapping statuses

Report each stage separately; never call a flattened source master `raw`.

| Stage | Status | Required evidence |
| --- | --- | --- |
| Finished timeline → source master | `verified` | segment ids or edit graph plus checked words/picture at both boundaries |
| Finished timeline → source master | `partial` | only part of the range or one boundary is proved |
| Finished timeline → source master | `unavailable` | no deterministic segment/path mapping exists |
| Source master → original camera | `verified` | matched source file and in/out, waveform correlation, and visual/lip-sync confirmation |
| Source master → original camera | `pending` | originals exist but the candidate-specific match is not complete |
| Source master → original camera | `unavailable` | no usable original picture can be located |
| Source master → original audio | `verified` | matched audio file and in/out plus waveform and lip-sync confirmation |
| Source master → original audio | `pending` | isolated audio exists but sync is not proved |
| Source master → original audio | `not-applicable` | no separate original audio was recorded and this absence is documented |
| Source master → original audio | `unavailable` | expected original audio cannot be located or matched |

Production requires `verified` original camera and either `verified` or
`not-applicable` original audio. Anything else is held unless the user
explicitly authorizes a `finished-master exception`; record the reason and the
quality/crop limits in the approval gate.
