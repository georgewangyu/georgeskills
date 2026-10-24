---
name: sync-workflow-ops
description: On-demand sync across every fork, vendored upstream, and private/public mirror pair you maintain. Reads one registry, reports drift and leak risks per pair, does the safe and reversible items itself, and batches every other decision into one short digest with one-word defaults. Use when the user says "run a sync workflow", "sync the forks", or "upstream sync", or when forks keep drifting because reviews produce lists instead of merges.
metadata:
  memory_tags:
    - domain:agent-systems
    - workflow:upstream-sync
    - skill_role:operator
    - repo_boundary:tools
    - inputs:fork-registry
    - outputs:sync-digest
    - risk:medium
---

# Sync Workflow Ops

## Purpose

Forks and mirrors drift for predictable reasons:

- A scheduled review gets skipped.
- A review produces a list but nothing merges.
- Forks with no shared history need hand ports.
- A private identity or private marker leaks into a public repo.

This skill handles all your pairs in one run, whenever you ask. It does the
safe work itself, and it hands you a single decision list where each item has
a default.

## Pair classes

| Class | Use when | Mechanism |
|---|---|---|
| V vendored core | Your changes fit behind extension points | Read-only `third_party/<upstream>/` via `git subtree --squash` on release tags, an overlay package, a no-edit check, and a version tied to upstream |
| M merge fork | Shared history, and you change the product | An `upstream` remote. Merge release tags only |
| P port by content | No shared history | A `reviewed_through` pin per upstream, plus a ledger of ported items |
| C canonical plus overlay | Generic content exists on both sides | The public side is canonical. The private side vendors it. Private-first work is promoted by rewriting it |
| R retire | The upstream no longer feeds a plan | Archive the remote and drop the pair |

## Inputs

- A private registry file. The format is in `references/registry-format.md`.
  Keep it outside public repos, since it names your private paths.
- Optional: release notes or advisories pages for the upstreams.

## Workflow

1. **Drift report.**
   `python3 scripts/drift_report.py --registry <registry> --fetch > /tmp/drift.md`.
   It is read only. `--fetch` updates remote-tracking refs, and partial-clones
   any upstream that is missing but has a `url`.
2. **Read, do not trust the regex.** Security hints are prompts to read the
   real commits or PRs. Also scan the whole window since `landed_through`,
   because fixes are often disclosed after they merge. Mark a feature adopt
   only if it matches a current plan.
3. **Do the safe tier without asking.** List every action:
   - advance `reviewed_through` on pairs with nothing new
   - set the push URL to `DISABLED` on any private-repo remote that points at a public clone
   - install your scrub pre-push hook in any public repo that lacks one, but
     only if the current tree already scans clean. A whole-tree hook on a tree
     with old findings blocks every push. Prefer a hook that scans only the
     added lines
   - create draft branches `sync/<id>-<date>` with a merge preview and a test run, without merging them
4. **Land only the narrow case.** A security fix or a conflict-free class V
   pull lands without asking only when all of these hold:
   - the repo is yours (personal tier)
   - it is not parked
   - its worktree is clean
   - its tests are green
   - for a public repo, the scrub and identity checks pass
5. **One digest.**

   ```text
   Done (safe): <one line>.
   Decide (reply "ok" for all defaults, or "ok except 2"):
   1. <pair>: <what is new>. Default: <land | port N | skip | resolve-theirs | defer>.
   Name-only (not covered by "ok"): retire <pair>?
   ```

   A draft that has waited 7 or more days gets its own line with a resolution
   default.
6. **Apply the answer.** Land the approved drafts and set `landed_through`.
   Advance `reviewed_through` on every reviewed pair, skips included. Commit
   the registry.
7. **Record.** Write a dated report with the drift table, the safe actions,
   the decisions and what landed.
   Regenerate the per-pair status table with `--status-md STATUS.md` (one row
   per pair: upstream, our copy, direction, pin or last sync, drift, last
   decision, next action, owner). Record decisions in the registry's
   `last_decision`, `next_action` and `owner` fields, never in the table.

## Hard rules

- Private-to-public changes are rewritten in the public tree, never
  cherry-picked. Run your marker scan on the added lines before every public
  push, and keep private provenance out of the public tree.
- Public repos use your public git identity only. The report flags any commit
  of yours that uses a forbidden identity.
- Never force-push, rewrite published history, or touch unpushed work in a
  parked repo.
- Retiring a pair, and any other destructive choice, is never covered by "ok".

## Optional reminder

A morning routine can say one line when the last sync report is more than
7 days old: "Forks: N pairs with news. Run sync workflow?" It never runs the
sync unasked.

## Files

| Path | Purpose |
|---|---|
| `scripts/drift_report.py` | Read-only drift and hygiene report (stdlib, plus PyYAML for `.yaml`) |
| `references/registry-format.md` | Registry schema and default rules |
| `tests/test_drift_report.py` | `python3 -m unittest discover -s tests` |
