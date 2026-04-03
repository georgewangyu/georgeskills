# Codex Session Bootstrap

Read in order:

1. `README.md`
2. `MEMORY_TAGS.md`
3. relevant `skills/<name>/SKILL.md`

Priority:

1. User instructions in chat
2. Skill-specific `SKILL.md`
3. Repository-level docs

## Reusability Rule

- Skills in this repo must stay reusable across users and installations.
- Do not hardcode personal handles, emails, account ids, private URLs, or user-specific defaults into `skills/`.
- Keep user-specific defaults, wrappers, credentials, and private overlays in the user's private repo instead.
- When examples are needed, use generic placeholders like `examplecreator`, `exampleuser`, or `<target>`.

## Public Publication Guard

- Treat `georgeskills` as eventually public.
- Before commit or push, staged changes must pass the repo's public-safety
  validation in `.githooks/public-safety-check.py`.
- That validation is meant to catch obvious publication mistakes in staged
  additions: local identity strings derived from git/home config, non-placeholder
  email addresses, absolute local filesystem paths, and common secret material.
- If a change intentionally needs a real identifier, stop and get explicit human
  confirmation before committing.
