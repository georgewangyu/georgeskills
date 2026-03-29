# Migration Queue

Candidate moves from `<private-repo>/scripts/` to modular skills in this repo.

## Journal Ops

- [x] `<private-repo>/scripts/journal/run_daily_workflow_prep.py`
- [x] `<private-repo>/scripts/journal/morning_brief.py`
- [x] `<private-repo>/scripts/journal/print_health_interview_context.py`
- [x] `<private-repo>/scripts/journal/print_email_interview_context.py`
- [x] `<private-repo>/scripts/journal/print_location_interview_context.py`
- [x] `<private-repo>/scripts/journal/visualize_daily_metrics.py`
- [x] `<private-repo>/scripts/journal/health_overnight_analysis.py`
- [x] `<private-repo>/scripts/journal/check_daily_workflow_completeness.py`
- [x] `<private-repo>/scripts/journal/visualize_sprint_metrics.py`
- [x] `<private-repo>/scripts/journal/check_automation.sh`

Status:
- Implementation moved to `georgeskills/skills/journal-ops/scripts/`
- Compatibility wrappers remain at original `<private-repo>/scripts/journal/` paths

## Memory Ops

- [x] `<private-repo>/scripts/memory/extract_daily_summary_candidates.py`
- [x] `<private-repo>/scripts/memory/validate_memory_records.py`
- [x] `<private-repo>/scripts/memory/promote_memory_candidates.py`

Status:
- Implementation moved to `georgeskills/skills/memory-ops/scripts/`
- Compatibility wrappers remain at original `<private-repo>/scripts/memory/` paths

## Health Ops

- [x] `<private-repo>/scripts/journal/import_health_auto_export_google_drive.py`
- [x] `<private-repo>/scripts/journal/import_apple_health_export_xml.py`
- [x] `<private-repo>/scripts/journal/import_health_auto_export_csv.py`
- [x] `<private-repo>/scripts/journal/import_health_shortcut_csv.py`
- [x] `<private-repo>/scripts/journal/sync_health_shortcut_metrics.py`
- [x] `<private-repo>/scripts/journal/health_auto_export_rest_receiver.py`
- [x] `<private-repo>/scripts/journal/build_health_dashboard.py`
- [x] `<private-repo>/scripts/journal/parse_hae_sleep_experimental.py`
- [x] `<private-repo>/scripts/journal/health_overnight_analysis.py` (implemented in `journal-ops` due direct module coupling with morning-context scripts)

Status:
- Health implementations moved to `georgeskills/skills/health-ops/scripts/`
- Compatibility wrappers remain at original `<private-repo>/scripts/journal/` paths

## Deep Exploration Ops

- queue and distillation helpers as they are extracted from private workflows

## Exports Ops

- [x] `<private-repo>/scripts/exports/apple-notes/export_apple_notes.py`
- [x] `<private-repo>/scripts/exports/calendar/export_calendar_google.py`
- [x] `<private-repo>/scripts/exports/cursor-chats/export_cursor_chats.py`
- [x] `<private-repo>/scripts/exports/email/export_emails_gmail_api.py`
- [x] `<private-repo>/scripts/exports/email/export_all_emails.py`
- [x] `<private-repo>/scripts/exports/email/deduplicate_emails.py`
- [x] `<private-repo>/scripts/exports/email/send_email_gmail_api.py`
- [x] `<private-repo>/scripts/exports/email/verify_gmail_scopes.py`
- [x] `<private-repo>/scripts/exports/social-media/export_x_feed_bird.py`

Status:
- Implementations moved to `georgeskills/skills/exports-ops/scripts/`
- Compatibility wrappers remain at original `<private-repo>/scripts/exports/` paths

## PDF Reconstruction Ops

- [x] `<private-repo>/scripts/pdf-reconstruction/extract_pdf_text.py`
- [x] `<private-repo>/scripts/pdf-reconstruction/extract_pdf_ocr.py`
- [x] `<private-repo>/scripts/pdf-reconstruction/extract_image_ocr.py`

Status:
- Implementations moved to `georgeskills/skills/pdf-reconstruction-ops/scripts/`
- Compatibility wrappers remain at original `<private-repo>/scripts/pdf-reconstruction/` paths

## Utility Ops

- [x] `<private-repo>/scripts/utils/convert_resume.py`
- [x] `<private-repo>/scripts/utils/extract_pdf_text.py`
- [x] `<private-repo>/scripts/utils/extract_pdf_text_applescript.sh`
- [x] `<private-repo>/scripts/utils/generate_repo_summaries.py`

Status:
- Implementations moved to `georgeskills/skills/utility-ops/scripts/`
- Compatibility wrappers remain at original `<private-repo>/scripts/utils/` paths

## Aida Ops

- [x] `<private-repo>/scripts/aida-bookkeeping-audit.mjs`

Status:
- Implementation moved to `georgeskills/skills/aida-ops/scripts/`
- Compatibility wrapper remains at original `<private-repo>/scripts/` path
