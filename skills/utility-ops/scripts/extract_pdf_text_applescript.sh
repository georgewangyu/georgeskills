#!/bin/bash
# Extract text from PDF using macOS Preview via AppleScript
# Usage: ./extract_pdf_text_applescript.sh <pdf_file>

PDF_FILE="$1"

if [ -z "$PDF_FILE" ]; then
    echo "Usage: $0 <pdf_file>"
    exit 1
fi

osascript <<EOF
tell application "Preview"
    open POSIX file "$(pwd)/$PDF_FILE"
    delay 1
    tell application "System Events"
        keystroke "a" using command down
        delay 0.5
        keystroke "c" using command down
        delay 0.5
    end tell
    quit
end tell
EOF

# The text is now in clipboard - we can't easily get it from shell
# But this shows the approach - user can paste after running

echo "Text extracted to clipboard. You can paste it now."




