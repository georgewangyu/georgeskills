# Current Options

## Practical rule

- Default assumption: use the public profile page first.
- For visual confirmation or post-by-post inspection, use `playwright`.

## Official Meta paths

- Meta Graph API exists, but it is not a general anonymous public-profile lookup API.
- Access depends on app setup, permissions, and the account/business relationship involved.
- For "check this public Instagram profile for me," the public web page is usually the practical path unless the user already has the right app access.

### Authorized owned-account maintenance

- IGBot stores non-secret expiry metadata beside its private token. Run a
  non-mutating health check daily and refresh a valid long-lived token when it
  has fewer than 14 days remaining.
- A long-lived Instagram token is approximately 60 days, but the automation
  threshold is intentionally earlier so a missed run does not force OAuth.
- Once the token is expired or revoked, refresh is no longer a recovery path;
  require fresh OAuth consent and an exact redirect-URI match.
- Browser login cookies do not replace app OAuth authorization.

## Public extraction path

- Instagram often exposes title and summary information in public meta tags.
- Counts from those tags are useful, but they are a page-level summary and can be rounded.
- Public HTML structure can change without notice.
