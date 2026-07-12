---
name: calcom-consultation-offer-ops
description: Create, update, publish, and verify Cal.com consultation offers, including recurring or one-time schedules, shared availability across multiple event types, positioning copy, intake fields, conferencing, manual or integrated payment wording, and live slot checks. Use when setting up a new consultation product, changing its hours or audience, cloning an existing offer, troubleshooting missing Cal.com availability, or confirming that a public booking page works end to end.
memory_tags:
  - domain:workflow
  - workflow:consultation-offer
  - skill_role:operator
  - integration:calcom
  - outputs:booking-offer
  - risk:high
---

# Cal.com Consultation Offer Ops

Create a consultation offer as an explicit customer contract, map it to the
correct Cal.com schedule, and prove the public booking flow works without
submitting a test booking.

## Inputs

Resolve these fields before making the offer public:

- customer and problem
- title and URL slug
- credibility statement supported by the offer owner
- session outcome and exclusions
- duration and slot interval
- price and collection method
- timezone and availability windows
- one-time, recurring, or bounded booking horizon
- conferencing location
- required intake questions
- public, hidden, or private-link distribution

Ask only when an unresolved choice materially changes price, recurrence,
financial collection, or who may book. Otherwise make a reversible assumption,
state it, and keep the event hidden until verification is complete.

## Workflow

### 1. Inspect before mutating

Use the Cal.com CLI or API to inspect:

- authenticated user and timezone
- schedules and overrides
- existing event types and slugs
- installed conferencing apps
- selected and destination calendars
- payment integration status when payment is requested

Do not repurpose a generic event type when a distinct offer is intended. Do not
modify the default working-hours schedule for a product-specific offer.

### 2. Write the offer contract

Use this description sequence:

1. price, duration, and payment timing
2. concise, truthful credibility
3. two or fewer named customer situations
4. the concrete artifact, decision, or result produced in the session
5. what the customer should bring
6. exclusions and no-guarantee boundary

Prefer one problem category per event type. Do not combine business consulting,
career coaching, résumé review, and generic advice in one public offer.

### 3. Model availability correctly

- Treat the schedule end time as exclusive. A 30-minute event available from
  14:00 to 19:00 has starts from 14:00 through 18:30.
- Use a weekly availability rule for “every Saturday until changed.”
- Use a date override only for a one-time or exceptional date.
- Use multiple availability entries for split windows such as 14:00-18:00 and
  19:00-21:00.
- Attach multiple event types to the same non-default schedule when they should
  expose identical hours. The connected calendar should remove a time from the
  other event after either offer is booked.
- Preserve the account timezone so daylight-saving changes are handled by the
  schedule rather than hardcoded UTC offsets.

Read [references/calcom-api.md](references/calcom-api.md) before raw API writes.

### 4. Configure the event

Set and verify:

- duration and slot interval
- dedicated `scheduleId`
- minimum booking notice and buffers
- conferencing integration
- public or hidden status
- required custom intake fields
- guest behavior when relevant

Intake questions should reveal the exact artifact or workflow to review. Do not
request passwords, credentials, private keys, production access, regulated
records, or confidential data dumps. Invite public or redacted links only.

### 5. Handle payment honestly

If an integrated payment provider is connected, verify the price and currency
on the visitor-facing page before publishing.

If payment is manual:

- leave Cal.com's internal price at zero
- state the real fee and collection timing at the top of the description
- say explicitly that no payment is collected while booking
- remind the operator that Cal.com will not guarantee or automate collection

Never describe a manual-payment reservation as prepaid.

### 6. Protect credentials

- Never print API keys, OAuth states, authorization headers, or unsanitized
  payment-connection URLs.
- Prefer an existing protected CLI configuration or environment variable.
- If a key is exposed, rotate it, store the replacement without echoing it, and
  revoke superseded keys.
- Do not run a command that emits a Stripe or OAuth redirect URL into shared
  output when its state may embed an API credential. Use a browser handoff or
  sanitize the URL first.
- Keep user-specific identifiers, key names, event IDs, schedules, and private
  URLs out of this public skill.

### 7. Run the proof gate

Run `scripts/verify_consultation.sh` for at least:

1. the next intended date
2. a later date in the same daylight-saving period
3. a date across a daylight-saving boundary when the timezone observes one

Then inspect the public page and confirm:

- title and description
- stated fee and payment method
- duration, timezone, and conferencing
- every intended start time
- deliberately unavailable gaps
- required intake fields
- no unintended dates or hours

Select a slot to inspect the intake form, but do not submit a test booking
without explicit authorization.

### 8. Clean up and report

Remove redundant schedules or partial duplicate event types created during a
failed setup. Preserve unrelated schedules and events.

Report:

- public booking URL
- event title, duration, price wording, and payment method
- recurring rule and exact start times
- conferencing and intake fields
- verification dates and result
- remaining manual steps or limitations

Do not call the setup complete until the live page and future slot inventory
both match the offer contract.
