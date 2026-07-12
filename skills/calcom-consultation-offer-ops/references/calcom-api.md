# Cal.com API Notes

Use the CLI for ordinary reads and the v2 API when the CLI does not expose
availability arrays, overrides, booking fields, locations, or schedule
attachment.

## Headers

Schedules:

```text
cal-api-version: 2024-06-11
Authorization: Bearer <api-key>
Content-Type: application/json
```

Event types:

```text
cal-api-version: 2024-06-14
Authorization: Bearer <api-key>
Content-Type: application/json
```

Never print the authorization header.

## Recurring schedule

Create with `POST /v2/schedules` or update with
`PATCH /v2/schedules/<schedule-id>`:

```json
{
  "name": "Saturday consultations",
  "timeZone": "America/Los_Angeles",
  "isDefault": false,
  "availability": [
    {
      "days": ["Saturday"],
      "startTime": "14:00",
      "endTime": "18:00"
    },
    {
      "days": ["Saturday"],
      "startTime": "19:00",
      "endTime": "21:00"
    }
  ],
  "overrides": []
}
```

For a one-time window, use an empty weekly `availability` array and a dated
override:

```json
{
  "availability": [],
  "overrides": [
    {
      "date": "2030-01-05",
      "startTime": "14:00",
      "endTime": "19:00"
    }
  ]
}
```

## Event type

Create with `POST /v2/event-types` or update with
`PATCH /v2/event-types/<event-type-id>`:

```json
{
  "title": "1:1 Consultation",
  "slug": "consultation",
  "lengthInMinutes": 30,
  "description": "<customer-facing offer contract>",
  "hidden": true,
  "scheduleId": 123,
  "slotInterval": 30,
  "minimumBookingNotice": 60,
  "beforeEventBuffer": 0,
  "afterEventBuffer": 0,
  "locations": [
    {
      "type": "integration",
      "integration": "google-meet"
    }
  ],
  "bookingFields": [
    {
      "type": "textarea",
      "slug": "session_focus",
      "label": "What should we focus on?",
      "placeholder": "Describe the concrete artifact, workflow, or decision.",
      "required": true
    }
  ]
}
```

Every custom booking field other than name, split name, or email needs a stable
`slug`. Updating `bookingFields` replaces the custom-field set, so include every
custom field that should remain.

When Google Meet is already installed, use:

```json
{"type":"integration","integration":"google-meet"}
```

## Hidden semantics

`hidden: true` removes the event from the public profile but does not prevent a
person with the direct URL from booking. Keep an unfinished event hidden and do
not share its URL. Use private links when access itself must be limited.

## Verification reads

- `GET /v2/schedules/<schedule-id>` with schedule headers
- `GET /v2/event-types/<event-type-id>` with event headers
- `calcom slots available` for visitor slot inventory

Use ISO timestamps with the correct offset for each verification date. A
timezone-aware recurring schedule should retain the same local hours across
daylight-saving changes.
