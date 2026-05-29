# Watchlist Format

Store real account watchlists in a private repo. Use a markdown table so the list is easy to edit by hand.

Required columns:

- `platform`: `youtube`, `tiktok`, or `instagram`
- `handle`: account handle, channel name, or profile username

Recommended columns:

- `url`: profile/channel URL
- `query`: optional platform-specific search seed; useful for YouTube when the handle alone is ambiguous
- `niche`: short category label
- `priority`: `watch-first`, `normal`, or `low`
- `notes`: why this account matters

Example:

```markdown
# Niche Account Watchlist

| platform | handle | url | query | niche | priority | notes |
|---|---|---|---|---|---|---|
| tiktok | examplecreator | https://www.tiktok.com/@examplecreator | examplecreator | software engineer comedy | watch-first | Strong on-call skits |
| instagram | examplecreator | https://www.instagram.com/examplecreator/ | examplecreator | developer lifestyle | normal | Reels pacing reference |
| youtube | Example Channel | https://www.youtube.com/@examplechannel | Example Channel AI coding shorts | AI coding | normal | Shorts about AI developer tools |
```

Tips:

- Keep handles generic or private-safe in public examples.
- Put sensitive notes in the private repo only.
- If a platform collector is flaky, keep the account in the watchlist anyway; the skill should report platform failures and continue.
- For YouTube, use a specific `query` if the handle can collide with unrelated names, products, or celebrities.
