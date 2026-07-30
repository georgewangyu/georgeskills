# Scoring Model

The model ranks the next marginal block of capacity in each lane. All factors
use a 0–100 scale.

## Factors

| Key | Factor | Question | Anchors |
|---|---|---|---|
| `pnr` | Probability-adjusted near-term revenue | How much credible cash or economic value can the next block generate within 90 days? | 0 none; 50 plausible but uncommitted; 100 contracted, realized, or extremely likely and material |
| `bp` | Base protection | How strongly does the next block protect runway, employability, credentials, or essential stability? | 0 no protection; 50 meaningful option protection; 100 prevents a serious near-term downside |
| `ca` | Ten-year compounding assets | What reusable skill, proof, product, audience, relationship, data, or insight remains? | 0 disposable; 50 reusable in adjacent work; 100 likely to compound across many future paths |
| `fit` | Personal fit and energy | Does the work texture fit demonstrated strengths, motivation, and sustainable energy? | 0 repeatedly harmful; 50 tolerable; 100 unusually energizing and sustainable |
| `align` | Strategic alignment | Does success move the person toward the desired life and contribution rather than a nearby proxy? | 0 conflicts; 50 useful bridge; 100 direct expression |
| `ec` | Evidence confidence | How trustworthy are the preceding estimates? | 0 speculation; 50 indirect or small-sample evidence; 100 repeated direct evidence |
| `oc` | Opportunity cost | How much unusually valuable, time-sensitive, or exclusive alternative is displaced? | 0 little displaced; 50 meaningful alternative; 100 a clearly superior or expiring option is crowded out |
| `sat` | Saturation | How far has current effort already reduced the value of the next block? | 0 returns still strong; 50 visibly flattening; 100 the next block adds almost nothing |

## Default Formula

```text
core =
  0.22 × pnr +
  0.16 × bp +
  0.26 × ca +
  0.16 × fit +
  0.20 × align

confidence multiplier = 0.60 + 0.40 × (ec / 100)

adjusted score =
  core × confidence multiplier
  − 0.12 × oc
  − 0.12 × sat
```

Clamp the adjusted score to 0–100.

The weights are normative defaults, not population estimates. They express a
balanced preference for compounding and alignment while retaining near-term
revenue and downside protection. Change them only when the person can state the
tradeoff being changed. Core weights must sum to 1.

The 0.60 confidence floor prevents uncertain experiments from being erased
before they can generate evidence. Confidence can only shrink a claim; it
never adds points.

## Avoid Double-Counting

- `pnr` measures near-term economic effect; `bp` measures protection from a
  downside. One salary can support both only if the notes distinguish cash
  earned from risk avoided.
- Give a durable asset one primary home in `ca`. Do not also award the same
  credential as alignment unless it directly advances the stated direction.
- `fit` describes sustainable work texture, not whether the lane is important.
- `align` describes destination or bridge fit, not enjoyment.
- `oc` describes the displaced alternative or expiring window. It is not the
  inverse of the lane's core quality.
- `sat` describes the next block after the current allocation. A hard practical
  ceiling belongs in `max_pct`, not in a second saturation penalty.

## Allocation Algorithm

1. Calculate each lane's adjusted score.
2. Reserve every `min_pct`.
3. Distribute remaining capacity in proportion to positive adjusted scores.
4. When a lane reaches `max_pct`, hold it there and redistribute the remainder
   among uncapped lanes.
5. Convert percentages to hours when `capacity_hours` is present.

This is constrained proportional allocation, not proof of a global optimum.
Floors and caps encode the parts of the decision that arithmetic should not
silently override.

## JSON Input

```json
{
  "profile": {
    "name": "Example Person",
    "horizon": "two-week sprint",
    "capacity_hours": 40
  },
  "model": {
    "core_weights": {
      "pnr": 0.22,
      "bp": 0.16,
      "ca": 0.26,
      "fit": 0.16,
      "align": 0.20
    },
    "confidence_floor": 0.60,
    "penalties": {
      "oc": 0.12,
      "sat": 0.12
    }
  },
  "lanes": [
    {
      "name": "Salaried career",
      "scores": {
        "pnr": 80,
        "bp": 90,
        "ca": 70,
        "fit": 65,
        "align": 70,
        "ec": 85,
        "oc": 20,
        "sat": 30
      },
      "min_pct": 25,
      "max_pct": 55,
      "evidence": [
        "The current role supplies most household income."
      ],
      "notes": "Protect the base without allowing it to consume the sprint."
    }
  ]
}
```

`model` is optional. Omit it to use the defaults. Every score must be between 0
and 100. Floors and caps must be between 0 and 100, each floor must not exceed
its cap, and total floors must not exceed 100.

## Sensitivity and Review

Run separate low, base, and high scenarios when uncertain inputs could move by
more than 15 points. Do not average scenarios. Report:

- whether the ranking changes
- whether an allocation changes by at least 10 percentage points
- the assumption responsible

Recalculate at the next sprint only after adding actual evidence: hours spent,
cash or interviews generated, artifacts shipped, energy observations,
dependencies cleared, or options created. Changing numbers without new
evidence is model churn.
