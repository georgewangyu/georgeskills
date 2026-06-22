# SnackVoice-Inspired Design Language

Use this reference when a catalog should feel warm, polished, technical, and friendly without becoming playful or decorative.

## Transferable Principles

- Soft technical surfaces: off-white panels, warm inset areas, subtle translucent panel backgrounds.
- One restrained accent: use a purple or blue-purple accent for CTAs, focus rings, active states, and progress only.
- Rounded controls: pills for compact actions, 12-20px radius for inputs and textareas, larger panel radius only for major containers.
- Gentle depth: light borders plus soft shadows; avoid heavy drop shadows or floating card stacks.
- Friendly power-user tone: concise labels, compact metadata, no corporate marketing copy.
- Token-first styling: define colors, surfaces, borders, shadows, and focus rings once, then reuse them.

## Useful Token Shape

```css
:root {
  --color-text: #0f0f0f;
  --color-background: #fbfbfb;
  --color-surface-1: #fbfaf7;
  --color-surface-2: #ffffff;
  --color-surface-inset: #f4efe7;
  --color-surface-hover: #f5f1ff;
  --color-border: #e8e3d8;
  --color-border-strong: #d7cff8;
  --color-accent: #7c6feb;
  --color-accent-bg: #5a4fbf;
  --color-shadow-soft: 0 12px 30px rgba(35, 32, 54, 0.05);
  --color-shadow-medium: 0 18px 40px rgba(35, 32, 54, 0.08);
}
```

Adapt the accent to the product. Keep the surface, border, and shadow relationships.

## Control Defaults

- Buttons: rounded-full, medium weight, compact padding, clear disabled state.
- Inputs: soft surface, 12-16px radius, 1px border, subtle shadow, accent focus ring.
- Textareas: same as inputs, slightly larger radius, visible resize only when useful.
- Badges: small rounded labels for category and status.
- Tabs: rounded active pill, muted inactive text, no heavy underlines.

## Layout Defaults

- Use a max-width shell with a sticky topbar for prototypes.
- Keep the catalog above the form.
- Use a rail/list/detail composition on desktop.
- Collapse into a single readable column on mobile.
- Prefer row density over card grids when the user is scanning many resources.

## Avoid

- Hardcoded product-specific brand names or mascot references in reusable work.
- Hot pink or one-note purple gradients.
- Decorative blobs, bokeh, oversized heroes, or card mosaics.
- Copy that explains the UI instead of helping the user browse, copy, or contribute.
