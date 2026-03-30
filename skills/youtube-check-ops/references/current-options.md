# Current Options

## Practical rule

- Default assumption: the public YouTube channel page is enough for a quick check.
- If the user already has an API key and needs structured data, YouTube Data API is the clean official path.

## Official path

- YouTube Data API is the official structured interface for public channel/video metadata.
- It requires credentials and quota management.
- For a simple "check my public channel" task, direct public-page extraction is usually faster.

## Public extraction path

- Channel title and description are exposed in public metadata reliably.
- Subscriber counts may also appear in page text, often rounded.
- Some richer counts or tab data can move around with frontend changes.
