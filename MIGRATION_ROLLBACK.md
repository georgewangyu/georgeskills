# Migration Rollback Guide

This migration is intentionally rollback-safe.

## Safety Mechanisms

- Original command paths in `<private-repo>/scripts/...` are preserved as wrappers.
- Wrappers delegate to `georgeskills` implementations by default.
- Wrappers include local `_legacy` fallbacks in `<private-repo>` if `georgeskills`
  is unavailable.

## Runtime Rollback (No File Moves)

If `georgeskills` is unavailable, wrappers automatically run local fallback
scripts under:

- `<private-repo>/scripts/journal/_legacy/`
- `<private-repo>/scripts/journal/_legacy_health/`
- `<private-repo>/scripts/memory/_legacy/`
- `<private-repo>/scripts/exports/_legacy/`
- `<private-repo>/scripts/pdf-reconstruction/_legacy/`
- `<private-repo>/scripts/utils/_legacy/`
- `<private-repo>/scripts/_legacy/`

No manual action is required for this fallback.

## Hard Rollback (Restore Pre-Migration Layout)

To fully restore in-repo implementations:

1. Copy scripts from `<private-repo>/scripts/*/_legacy*` back into their parent
   directories.
2. Replace wrappers with those copied implementations.
3. Optionally remove delegated implementations from `georgeskills`.

Because wrappers preserve stable entrypoints, hard rollback is optional and
primarily for repository-layout preferences.
