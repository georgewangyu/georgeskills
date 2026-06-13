# Social Platform Fallbacks

Use this reference from social-media skills when lightweight CLI or API probes are blocked.

## Access Order

1. Prefer platform-specific CLI probes or official API paths when credentials and scope already exist.
2. Use `playwright` for public, clean-session visual checks when CLI output is incomplete.
3. Use `social-screen-control-ops` only when the user asks for local screen control, logged-in browser state is required, or public/browser probes are blocked.

## Screen-Control Limits

Screen control is a bounded viewing aid. Use it to inspect visible profiles, posts, captions, metadata, and page state.

Do not use it to send messages, post, comment, like, follow, change account settings, solve captchas, or enter credentials unless the user gives explicit task-specific approval at action time.

Keep media muted by default. Enable audio only when the user asks to listen or audio capture is required for an approved transcription task.
