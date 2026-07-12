#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <event-type-id> <date> <start-iso> <end-iso> <timezone>" >&2
  exit 2
}

[[ $# -eq 5 ]] || usage

event_type_id="$1"
date="$2"
start_iso="$3"
end_iso="$4"
timezone="$5"

command -v calcom >/dev/null || {
  echo "calcom CLI is required" >&2
  exit 1
}

command -v jq >/dev/null || {
  echo "jq is required" >&2
  exit 1
}

event_json="$(calcom event-types get "$event_type_id" --json)"
slot_json="$(
  calcom slots available \
    --start "$start_iso" \
    --end "$end_iso" \
    --event-type-id "$event_type_id" \
    --timezone "$timezone" \
    --json
)"

jq -n \
  --arg date "$date" \
  --arg timezone "$timezone" \
  --argjson event "$event_json" \
  --argjson slots "$slot_json" \
  '{
    event: {
      id: $event.id,
      title: $event.title,
      slug: $event.slug,
      hidden: $event.hidden,
      duration_minutes: $event.lengthInMinutes,
      schedule_id: $event.scheduleId,
      slot_interval: $event.slotInterval,
      locations: $event.locations
    },
    date: $date,
    timezone: $timezone,
    count: ($slots.data[$date] | length),
    starts: [$slots.data[$date][]?.start]
  }'
