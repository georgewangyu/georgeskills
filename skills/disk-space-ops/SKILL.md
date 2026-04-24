---
name: disk-space-ops
description: Check disk usage on a Mac or Linux machine, surface the largest folders and files, and produce conservative cleanup suggestions with risk framing.
memory_tags:
  - domain:storage
  - workflow:disk-audit
  - repo_boundary:tools
  - inputs:filesystem
  - outputs:cleanup-report
  - risk:medium
---

# Disk Space Ops

## Trigger

Use this skill when the user wants to:
- check disk space or see what is using storage
- find large folders, caches, downloads, backups, or build artifacts
- get practical suggestions for what can be deleted safely versus what needs review first

Do not use this skill for:
- automatic destructive cleanup without explicit user approval
- forensic recovery of deleted files
- low-level partitioning, APFS repair, or disk-health diagnosis

## Inputs

- Required: target machine or filesystem context
- Optional: specific path to inspect, workspace/repo path, minimum file size threshold, whether to scan for large files

## Workflow

1. Start with a non-destructive audit.
   Run:
   - `python3 georgeskills/skills/disk-space-ops/scripts/analyze_disk_usage.py`
   - add `--workspace <path>` when the user likely has large local dev artifacts in a repo tree
   - add `--find-large-files` when a file-level scan is worth the extra runtime
2. Read the report in this order:
   - overall free/used space on the target volume
   - largest immediate children of the home directory or target path
   - common cleanup hotspots and their current sizes
   - large files worth manual review
3. Separate recommendations by risk:
   - safe-ish now: caches, trash, transient build outputs, Xcode derived data
   - review first: downloads, local backups, archives, old installers, VM images
   - avoid suggesting: system folders, app support data unless the user understands the consequence
4. Give the user concrete next actions.
   Prefer a short ranked list of the biggest wins, with path, approximate size, why it is large, and whether the deletion is reversible or disruptive.
5. Only delete after explicit confirmation.
   This skill is for diagnosis and guidance first, not silent cleanup.

## Script Surface

Primary entrypoint:
- `skills/disk-space-ops/scripts/analyze_disk_usage.py`

Useful flags:
- `--target <path>`: inspect a different root instead of the current home directory
- `--workspace <path>`: scan a repo or workspace for large dev artifacts
- `--top <n>`: number of largest entries to print per section
- `--min-file-size-gb <n>`: threshold for large-file reporting
- `--find-large-files`: include a recursive large-file pass

## Outputs

- current free/used disk summary for the target volume
- ranked top folders under the main target path
- a hotspot table of likely cleanup candidates with risk labels
- optional large-file review list
- a short cleanup recommendation set grounded in actual size, not generic advice

## Boundaries

- Default to read-only inspection.
- Do not recommend deleting random items under `/System`, `/private`, `/usr`, or opaque application data without explaining the risk.
- Treat caches and build artifacts as suggestions, not commands, unless the user explicitly asks for deletion.
- Keep the skill reusable: no hardcoded personal paths, repo names, account ids, or machine-specific assumptions.
