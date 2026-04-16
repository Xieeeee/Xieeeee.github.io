# Background Light Effects Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add slow, smooth frosted-glass background light effects (shifting gradients + grain texture) to all pages, adapting to light/dark mode.

**Architecture:** Two CSS pseudo-elements on `body` — `::before` for animated radial gradient layers, `::after` for an SVG noise grain overlay. Colors are CSS custom properties defined in `_themes.scss`. Keyframes and pseudo-element rules go in `_base.scss`. Zero JavaScript, zero external assets.

**Tech Stack:** SCSS, CSS custom properties, CSS `@keyframes`, inline SVG data URI for grain texture, Jekyll/al-folio

---

### Task 1: Add theme color variables for gradient layers

**Files:**
- Modify: `_sass/_themes.scss`

The existing `:root` block (light mode) and `html[data-theme="dark"]` block each need new CSS custom properties for the three gradient stop colors. This keeps theme reactivity consistent with the rest of the site.

**Step 1: Open the file and locate the two theme blocks**

The file has two blocks to modify:
- `:root { ... }` — light mode (around line 5)
- `html[data-theme="dark"] { ... }` — dark mode (around line 68)

**Step 2: Add light mode gradient variables inside `:root { ... }`**

Add these lines before the closing `}` of the `:root` block:

```scss
  // Background light effect gradient colors (light mode)
  --bg-gradient-1: rgba(240, 200, 180, 0.45);
  --bg-gradient-2: rgba(255, 220, 150, 0.35);
  --bg-gradient-3: rgba(210, 190, 240, 0.30);
  --bg-grain-opacity: 0.04;
```

**Step 3: Add dark mode gradient variables inside `html[data-theme="dark"] { ... }`**

Add these lines before the closing `}` of the dark mode block:

```scss
  // Background light effect gradient colors (dark mode)
  --bg-gradient-1: rgba(38, 152, 186, 0.20);
  --bg-gradient-2: rgba(60, 40, 120, 0.25);
  --bg-gradient-3: rgba(20, 40, 80, 0.30);
  --bg-grain-opacity: 0.03;
```

**Step 4: Commit**

```bash
git add _sass/_themes.scss
git commit -m "feat: add CSS variables for background light effect gradient colors"
```

---

### Task 2: Add keyframe animations to `_base.scss`

**Files:**
- Modify: `_sass/_base.scss`

Two independent `@keyframes` definitions. Add them right after the existing `@keyframes fadeInUp` block (around line 15–28 of `_base.scss`).

**Step 1: Locate the existing `fadeInUp` keyframe in `_base.scss`**

It ends around line 24. Add the new keyframes immediately after.

**Step 2: Add the two keyframes**

```scss
// Background light effect animations
@keyframes bg-shift {
  0% {
    background-position: 0% 0%, 100% 50%, 50% 100%;
  }
  100% {
    background-position: 15% 10%, 85% 40%, 35% 90%;
  }
}

@keyframes grain-drift {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(3px, 2px);
  }
}
```

**Step 3: Commit**

```bash
git add _sass/_base.scss
git commit -m "feat: add bg-shift and grain-drift keyframe animations"
```

---

### Task 3: Add the gradient layer pseudo-element (`body::before`)

**Files:**
- Modify: `_sass/_base.scss`

Add the gradient pseudo-element rule. Place it after the `body { ... }` block (around line 12) and before the `// Page load animations` comment.

**Step 1: Add `body::before` rule**

```scss
body::before {
  content: '';
  position: fixed;
  inset: -20%;
  width: 140%;
  height: 140%;
  pointer-events: none;
  z-index: -1;
  background-image:
    radial-gradient(ellipse 60% 50% at 20% 30%, var(--bg-gradient-1), transparent),
    radial-gradient(ellipse 50% 60% at 80% 50%, var(--bg-gradient-2), transparent),
    radial-gradient(ellipse 70% 55% at 40% 80%, var(--bg-gradient-3), transparent);
  background-size: 140% 140%;
  animation: bg-shift 20s ease-in-out infinite alternate;
  will-change: background-position;
}
```

Note: `inset: -20%` and `width/height: 140%` make the layer slightly oversized so the edges never show a hard cutoff as gradients drift.

**Step 2: Verify the Jekyll site still builds**

Run: `bundle exec jekyll build`
Expected: Build completes with no SCSS compile errors.

**Step 3: Commit**

```bash
git add _sass/_base.scss
git commit -m "feat: add animated gradient background layer via body::before"
```

---

### Task 4: Add the grain/noise layer pseudo-element (`body::after`)

**Files:**
- Modify: `_sass/_base.scss`

Add the grain pseudo-element rule immediately after the `body::before` block added in Task 3.

**Step 1: Add `body::after` rule**

The grain texture uses an inline SVG with `feTurbulence`. The SVG is URL-encoded for use as a CSS `background-image` data URI.

```scss
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: -1;
  opacity: var(--bg-grain-opacity);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 200px 200px;
  animation: grain-drift 8s ease-in-out infinite alternate;
  will-change: transform;
}
```

Explanation of SVG:
- `feTurbulence type='fractalNoise'` — generates a static noise pattern
- `baseFrequency='0.65'` — controls grain density (higher = finer grain)
- `numOctaves='3'` — adds detail layers to the noise
- `stitchTiles='stitch'` — makes the tile seamlessly repeatable
- `feColorMatrix saturate=0` — desaturates to pure grey grain

**Step 2: Verify the Jekyll site builds**

Run: `bundle exec jekyll build`
Expected: No errors.

**Step 3: Preview visually (optional but recommended)**

Run: `bundle exec jekyll serve`
Open `http://localhost:4000` in a browser. You should see:
- Soft warm color glow in the background (light mode)
- Barely-visible grain texture over it
- Toggle dark mode — the glow should shift to cool teal/indigo tones

**Step 4: Commit**

```bash
git add _sass/_base.scss
git commit -m "feat: add animated grain texture overlay via body::after"
```

---

### Task 5: Verify theme transitions work cleanly

**Files:**
- No code changes — verification only

The site has a theme transition class (`html.transition`) in `_base.scss` (around line 1132) that applies `transition: all 750ms` to everything during a theme switch. This will smoothly fade the gradient colors between light and dark mode automatically, since the gradient uses CSS custom properties.

**Step 1: Test in browser**

Run: `bundle exec jekyll serve`

1. Open `http://localhost:4000`
2. Click the light/dark toggle in the navbar
3. Expected: gradient colors crossfade smoothly over ~750ms as the theme switches
4. Check a few other pages (publications, CV) — effect should be present on all pages

**Step 2: Check for any visual regressions**

- Navbar text/links should be fully readable
- Card backgrounds should still appear solid (cards use `var(--global-card-bg-color)` with no transparency)
- Footer should render cleanly

**Step 3: Commit (if no issues)**

No code changes needed if all looks good. If you see any z-index layering issues (e.g., the gradient appearing on top of content), increase `z-index` on the main content areas or lower the pseudo-element `z-index` further (e.g., `-2`).

---

## Summary of all changed files

| File | Change |
|---|---|
| `_sass/_themes.scss` | Add 4 CSS custom properties to `:root` and `html[data-theme="dark"]` |
| `_sass/_base.scss` | Add 2 `@keyframes`, `body::before`, `body::after` |

Total new CSS: ~50 lines. Zero new files, zero JS, zero external assets.
