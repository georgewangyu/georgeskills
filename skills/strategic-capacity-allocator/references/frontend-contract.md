# Frontend Contract

Build the frontend as a guided decision notebook around the allocator, not as a
quiz that emits a mysterious life score.

## User Flow

### 1. Frame

Collect:

- horizon and discretionary hours
- current chapter
- desired direction
- non-negotiables and fixed commitments

Show fixed commitments before asking the user to allocate discretionary time.

### 2. Lanes

Let the user create three to seven lane cards. Each card contains:

- lane name
- near-term outcome
- primary durable asset
- current allocation

Warn about overlapping lanes and ask which lane owns shared work.

### 3. Guided Interview

Ask one question at a time using `interview-guide.md`. Show:

- why the answer matters
- a recommended interpretation
- an evidence field
- `fact`, `observation`, `estimate`, or `hypothesis`

Do not show all numeric sliders first. That encourages users to reverse-engineer
the outcome they want.

### 4. Scores and Constraints

Reveal factor scores after the evidence pass. Require:

- one evidence note for a score above 70
- a low/base/high range for uncertain material factors
- a reason for floors and caps
- an explicit dependency state

### 5. Recommendation

Show:

- allocation bars and hours
- factor contribution table
- floors and caps
- primary reason each lane gained or lost capacity
- evidence-confidence badge
- model configuration

Keep the formula inspectable in a drawer or details view.

### 6. Sensitivity

Allow the user to change one assumption at a time. Highlight:

- rank changes
- allocation changes of at least 10 points
- the smallest change that flips the lead lane

Offer low, base, and high scenarios. Do not collapse them into one expected
answer.

### 7. Human Override and Review

Allow an override only with:

- revised percentage
- reason
- review date
- evidence expected before the review

At review, compare planned hours, actual hours, outcomes, and energy. Preserve
prior runs instead of overwriting them.

## Data Model

Keep these records separate:

```text
Profile
  vision, chapter, constraints, horizon, capacity

Lane
  name, outcome, asset, dependency state

Evidence
  lane, factor, text, evidence type, source/date

ScoreScenario
  lane, low/base/high factor values, confidence

AllocationRun
  immutable inputs, model version, outputs, timestamp

Override
  allocation run, changed value, reason, review date

Review
  planned hours, actual hours, outcomes, energy, new evidence
```

The CLI JSON is the calculation contract. A frontend service can serialize one
base scenario to that format, invoke the same calculation logic, and store the
immutable input and output together.

## Scaling Rules

- Version the model and weights.
- Keep user-specific weights and vision private.
- Never train defaults from one person's private answers without explicit
  consent.
- Separate recommendation generation from any calendar or task mutation.
- Require human approval before changing a schedule.
- Log why a number changed, not only that it changed.
- Use cohort defaults only as starting priors and label their source.
- Support accessibility, keyboard navigation, and plain-language factor names.

## Minimum Viable Frontend

Start with:

1. frame form
2. lane cards
3. one-question interview
4. evidence-backed scoring matrix
5. floor/cap controls
6. recommendation and sensitivity view
7. saved override and review date

Do not add social comparison, leaderboards, or a universal “best career” score.
The product is useful because it makes a person's tradeoffs explicit.
