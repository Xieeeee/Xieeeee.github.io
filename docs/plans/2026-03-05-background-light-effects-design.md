# Background Light Effects Design

**Date:** 2026-03-05
**Status:** Approved

## Summary

Add slow, smooth dynamic background light effects to the personal portfolio website. The effect should feel like light through frosted glass — layered shifting gradients with a subtle noise/grain texture overlay — creating atmosphere without distracting from content.

## Requirements

- **Coverage:** All pages (persistent across the entire site)
- **Visibility:** Moderate — clearly visible but not distracting
- **Theme behavior:** Adapts to light/dark mode
  - Light mode: warm tones (dusty rose, warm amber, pale lavender)
  - Dark mode: moody cool tones (muted teal echoing `#2698ba`, deep indigo, cool charcoal-blue)

## Approach: Pure CSS Pseudo-elements

No JavaScript, no dependencies. The effect is implemented entirely via CSS on `body::before` (gradient layer) and `body::after` (grain/noise layer).

### Layer Structure

| Layer | Element | Purpose |
|---|---|---|
| Gradient | `body::before` | Shifting radial gradients for the light color effect |
| Grain | `body::after` | SVG `feTurbulence` noise texture for frosted-glass feel |

Both layers are:
- `position: fixed` — cover the full viewport at all times
- `pointer-events: none` — never interfere with content interaction
- `z-index: -1` — sit behind all page content

### Animations

Two independent `@keyframes`:

1. **`bg-shift`** — 20s, `ease-in-out`, `infinite alternate`
   - Moves gradient `background-position` by ~15% on each axis
   - Creates slow drifting light feel

2. **`grain-drift`** — 8s, `ease-in-out`, `infinite alternate`
   - Offsets the noise texture position by a few pixels
   - Gives grain a subtle living quality

Both use `will-change: transform` for GPU compositing.

### Light Mode Colors

- Radial gradient 1: `rgba(240, 200, 180, 0.45)` — warm rose/peach (top-left area)
- Radial gradient 2: `rgba(255, 220, 150, 0.35)` — warm amber (center-right)
- Radial gradient 3: `rgba(210, 190, 240, 0.30)` — pale lavender (bottom-left)
- Grain opacity: `0.04`

### Dark Mode Colors

- Radial gradient 1: `rgba(38, 152, 186, 0.20)` — muted teal (`#2698ba` base)
- Radial gradient 2: `rgba(60, 40, 120, 0.25)` — deep indigo (center-right)
- Radial gradient 3: `rgba(20, 40, 80, 0.30)` — cool charcoal-blue (bottom-left)
- Grain opacity: `0.03`

## Implementation

**File to modify:** `_sass/_base.scss`

Add pseudo-element rules under the `body` block, keyframe definitions, and theme-reactive color variables. The grain SVG filter is an inline `data:image/svg+xml` URI — no external file needed. Theme reactivity uses existing `:root` (light) and `html[data-theme="dark"]` (dark) CSS patterns matching `_themes.scss`.

## Non-goals

- No JavaScript animation loop
- No canvas element
- No external image files for the grain texture
- No mouse-tracking interaction
