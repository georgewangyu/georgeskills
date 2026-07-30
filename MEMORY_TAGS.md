# Memory Tags

`metadata.memory_tags` in skill headers are lightweight metadata for retrieval
and routing. They are not secrets and should be public-safe.

## Format

Use YAML list format beneath the schema-compatible top-level `metadata` key:

```yaml
metadata:
  memory_tags:
    - domain:journal
    - workflow:daily-summary
    - data_class:private-derived
    - repo_boundary:tools
```

Some older skills still use a top-level `memory_tags` key. Preserve that
legacy shape until the skill is otherwise touched, but use
`metadata.memory_tags` for new or updated skills so the official skill
validator accepts the header.

## Required Tags

- `domain:<name>` (journal, memory, health, deep-exploration, etc.)
- `repo_boundary:tools`

## Recommended Tags

- `workflow:<name>`
- `skill_role:<generator|evaluator|operator|researcher|orchestrator>`
- `risk:<low|medium|high>`
- `inputs:<type>`
- `outputs:<type>`

## Skill Role Tags

- `skill_role:generator` creates candidate artifacts: drafts, plans,
  messages, scripts, names, or designs.
- `skill_role:evaluator` judges an existing artifact against a rubric and
  returns scores, risks, required fixes, or a pass/fail decision.
- `skill_role:operator` runs a concrete workflow against files, APIs, local
  tools, or external state.
- `skill_role:researcher` gathers and synthesizes evidence before a decision.
- `skill_role:orchestrator` routes, sequences, or coordinates other skills and
  workflow state.

## Rule

If a skill requires private data to run, tag it clearly (for example
`data_class:private-derived`) and keep private files in the configured private
repo.
