# X-Native Xbot Improvements

## Bot Detection Strategy

**Captured**: 2026-07-04
**Status**: open
**Priority**: high

### User Problem

X can return `Error 226` automated-bot-detection failures during daily feed
checks. When that happens, the workflow loses its low-friction public-notebook
input surface.

### Product Principle

X checking should be resilient but conservative: use the native xbot path first,
escalate only when blocked, and avoid noisy or risky public actions.

### V1 Improvement

Move toward a hybrid stealth architecture:

- Browserless-first requests for fast daily exports.
- Full browser automation fallback only when raw requests are blocked.
- Chrome profile reuse for session continuity when browser fallback is needed.
- Stealth hardening for obvious automation markers.

### Future Builds

- Adaptive scheduling with randomized delays between actions.
- Automatic token refresh from the browser session when tokens expire.
- Headless-mode tuning that does not leak automation markers.

### Acceptance Criteria

- Daily feed checks prefer the xbot CLI path.
- Bot-detection failures are reported with the fallback attempted.
- The workflow does not silently switch to posting, liking, replying, or other
  public actions.
- Failures preserve enough diagnostics for the next maintenance pass.
