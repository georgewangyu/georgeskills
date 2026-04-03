#!/bin/bash
# Helper script to check private-repo automation jobs.
# Backward-compatible with older launchd labels and log names.

JOB_PREFIX="${PRIVATE_REPO_JOB_PREFIX:-com.private-repo}"
LEGACY_JOB_PREFIX="${LEGACY_JOB_PREFIX:-com.liferepo}"
LOG_PREFIX="${PRIVATE_REPO_LOG_PREFIX:-private-repo}"
LEGACY_LOG_PREFIX="${LEGACY_LOG_PREFIX:-liferepo}"

echo "=== Private Repo Automation Jobs ==="
echo ""

resolve_job_label() {
  local preferred="$1"
  local legacy="$2"
  if launchctl list "$preferred" &>/dev/null; then
    echo "$preferred"
    return
  fi
  if launchctl list "$legacy" &>/dev/null; then
    echo "$legacy"
    return
  fi
  echo ""
}

print_job_status() {
  local title="$1"
  local preferred="$2"
  local legacy="$3"
  local label
  label="$(resolve_job_label "$preferred" "$legacy")"
  echo "$title:"
  if [ -n "$label" ]; then
    echo "  ✅ Loaded and active ($label)"
    launchctl list "$label" | grep -E "(LastExitStatus|Program)" | sed 's/^/    /'
  else
    echo "  ❌ Not loaded"
  fi
  echo ""
}

print_log_tail() {
  local title="$1"
  local preferred_log="$2"
  local legacy_log="$3"
  echo "$title:"
  if [ -f "$preferred_log" ]; then
    echo "  Last 3 lines:"
    tail -3 "$preferred_log" 2>/dev/null | sed 's/^/    /' || echo "    (empty)"
  elif [ -f "$legacy_log" ]; then
    echo "  Last 3 lines (legacy path):"
    tail -3 "$legacy_log" 2>/dev/null | sed 's/^/    /' || echo "    (empty)"
  else
    echo "  No log file yet (job hasn't run or no output)"
  fi
  echo ""
}

print_job_status "📊 Metrics Visualization" "${JOB_PREFIX}.visualize-metrics" "${LEGACY_JOB_PREFIX}.visualize-metrics"
print_job_status "📝 Apple Notes Export" "${JOB_PREFIX}.export-apple-notes" "${LEGACY_JOB_PREFIX}.export-apple-notes"
print_job_status "📬 Email Export" "${JOB_PREFIX}.export-emails" "${LEGACY_JOB_PREFIX}.export-emails"
print_job_status "📅 Calendar Export" "${JOB_PREFIX}.export-calendar" "${LEGACY_JOB_PREFIX}.export-calendar"
print_job_status "🧠 Memory Dream" "${JOB_PREFIX}.memory-dream" "${LEGACY_JOB_PREFIX}.memory-dream"
print_job_status "📚 Agent-Managed Refresh" "${JOB_PREFIX}.agent-managed-refresh" "${LEGACY_JOB_PREFIX}.agent-managed-refresh"

echo "📋 Recent Log Activity:"
echo ""
print_log_tail "Metrics Visualization" "/tmp/${LOG_PREFIX}-metrics-visualization.log" "/tmp/${LEGACY_LOG_PREFIX}-metrics-visualization.log"
print_log_tail "Apple Notes Export" "/tmp/${LOG_PREFIX}-apple-notes-export.log" "/tmp/${LEGACY_LOG_PREFIX}-apple-notes-export.log"
print_log_tail "Email Export" "/tmp/${LOG_PREFIX}-email-export.log" "/tmp/${LEGACY_LOG_PREFIX}-email-export.log"
print_log_tail "Calendar Export" "/tmp/${LOG_PREFIX}-calendar-export.log" "/tmp/${LEGACY_LOG_PREFIX}-calendar-export.log"
print_log_tail "Memory Dream" "/tmp/${LOG_PREFIX}-memory-dream.log" "/tmp/${LEGACY_LOG_PREFIX}-memory-dream.log"
print_log_tail "Agent-Managed Refresh" "/tmp/${LOG_PREFIX}-agent-managed-refresh.log" "/tmp/${LEGACY_LOG_PREFIX}-agent-managed-refresh.log"

echo "=== Quick Commands ==="
echo "  Start metrics:    launchctl start ${JOB_PREFIX}.visualize-metrics"
echo "  Start notes:      launchctl start ${JOB_PREFIX}.export-apple-notes"
echo "  Start email:      launchctl start ${JOB_PREFIX}.export-emails"
echo "  Start calendar:   launchctl start ${JOB_PREFIX}.export-calendar"
echo "  Start memory:     launchctl start ${JOB_PREFIX}.memory-dream"
echo "  Start knowledge:  launchctl start ${JOB_PREFIX}.agent-managed-refresh"
echo "  View metrics log: tail -f /tmp/${LOG_PREFIX}-metrics-visualization.log"
echo "  View notes log:   tail -f /tmp/${LOG_PREFIX}-apple-notes-export.log"
echo "  View email log:   tail -f /tmp/${LOG_PREFIX}-email-export.log"
echo "  View calendar log: tail -f /tmp/${LOG_PREFIX}-calendar-export.log"
echo "  View memory log:  tail -f /tmp/${LOG_PREFIX}-memory-dream.log"
echo "  View knowledge log: tail -f /tmp/${LOG_PREFIX}-agent-managed-refresh.log"
