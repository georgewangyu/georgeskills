---
name: bitter-lesson-check-ops
description: Judge whether a piece of agent scaffolding (skill, rule, prompt, steering doc, lint, harness, eval, workflow) will compound or decay as models improve, using Sutton's bitter lesson. Use when deciding what to build, keep, or delete in an agent setup, or when ranking improvements to a coding agent.
memory_tags:
  - domain:agent-systems
  - workflow:agent-scaffolding-review
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:agent-scaffolding
  - outputs:durability-verdict
  - risk:low
---

# Bitter Lesson Check

Sutton's bitter lesson (2019): general methods that scale with compute, like
search and learning, beat hand-coded human knowledge over time. For agents:
scaffolding that makes up for a weak model gets washed out by the next model.
Scaffolding that gives the model feedback, or states what you actually want,
gets more valuable as models improve.

This skill sorts each item into **durable** or **temporary** so effort goes to
the part that compounds.

## Trigger

Use when:
- the user asks "does this violate the bitter lesson" or "will this age well"
- ranking improvements to an agent, skill library, or harness
- a steering doc, rule file, or skill set keeps growing and needs pruning
- comparing someone else's agent setup with your own

Do not use when:
- the question is only about code correctness
- there is no agent or model in the loop

## Inputs

- Required: the list of items to judge (skills, rules, prompts, lints, evals, harness pieces)
- Optional: the problem each item was added to fix, how often it fires, its maintenance cost

## The test

For each item ask: **would we still need this if the model were 10x smarter?**

| Category | Typical examples | Verdict |
|---|---|---|
| Feedback signal | run the real app, traces, test harnesses, metric assertions, feature maps for navigation | Durable. A smarter model gets more out of it. |
| Search against a score | evals, judge models, hill-climbing loops | Durable. This is compute doing the work. |
| Intent and invariants | lint rules, type constraints, CI gates, import bans, architecture tests | Durable. Encodes your spec, which no model learns from general data. |
| Deterministic tooling | scripts and CLIs inside skills, codemods | Neutral to durable. Judgment on mechanical steps is waste at any size, and results stay consistent. |
| Reasoning coaching | "stop guessing", "read the code first", how-to-think checklists, long style essays | Temporary. Compensates for model weakness. |
| Implementation recipes in prose | exact command sequences the model could derive | Temporary. Delete as models catch up. |
| Team taste | "reuse the existing seam", "short docstrings" | Middle. Prefer a lint rule or examples mined from real review comments over hand-written rules. |

## Workflow

1. List every item. For each, note the failure it was added to fix.
2. Apply the 10x test and place it in a category above.
3. Mark it **durable**, **temporary**, or **middle**.
4. For temporary items: keep them small, add a review date, and note what would let you delete them (a model upgrade, a lint rule, an eval showing it no longer changes behavior).
5. For middle items: check if a hard gate (lint, type, CI) or learning from examples can replace the prose.
6. Rank improvements: durable items with high leverage first. Temporary items only when the near-term payoff is clear.

## Caveat

The bitter lesson is about research over years. Shipping work is about this
quarter. A temporary rule that saves many review rounds now is worth it. Mark
it temporary and do not build process on top of it.

## Output

A table with columns: item, category, verdict (durable / temporary / middle),
reason, and the action (invest, keep small with review date, convert to a
hard gate, or delete). End with the top three investments.
