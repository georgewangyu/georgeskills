---
name: agent-eval-harness-ops
description: Design lightweight eval harnesses for coding or workflow agents, especially when testing whether agents follow steering docs, use tools correctly, preserve user edits, recover from failures, and produce the intended artifact.
memory_tags:
  - domain:agent-systems
  - workflow:agent-evaluation
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:agent-instructions
  - outputs:evaluation-rubric
  - risk:medium
---

# Agent Eval Harness Ops

## Trigger

Use when:
- the user wants to test whether an agent follows instructions or steering docs
- the user asks for evals, rubrics, failure categories, or test cases for an agent workflow
- the task involves coding agents, tool-use agents, workflow agents, or skill/AGENTS.md behavior
- an agent run failed and the user wants a reproducible eval instead of a one-off postmortem

Do not use when:
- the user only wants a normal code review or prompt rewrite
- the target behavior is too vague to evaluate
- the task requires live benchmark infrastructure before a lightweight rubric is useful

## Inputs

- Required: agent instructions or steering docs, target task, expected behavior
- Optional: prior agent transcript, repo/tool constraints, known failure examples, scoring scale, desired output artifact

## Workflow

1. Define the evaluation boundary:
   - agent role and allowed tools
   - task type
   - expected final artifact
   - behaviors that must never happen
2. Convert requirements into behavior categories:
   - instruction adherence
   - tool choice and sequencing
   - preservation of user edits
   - verification and test running
   - recovery from failed commands or missing context
   - output quality and handoff clarity
3. Build 3-7 focused eval cases:
   - one happy path
   - one ambiguous instruction case
   - one dirty-worktree or preexisting-change case
   - one tool failure or missing-data case
   - one final-report accuracy case
4. For each case, define:
   - setup/context
   - task prompt
   - expected behaviors
   - unacceptable behaviors
   - pass/fail or 1-5 scoring rubric
5. If a prior run exists, classify failures against the rubric.
6. Recommend fixes:
   - steering-doc edits
   - prompt changes
   - tool workflow changes
   - deterministic checks or scripts worth adding
7. Optionally record an execution receipt when runs need to be compared or
   audited:
   - Use any installed provider-neutral receipt runner; AI Task Receipt is one
     example, not a required dependency.
   - Prefer a machine-readable JSON receipt plus a concise human-readable view.
   - Capture task/case id, runner and provider/model when known, permissions,
     start/end or duration, exit status, bounded/redacted output, verifier
     result, and residual risk.
   - A receipt records what ran; it does not turn one run into a statistically
     meaningful benchmark.
   - Do not require paid multi-model runs. Use the smallest run set that can
     answer the evaluation question, including a single local or existing
     provider when appropriate.

## Output Contract

Return:
- eval objective
- behavior categories
- eval cases
- scoring rubric
- observed or hypothetical failure taxonomy
- recommended fixes ranked by leverage
- next action: run manually, automate, or defer
- optional receipt path/id and verifier result when a receipt was requested

## Boundaries

- Keep evals small enough to run in real work.
- Separate model capability failures from instruction/design failures.
- Do not claim statistical benchmark certainty from a tiny harness.
- Keep receipt tooling optional and provider-neutral; do not make a paid model
  or a specific runner a prerequisite for lightweight evaluation.
- Keep examples public-safe: no private paths, credentials, account IDs, or real personal identifiers.
