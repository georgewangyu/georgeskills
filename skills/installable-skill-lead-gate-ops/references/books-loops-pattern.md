# Books/Loops-Style Install Gate Reference

This reference captures the reusable pattern for public websites that reveal an
installable agent skill command after collecting a name and email.

## Front Page Shape

Place the gate in the main installable-skill section, not on a separate form
page. The section should feel like a direct continuation of the product pitch:

- Left side: short product-specific promise and why the skill is useful.
- Right side before unlock: compact name/email form.
- Right side after unlock: command block, copy button, and repo-star action.

Use a two-column layout on desktop and a stacked layout on mobile. Keep the
container stable so the page does not jump when the command is revealed.

Suggested DOM/class shape:

```tsx
<section id="agent-setup" className="agent-setup">
  <div className="agent-setup__copy">
    <p className="eyebrow">Agent skill</p>
    <h2>Use {productName} in your agent.</h2>
    <p>{valueProposition}</p>
  </div>

  <div className="agent-setup__panel">
    {leadUnlocked ? (
      <div className="setup-command">
        <pre><code>{skillInstallCommand}</code></pre>
        <div className="setup-command__actions">
          <button type="button">Copy command</button>
          <a href={repoUrl}>Star the repo</a>
        </div>
        <p>Star {productName} to save it and support the project.</p>
      </div>
    ) : (
      <form className="unlock-form">
        <input name="name" autoComplete="name" required />
        <input name="email" type="email" autoComplete="email" required />
        <input name="website" tabIndex={-1} autoComplete="off" />
        <button type="submit">Unlock install command</button>
        <p>Unlocks the skill command and occasional updates. No spam.</p>
      </form>
    )}
  </div>
</section>
```

The `website` field is a hidden honeypot. Hide it visually and from normal tab
flow, but submit it so the API can silently ignore bot-like submissions.

## Client State

Recommended state names:

- `leadUnlocked`
- `leadStatus`: `idle | submitting | success | error`
- `leadError`
- `leadForm`: `name`, `email`, `website`

Persist unlock state in local storage with a product-scoped key:

```ts
const leadUnlockStorageKey = `${productSlug}:install-command-unlocked`;
```

Successful submission should:

- Store the unlock key.
- Reveal the command.
- Leave the command visible on refresh.
- Avoid storing the submitted email in local storage unless the app already has
  a clear need for it.

## API Contract

Default route shape for Next.js App Router:

```txt
POST /api/leads
```

Request body:

```json
{
  "name": "Example User",
  "email": "person@example.com",
  "website": ""
}
```

Response:

```json
{ "ok": true }
```

Validation rules:

- `name`: trimmed string, required, reasonable length.
- `email`: trimmed lowercase email, required.
- `website`: optional honeypot. If present, return `{ "ok": true }` without
  writing a row.

The API should never require a client-side Supabase key. Use a server-only
helper backed by `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

## Supabase Table

Use one shared table across products:

```sql
create table if not exists public.radar_leads (
  id uuid primary key default gen_random_uuid(),
  product text not null,
  email text not null,
  name text not null,
  source text not null default 'website-install-gate',
  consent_updates boolean not null default true,
  install_command_revealed boolean not null default true,
  repo_url text,
  referrer text,
  user_agent text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (product, email)
);

alter table public.radar_leads enable row level security;
```

Do not add public read/write policies for website visitors. The app route writes
with the server-side service role key.

Recommended upsert fields:

- `product`: product slug, such as `<product-slug>`.
- `email`
- `name`
- `source`: `website-install-gate`
- `consent_updates`: `true`
- `install_command_revealed`: `true`
- `repo_url`
- `referrer`
- `user_agent`
- `updated_at`: current timestamp

Use `on_conflict=product,email` or the SDK equivalent so repeat submissions
update the existing lead instead of creating duplicates.

## Deployment Env

Add these to local examples and deployment environments:

```txt
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

For Vercel, set both Preview and Production values when the site has both
environments. Redeploy after changing env vars. If a preview is protected by
SSO, external API smoke tests may redirect before reaching the app.

## UI Copy Defaults

Use this as the baseline and adapt the value proposition to the product:

- Heading: `Use <Product> in your agent.`
- Form button: `Unlock install command`
- Form note: `Unlocks the skill command and occasional updates. No spam.`
- Unlocked heading: `Install command unlocked`
- Copy button: `Copy command`
- Star CTA: `Star the repo`
- Star note: `Star <Product> to save it and support the project.`

Keep fields to name and email unless the user asks for more.

## Tests

When the repo has UI tests, cover:

- The install command is hidden before submission.
- Invalid or missing email shows a validation state.
- A successful mocked `/api/leads` response reveals the command.
- The copy button writes the command to the clipboard.
- The repo-star link points to the configured repo URL.
- The form and unlocked command fit on mobile without text overlap.

For API tests, cover:

- Valid lead creates/upserts a row.
- Honeypot submission returns success without writing.
- Missing env vars return a controlled server error.
- The service role key is never exposed in client bundles or docs.

## Guardrails

- Do not hardcode private Supabase project refs, account IDs, personal emails,
  personal handles, or local filesystem paths in reusable skill artifacts.
- Do not create one GitHub issue per lead; use Supabase or another database
  when the user wants lead collection.
- Do not gate access to the public repository itself. Gate only the website's
  install command reveal.
- Do not add newsletter sending or marketing automation unless requested.
- Do not log full service keys, request bodies, or production lead data during
  verification.
