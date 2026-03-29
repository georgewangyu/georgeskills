# Health Ops Scripts

Modular health-processing implementations used by private workflows.

## Boundary

- Public workflow/spec docs live in `liferepo/health/`.
- Private health state lives in `<private-repo>`.
- Stable entrypoints remain in `<private-repo>/scripts/journal/` as wrappers.

New-user onboarding for Apple Health setup lives in:
- `liferepo/health/APPLE_HEALTH_ONBOARDING.md`

## Scripts

Implementation scripts are under:
- `scripts/`

Key paths:
- JSON importer: `scripts/import_health_auto_export_google_drive.py`
- XML importer: `scripts/import_apple_health_export_xml.py`
- Shortcut CSV importer: `scripts/import_health_shortcut_csv.py`
- Dashboard builder: `scripts/build_health_dashboard.py`
