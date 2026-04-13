---
name: stripe-ops
description: Use when a repo needs Stripe setup or maintenance through local shared credentials, Stripe CLI, and the installed upstream Stripe skills.
memory_tags:
  - domain:payments
  - workflow:stripe-setup
  - repo_boundary:tools
  - risk:high
---

# Stripe Ops

## Trigger

Use when:
- a repo needs Stripe Checkout, products, prices, webhook forwarding, or environment wiring
- the task is local Stripe setup using shared private credentials from `<private-repo>`
- the user asks where Stripe credentials or shared Stripe defaults live across repos

Do not use when:
- the task is purely Stripe architecture guidance with no local setup; use the installed upstream Stripe skills directly
- the task would require hardcoding private credentials into `georgeskills`

## Inputs

- Required: target repo path and whether the task is `test` or `live`
- Optional: product name, price amount, billing interval, webhook route, production domain

## Workflow

1. Load the installed upstream Stripe skills first when they are relevant:
   - `stripe-best-practices` for API and security decisions
   - `stripe-projects` for project bootstrapping
   - `upgrade-stripe` for SDK or API-version upgrades
2. Load shared private credentials from:
   - `<private-repo>/.tokens/stripe.env`
   Example:
   ```bash
   source "$LIFEREPO_PRIVATE_ROOT/.tokens/stripe.env"
   ```
3. Verify local Stripe CLI access before touching a repo:
   ```bash
   stripe config --list
   stripe accounts retrieve
   ```
4. Create or inspect products and prices with the CLI using the sourced key:
   ```bash
   stripe products list --live --limit 20
   stripe prices list --live --limit 20
   stripe products create --live --name "<product>" --type service --confirm
   stripe prices create --live --product <prod_id> --currency usd --unit-amount <amount_cents> --confirm
   ```
5. Wire project-local env files only inside the target repo. Keep secrets in local-only files such as:
   - `backend/.env.live.local`
   - `backend/.env.test.local`
   - `.env.local`
6. For local webhook testing, use Stripe CLI forwarding:
   ```bash
   stripe listen --forward-to localhost:<port>/<webhook-route>
   ```
   Copy the emitted `whsec_...` into the repo-local test env, not into `georgeskills`.
7. For production webhook setup, create the endpoint in Stripe for the deployed backend URL and store the resulting live `whsec_...` only in repo-local or deployment secrets.

## Output Contract

- Stripe account context used
- created or reused product and price IDs
- which repo-local env file was updated
- whether webhook setup is local-only or production-ready
- remaining missing live secrets such as SMTP or production webhook secret

## Guardrails

- Never commit Stripe secrets, webhook secrets, or personal account identifiers into `georgeskills`.
- Treat `<private-repo>/.tokens/stripe.env` as the shared local credential source of truth.
- Prefer repo-local env files for project-specific values like price IDs and webhook secrets.
- If a live secret was pasted into chat or exposed in logs, rotate it after setup.
