# georgeskills

Repository-managed source of truth for modular Codex skills and reusable
execution tooling.

## Model

- `liferepo` owns public specs (agents/workflows/templates).
- `georgeskills` owns modular execution logic (skills + scripts).
- `<private-repo>` owns private state and data.

This repo stores skill source under `skills/`.
Codex loads installed skills from `~/.codex/skills`.
The install step is handled by `scripts/sync-to-codex.sh`, which symlinks repo
skills into `~/.codex/skills`.

## Structure

```text
georgeskills/
├── AGENTS.md
├── README.md
├── MEMORY_TAGS.md
├── MIGRATION_QUEUE.md
├── MIGRATION_ROLLBACK.md
├── skills/
│   ├── journal-ops/
│   │   └── SKILL.md
│   ├── memory-ops/
│   │   └── SKILL.md
│   ├── health-ops/
│   │   └── SKILL.md
│   ├── exports-ops/
│   │   └── SKILL.md
│   ├── pdf-reconstruction-ops/
│   │   └── SKILL.md
│   ├── utility-ops/
│   │   └── SKILL.md
│   ├── aida-ops/
│   │   └── SKILL.md
│   └── deep-exploration-ops/
│       └── SKILL.md
├── templates/
│   └── SKILL_TEMPLATE.md
└── scripts/
    ├── bootstrap_private_repo.py
    └── sync-to-codex.sh
```

## Skill Header Convention

Each `SKILL.md` should include YAML frontmatter with `memory_tags`.

See:
- `templates/SKILL_TEMPLATE.md`
- `MEMORY_TAGS.md`

## Install / Sync

Run:

```bash
./scripts/sync-to-codex.sh
```

This will symlink each repo-managed skill into `~/.codex/skills/<skill-name>`.

## Private Repo Bootstrap

To initialize a user-named private data repo for `liferepo`:

```bash
python3 scripts/bootstrap_private_repo.py --name my-private-repo --create
```

## Notes

- `~/.codex` is machine-level, not workspace-local.
- This repo is the editable source of truth.
- Restart Codex after adding a brand-new skill so the skill list refreshes.
- The private repo keeps stable wrapper entrypoints while implementations migrate.
