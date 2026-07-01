---
name: sales-message-evaluator-ops
description: Evaluate and improve an existing first-touch lead message, sales discovery DM, or outbound email against buyer specificity, pain clarity, offer strength, proof, CTA, tone, and reply-likelihood.
memory_tags:
  - domain:business
  - workflow:sales-discovery
  - skill_role:evaluator
  - repo_boundary:tools
  - inputs:message-draft
  - outputs:message-rubric
  - risk:medium
---

# Sales Message Evaluator Ops

## Trigger

Use when:
- the user has a draft outbound email, LinkedIn message, DM, or sales discovery
  message and asks whether it is good
- the user wants a rubric-based critique before sending lead outreach
- the task is improving reply likelihood, specificity, CTA clarity, or tone
- the user wants to compare multiple lead-message variants

Do not use when:
- the user needs a fresh message from scratch; use the generator skill instead
- the message is a proposal, contract, negotiation, or close-stage email
- the user is asking for inbox triage, customer support, or account management

## Inputs

- Required: message draft
- Strongly preferred: target buyer, channel, offer, goal of the message
- Optional: recipient context, proof asset, desired tone, pricing, follow-up
  sequence, known objections

## Workflow

1. Identify the message's job:
   - reply
   - discovery call
   - permission to send ideas
   - beta conversation
   - referral or intro
2. Score the draft on the rubric below.
3. Name the top failure mode before rewriting.
4. Rewrite only as much as needed to fix the failure mode.
5. Return the improved version plus a short send/no-send decision.

## Rubric

Score each category from `0-2`:

- **Buyer specificity**: names a clear buyer type or recipient context.
- **Pain clarity**: points to a concrete repeated problem, not a vague benefit.
- **Offer clarity**: says what help is being offered in plain language.
- **Proof / credibility**: includes enough credibility without peacocking.
- **CTA quality**: asks for one small next step, not a giant commitment.
- **Tone**: respectful, specific, non-needy, non-pushy.
- **Brevity**: short enough for the channel.
- **Reply likelihood**: easy for the recipient to answer.

Interpretation:

- `14-16`: sendable; minor edits only.
- `10-13`: close; fix the top issue before sending.
- `6-9`: weak; rewrite before sending.
- `0-5`: do not send; the message is likely generic, confusing, or too heavy.

## Common Failure Modes

- Too much explanation before the ask.
- Selling the tool instead of the outcome.
- Vague market language like `AI transformation`, `digital innovation`, or
  `streamline operations`.
- No specific pain.
- No clear recipient reason.
- CTA asks for too much too soon.
- Social proof is louder than the buyer problem.
- Message sounds like a teardown or insult.

## Output Contract

Return:

- channel and assumed goal
- total score and category scores
- top failure mode
- send/no-send decision
- revised message
- one optional follow-up line
- what to learn from replies or silence

## Boundaries

- Do not invent private proof, credentials, client results, revenue, or case
  studies.
- If the offer is vague, say so and propose the smallest concrete offer shape.
- Optimize for starting a real buyer conversation, not sounding impressive.
