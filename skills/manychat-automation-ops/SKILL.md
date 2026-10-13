---
name: manychat-automation-ops
description: Set up, inspect, and maintain ManyChat social automations using official APIs for supported contact and flow actions and the signed-in browser for dashboard-only configuration.
metadata:
  memory_tags:
    - domain:social-media
    - workflow:manychat-automation
    - skill_role:operator
    - repo_boundary:tools
---

# ManyChat Automation Ops

Use this skill for ManyChat comment-to-DM campaigns, existing flow invocation,
contact fields/tags, and automation maintenance. Read
[capability boundaries](references/capabilities.md) when selecting an API or
working with templates. Recheck the official schema before execution; channel,
account, plan, and messaging eligibility can differ.

## Establish the intended change

Resolve the signed-in workspace and connected channel, the exact target post
or campaign, trigger/keywords, approved copy and destination link, and intended
state (draft, live, updated, or stopped). Inspect existing automations and
preserve the user's selected opening DM, follow request, email collection,
reengagement/follow-up, timing, and targeting options. Ask only for missing
choices that materially affect execution.

Draft preparation is not permission to Go Live, Update a live automation, send
a flow/message, or change campaign ownership. Honor existing explicit
approval for the exact copy, audience/recipient, and action; otherwise prepare
a concrete reviewable result and obtain approval at that boundary. Do not
connect channels, change account types, grant access, or change billing unless
separately requested. Login/security prompts follow the computer-use tool's
confirmation policy.

## Select the supported surface

- Use documented HTTP API operations for supported reads and authorized
  contact/tag/field changes or invocation of an **existing** flow. There is no
  assumed ManyChat CLI. Do not use browser cookies as API credentials or replay
  undocumented dashboard requests.
- Creating/editing flow nodes, comment triggers, Quick Automations, publishing,
  stopping, and configuring/installing templates use the signed-in,
  user-controlled browser unless a current official endpoint explicitly
  supports the exact operation.
- For dashboard actions use `mcp__cua_repl.js` and its documented `cua` APIs.
  Initialize with a single discovery/selection call and read the returned
  documentation. Prefer the user's requested browser or existing signed-in
  session; otherwise follow the environment's browser default. For this
  workflow use accessibility/native input and screenshots, not Playwright,
  Playwright locators, a managed browser, page-injected scripts, or hidden
  network endpoints. If browser tab input is DOM-only, use the native browser
  app through `cua.getApp` instead. If no approved surface works, report the
  blocker. Read fresh UI state after actions before selecting new controls.

## Dashboard configuration

For Instagram comment-to-DM, use Automations → My Automations → New Automation
→ Auto-DM links from comments (or the appropriate existing Quick Automation).
Use the observed UI and current official guide, not assumed fixed labels.

Verify specific/any/next-post scope, keyword matching, public replies, opening
DM/button, link, email collection, follow request, and follow-up settings in
preview. Preserve optional selections; disabling the opening DM can remove
email collection and follow-up functionality. Only one next-post automation
can be active at a time. Inspect overlaps and ordering before activation.

Treat activation as handling future qualifying events. Do not promise replies
to old comments or run retrospective sends without a separate authorized,
eligible recipient plan. Repeated comments may not retrigger. A preview or
saved draft is not proof of delivery or live status.

## API execution and recovery

Use an existing authorized account API token via secure runtime configuration;
Profile API uses a separate profile token. Never print tokens, put them in
URLs/command arguments, or save credentials/contact exports in public files.
Treat generated single-use template installation links as redeemable access
capabilities: store them privately, redact them from public output and receipts,
and share only with the explicitly approved recipient/destination. Generating a
link does not authorize distributing it.
Use `Authorization: Bearer` over HTTPS to the official host. Confirm exact IDs
from documented reads or the visible dashboard; do not guess subscriber IDs,
channel identities, or `flow_ns` values from usernames.

Inspect the current request schema, channel restrictions, consent, messaging
window, response status/body, and rate limits before mutation. Field/tag changes
can trigger existing rules and sends; treat those effects as part of the
approved action. Creating a contact does not manufacture Instagram/Messenger
permission. Never invent opt-in or consent flags.

Record private minimal execution evidence keyed by account/channel, campaign,
recipient, and event. Mark sends pending before dispatch and record confirmed
or unknown outcome afterwards. No documented idempotency key should be assumed:
a timeout or ambiguous send response must not trigger blind retry. Reconcile
using available delivery evidence; otherwise stop and report unknown outcome.
Bound read retries, respect rate limits, and stop on auth/permission/policy
errors rather than trying alternate sending routes.

During a provider handoff, inspect overlapping triggers, define a cutover time,
reconcile already-handled events/recipients and pending sends, then disable the
old path only within approved scope before enabling the replacement. Do not
replay the backlog by default or leave two providers responding to the same
campaign. If old-provider state is inaccessible, hold activation and report
the overlap risk.

## Verification and handoff

For skill validation/audits use synthetic payloads and read-only docs/account
inspection. Do not send messages or change live automations just to test.
For authorized setup, verify saved configuration and intended live/draft state
in fresh UI; test delivery only with an explicitly authorized test recipient.
An API success response proves request acceptance, not delivery.

Report the automation/action, surface used, preserved options, verified state,
remaining delivery/eligibility limits, and private evidence location. Keep
account IDs, credentials, private history, screenshots, and run receipts in the
user's private adoption layer. Public skill files contain generic guidance only.
