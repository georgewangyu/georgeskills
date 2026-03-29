# Memory Tags

`memory_tags` in skill headers are lightweight metadata for retrieval and
routing. They are not secrets and should be public-safe.

## Format

Use YAML list format in frontmatter:

```yaml
memory_tags:
  - domain:journal
  - workflow:daily-summary
  - data_class:private-derived
  - repo_boundary:tools
```

## Required Tags

- `domain:<name>` (journal, memory, health, deep-exploration, etc.)
- `repo_boundary:tools`

## Recommended Tags

- `workflow:<name>`
- `risk:<low|medium|high>`
- `inputs:<type>`
- `outputs:<type>`

## Rule

If a skill requires private data to run, tag it clearly (for example
`data_class:private-derived`) and keep private files in the configured private
repo.
