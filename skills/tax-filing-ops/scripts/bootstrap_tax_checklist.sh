#!/usr/bin/env bash
set -euo pipefail

YEAR="${1:-}"
DEST_DIR="${2:-plans}"

if [[ -z "$YEAR" ]]; then
  echo "Usage: $0 <tax-year> [dest-dir]" >&2
  exit 1
fi

mkdir -p "${DEST_DIR}/${YEAR}"
cat > "${DEST_DIR}/${YEAR}/checklist.md" <<'EOT'
# Tax Checklist {{YEAR}}

## Setup
- [ ] Confirm jurisdiction
- [ ] Confirm filing product
- [ ] Confirm planning vs filing session

## Documents
- [ ] Employment income forms
- [ ] Investment income forms
- [ ] Self-employment income and expense records
- [ ] Donation and credit receipts
- [ ] Other region-specific forms

## Status Gates
- [ ] All required docs marked received
- [ ] All values entered into filing software
- [ ] Validation warnings resolved
- [ ] Final human review completed
- [ ] Return filed
EOT

sed -i.bak "s/{{YEAR}}/${YEAR}/g" "${DEST_DIR}/${YEAR}/checklist.md"
rm -f "${DEST_DIR}/${YEAR}/checklist.md.bak"

echo "Created ${DEST_DIR}/${YEAR}/checklist.md"
