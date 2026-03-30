---
name: <skill-name>
description: <What this skill does and when to trigger it>
memory_tags:
  - domain:<domain>
  - workflow:<workflow>
  - repo_boundary:tools
  - risk:<low|medium|high>
---

# <Skill Title>

## Trigger

Use when:
- <condition 1>
- <condition 2>

Do not use when:
- <boundary condition>

## Inputs

- Required: <inputs>
- Optional: <inputs>

## Workflow

1. <step>
2. <step>
3. <step>

## Outputs

- <artifact/path/result>

## Boundaries

- Public specs live in `liferepo`.
- Private state lives in `<private-repo>`.
- This skill only owns modular tooling behavior.
- Keep the skill reusable: no hardcoded personal handles, emails, account ids, credentials, or user-specific defaults.
