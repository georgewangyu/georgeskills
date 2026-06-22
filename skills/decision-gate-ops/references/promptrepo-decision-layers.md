# PromptRepo Decision Layers

Use this reference when `promptrepo/` is available and the decision needs a
principles-backed read rather than a simple tradeoff table.

## Ray Dalio Principles Layer

Preferred local files:

- `promptrepo/decision-making/ray-dalio-principles/SKILL.md`
- `promptrepo/decision-making/ray-dalio-principles/prompts.md`

Useful lines to preserve as decision language:

- Tell the user what is really true, not only what is comforting.
- Weight advice by actual track record in the relevant domain.
- Show second- and third-order consequences.
- Identify the underlying machine or recurring pattern.
- End with the principle that should govern the decision.

Use this layer when:

- the user is avoiding an uncomfortable constraint
- a short-term win may create a worse second-order effect
- the decision should produce a durable operating rule
- the same problem keeps reappearing under different names

## Copy-Paste Prompt Seed

```text
I need help making a decision about [decision].

Apply a principles lens:
1. What is actually true here that I may be avoiding?
2. Whose evidence deserves the most weight in this domain?
3. What are the likely second- and third-order consequences?
4. What recurring pattern or system is producing this decision?
5. What principle should govern this decision next time?

Return a concrete recommendation, the strongest reason against it, the proof
threshold, and the future rule.
```

## Automation-Specific Prompt Seed

```text
I am deciding how much of [workflow] to automate.

Classify each step as:
- boring and reversible
- taste-sensitive
- public/reputation-sensitive
- platform-fragile
- blocked by missing proof

Recommend what to automate now, what should stay human-approved, what live proof
would change the boundary, and the principle I should reuse next time.
```
