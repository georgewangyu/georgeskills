---
name: sales-discovery-email-ops
description: Generate short, respectful first-touch lead messages for sales discovery across email, LinkedIn, DMs, or similar outreach, especially for consulting, services, workflow, or AI automation offers.
memory_tags:
  - domain:business
  - workflow:sales-discovery
  - skill_role:generator
  - repo_boundary:tools
  - inputs:offer-context
  - outputs:lead-message-drafts
  - risk:medium
---

# Sales Discovery Message Ops

## Trigger

Use when:
- the user wants first-touch outbound messages for a service, consulting offer, or design/build engagement
- the user wants to generate lead messages for email, LinkedIn, DMs, or similar outreach
- the goal is a discovery call, reply, or lightweight conversation
- the draft must avoid sounding like a teardown, pricing pitch, or generic spam

Do not use when:
- the user wants a proposal, quote, negotiation message, or closing message
- the recipient already asked for pricing or scope details
- the task is support, account management, or post-sale follow-up
- the user wants to critique an existing lead message; use the companion evaluator skill instead

## Workflow

1. Identify the actual goal of the first email:
   - start a conversation
   - get a quick discovery call
   - offer a few ideas, not a full audit
2. Anchor the email in one specific observation about the recipient:
   - keep it neutral
   - keep it visible and defensible
   - avoid stacking multiple criticisms
3. Establish credibility briefly:
   - role, domain expertise, or public proof
   - only the minimum social proof needed
4. State the lane clearly:
   - what you mainly help with
   - if relevant, mention adjacent capabilities in one sentence so the recipient is not surprised later
5. End with a soft CTA:
   - quick discovery call
   - or offer to send a few ideas
   - never force urgency unless the user explicitly wants that tone

## Generator / Evaluator Boundary

This is a **generator** skill. It should create plausible first-touch messages
from buyer, pain, offer, and proof context.

If the user already has a draft and wants to know whether it is good, specific,
or likely to get replies, use `sales-message-evaluator-ops` instead.

## Default Structure

```text
Hi {{name}},

I was looking at {{company}} and wanted to send a quick note.

I help {{target-type}} with {{core-outcome}}.

I came across {{company}} because {{neutral_observation}}.

{{brief_credibility}}

If this is relevant, would you be open to a quick 15-minute discovery call sometime next week? I’d be happy to share a few ideas for how I’d approach it.

Best,
{{sender}}
```

## DM / Short Message Structure

```text
Hey {{name}}, quick question.

I’m testing a small {{offer_type}} offer for {{target_type}}.

The idea is simple: {{specific_result}} without {{main_friction}}.

Do you have any recurring {{pain_area}} work right now that feels manual, annoying, or easy to forget?
```

## Tone Rules

- Keep the message short.
- Sound specific, not scripted.
- Use respectful curiosity, not teardown energy.
- Do not open with pricing.
- Do not promise detailed free work in the first email.
- Do not use vague agency phrases like `AI transformation` or `digital innovation`.
- Do not overuse hype, urgency, or social proof.

## Personalization Rules

- Use one observation only.
- Prefer language like:
  - `it feels like there may be an opportunity to...`
  - `the site could likely make X easier to understand`
  - `there may be room to simplify...`
- Avoid language like:
  - `your site is bad`
  - `this is outdated`
  - `your funnel is broken`
  - `you are losing customers`

## Category Patterns

### Website Remap

Lead with:
- clarity
- trust
- mobile experience
- booking or inquiry flow

Mention adjacent automation only briefly if true:
- `A big part of my work is also helping businesses automate repetitive internal tasks with practical AI workflows when that becomes relevant.`

### Workflow Automation

Lead with:
- repetitive admin
- intake
- follow-up
- document handling
- reporting

Keep the workflow guess narrow and concrete.

## Output Contract

Return:
- 2-5 subject line options
- one primary email draft
- one short DM/LinkedIn variant when useful
- one softer variant if tone is uncertain
- 1-3 bullet notes on why the personalization works

## Guardrails

- Optimize for reply rate, not cleverness.
- The first email should open the door, not dump the whole pitch.
- If social proof is weak or unfinished, prefer public creator/work examples over a weak product site.
- If the user has a better active proof asset than a company website, use that instead.
