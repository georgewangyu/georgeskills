# X-Native (xbot) Improvements

## Bot Detection Strategy (Anti-Bot Phase 2)

To address the recurring `Error 226` (Automated Bot Detection), we are moving to a **Hybrid Stealth Architecture** in the `xbot` repository:

1.  **Browserless-First (Efficiency)**: By default, the client sends raw HTTP requests with optimized headers (matching real browser signatures) and uses stored session tokens. This is the fastest method for daily exports.
2.  **Browser Fallback (Resilience)**: If a raw request is flagged or blocked, the system automatically escalates to **Full Browser Automation**.
3.  **Chrome Profile Reuse**: The native implementation reuses your actual Google Chrome profile (`Default`). This includes real cookies, active session history, and consistent device fingerprinting, making the automation indistinguishable from a human user.
4.  **Stealth Plugin**: Utilizes `playwright-extra-plugin-stealth` to hide automation signals (like the `navigator.webdriver` flag).

## Next Steps
- [ ] **Adaptive Scheduling**: Implement randomized delays between actions to mimic human typing and reading patterns.
- [ ] **Automatic Token Refresh**: Add a module to extract fresh tokens from the browser session automatically when they expire.
- [ ] **Headless Preference**: Optimize the "headless" flag to ensure it doesn't leak automation markers while keeping the UI hidden.
