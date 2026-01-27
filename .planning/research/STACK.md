# Technology Stack: CSS Design System Migration

**Project:** Legacy CSS to Design Token System Migration
**Domain:** Flask/Jinja2 + Bootstrap 5 Web Application
**Researched:** 2026-01-26
**Overall Confidence:** HIGH

---

## Executive Summary

This research focuses on the **Stack dimension** for migrating legacy CSS (inline styles, hardcoded hex colors) to a design token system in an existing Bootstrap 5 + Jinja2 application with 363 templates.

**Key Finding:** The existing `_design-tokens.css` file is already well-structured with HSL-based tokens and Bootstrap 5 integration. The migration path should leverage **pure CSS features** (no build tools) with **CSS Cascade Layers** for safe override management and the **`light-dark()` function** for simplified theming.

---

## Current State Analysis

| Metric | Count | Notes |
|--------|-------|-------|
| Total HTML templates | 363 | Verified via find command |
| Templates with `<style>` blocks | 104 | Inline CSS needs extraction |
| Templates with hardcoded hex colors | 100 | Priority targets for migration |
| Lines with hex color codes | 1,472 | ~15 colors per affected template avg |
| Inline `style=` attributes | 1,258 | Component-level overrides |
| Bootstrap versions in use | Mixed 5.1.3 / 5.3.0 | Standardization needed |

**Existing Token System:** `/app/static/css/_design-tokens.css`
- 711 lines, HSL-based hierarchy (0%->5%->10%->15%)
- Dark mode default with light mode support via `[data-bs-theme]`
- Bootstrap 5 CSS variable mapping already implemented
- Legacy compatibility aliases present (planned for removal)

---

## Recommended Stack

### Core Approach: Pure CSS (No Build Tools)

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| CSS Custom Properties | Level 1 (native) | Design token implementation | HIGH |
| CSS Cascade Layers | `@layer` (native) | Override management, specificity control | HIGH |
| `light-dark()` function | CSS Color Level 5 | Theme switching simplification | MEDIUM |
| Bootstrap | 5.3.3 | UI framework (standardize version) | HIGH |
| Container Queries | CSS Level 3 | Component-level responsiveness | HIGH |

**Rationale:** The project explicitly requires "no build tools/preprocessors." Modern CSS (2024-2026) has matured sufficiently that Sass/PostCSS are no longer necessary for design systems. CSS Custom Properties, Cascade Layers, and `light-dark()` provide all needed functionality natively.

### Why NOT Use Build Tools

| Tool | Why Not Use |
|------|-------------|
| **Sass/SCSS** | Adds build complexity; modern CSS has nesting, variables, and color functions natively |
| **PostCSS** | Project constraint: pure CSS only; most transforms now unnecessary |
| **Tailwind CSS** | Would require complete rewrite; incompatible with existing Bootstrap patterns |
| **Style Dictionary** | Requires JSON/YAML source + build step; overkill for CSS-only system |

---

## Technology Details

### 1. CSS Cascade Layers (`@layer`)

**Version:** Native CSS, shipped in all major browsers since March 2022
**Browser Support:** 96.7% global (Can I Use, Jan 2026)
**Confidence:** HIGH (verified via MDN, CSS-Tricks)

**Purpose:** Safely manage specificity when overriding Bootstrap and legacy styles without `!important` proliferation.

**Recommended Layer Structure:**
```css
/* Declare layer order at top of main stylesheet */
@layer reset, bootstrap, tokens, components, utilities, overrides;

/* Import Bootstrap into its layer */
@import url('bootstrap.min.css') layer(bootstrap);

/* Design tokens in their own layer */
@layer tokens {
  :root {
    --bg-dark: hsl(0 0% 0%);
    --bg: hsl(0 0% 5%);
    /* ... */
  }
}

/* Component styles override bootstrap */
@layer components {
  .card { /* ... */ }
}

/* Page-specific overrides (last = highest priority) */
@layer overrides {
  /* Legacy inline styles migrate here */
}
```

**Benefits for Migration:**
- Inline `<style>` blocks can be moved to `@layer overrides` without breaking existing pages
- Bootstrap overrides become explicit, not specificity wars
- Gradual migration: unlayered CSS has implicit highest priority, so existing code continues working

**Sources:**
- [MDN @layer Reference](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@layer)
- [CSS-Tricks Cascade Layers Guide](https://css-tricks.com/css-cascade-layers/)
- [Smashing Magazine Cascade Layers](https://www.smashingmagazine.com/2022/01/introduction-css-cascade-layers/)

---

### 2. CSS `light-dark()` Function

**Version:** CSS Color Level 5
**Browser Support:** 93%+ (Chrome 123+, Firefox 120+, Safari 17.5+)
**Baseline Status:** Newly Available (May 2024), Widely Available by Nov 2026
**Confidence:** MEDIUM (newer feature, fallback strategy required)

**Purpose:** Simplify dark/light mode switching without duplicating all color definitions.

**Current Approach (verbose):**
```css
:root {
  --text: hsl(0 0% 95%);
}
[data-bs-theme="light"] {
  --text: hsl(0 0% 5%);
}
```

**With `light-dark()` (simplified):**
```css
:root {
  color-scheme: light dark;
  --text: light-dark(hsl(0 0% 5%), hsl(0 0% 95%));
}
```

**Fallback Strategy:**
```css
/* Fallback for older browsers */
--text: hsl(0 0% 95%);
/* Modern browsers override */
--text: light-dark(hsl(0 0% 5%), hsl(0 0% 95%));
```

**Recommendation:** Adopt `light-dark()` for NEW tokens; keep existing dual-definition pattern for legacy compatibility during migration. Convert after Nov 2026 when "Widely Available."

**Sources:**
- [MDN light-dark()](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/light-dark)
- [Can I Use light-dark](https://caniuse.com/mdn-css_types_color_light-dark)
- [CSS-Tricks Almanac](https://css-tricks.com/almanac/functions/l/light-dark/)

---

### 3. Container Queries

**Version:** CSS Containment Module Level 3
**Browser Support:** 95%+ (all major browsers since Feb 2023)
**Confidence:** HIGH (verified, stable feature)

**Purpose:** Component-level responsiveness (cards, modals, tables adapt to container, not viewport).

**Usage:**
```css
.card-container {
  container-type: inline-size;
  container-name: card;
}

@container card (min-width: 400px) {
  .card-content {
    display: grid;
    grid-template-columns: 1fr 2fr;
  }
}
```

**Migration Value:** Replace many `@media` queries with `@container` for truly reusable components. Tables and cards in this system would benefit significantly.

**Sources:**
- [MDN Container Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_queries)
- [LogRocket Container Queries 2026](https://blog.logrocket.com/container-queries-2026/)

---

### 4. Bootstrap Version Standardization

**Current State:** Mixed 5.1.3 and 5.3.0 across templates
**Recommended:** Bootstrap 5.3.3 (latest stable as of Jan 2026)
**Confidence:** HIGH

**Why 5.3.x Specifically:**
- Native `[data-bs-theme]` attribute for dark mode (matches existing implementation)
- Full CSS Custom Properties support for all components
- Color mode utilities (`data-bs-theme="dark"` auto-propagates to components)
- Component-specific CSS variables (`.btn` has `--bs-btn-*` hooks)

**Migration Steps:**
1. Update CDN links to consistent `bootstrap@5.3.3`
2. Existing `_design-tokens.css` already maps to Bootstrap CSS vars
3. Remove Bootstrap 4 compatibility shims after full migration

**Source:** [Bootstrap 5.3 Official Docs](https://getbootstrap.com/docs/5.3/customize/css-variables/)

---

### 5. Optional: OKLCH Color Space (Future Enhancement)

**Version:** CSS Color Level 4
**Browser Support:** 93%+ (Chrome 111+, Firefox 113+, Safari 15.4+)
**Confidence:** MEDIUM (recommended for NEW palettes, not required for migration)

**Why Consider:**
- Perceptually uniform lightness (better than HSL for generating scales)
- P3 wide-gamut color support for modern displays
- Easier programmatic color manipulation

**Current System:** HSL-based (functional, no immediate need to change)

**Recommendation:** Keep HSL for existing tokens. Use OKLCH if adding new semantic colors or creating programmatic color scales in the future.

**Example Future Token:**
```css
--accent-primary: oklch(75% 0.18 85); /* Amber in OKLCH */
```

**Sources:**
- [Evil Martians OKLCH Guide](https://evilmartians.com/chronicles/oklch-in-css-why-quit-rgb-hsl)
- [OKLCH Color Picker](https://oklch.org)

---

## Supporting Tools

### Linting: Stylelint

**Version:** 16.x (current stable)
**Purpose:** Enforce design token usage, catch hardcoded colors
**Confidence:** HIGH

**No-Build Integration:** Works via VS Code extension or CLI without build pipeline.

**Recommended Configuration:**
```json
{
  "extends": ["stylelint-config-standard"],
  "rules": {
    "color-no-hex": true,
    "declaration-property-value-no-unknown": true,
    "custom-property-pattern": "^(bg|text|border|amber|semantic|gray|radius|shadow|space|font|transition)-"
  }
}
```

**Custom Rule Potential:** Create `no-hardcoded-colors` rule to flag hex values not in approved list.

**Sources:**
- [Stylelint Official Docs](https://stylelint.io/)
- [Stylelint GitHub](https://github.com/stylelint/stylelint)

---

### Migration Tooling

| Tool | Purpose | Recommendation |
|------|---------|----------------|
| **AI-assisted conversion** | Convert inline CSS to tokens | USE: Claude/ChatGPT can convert ~100 lines at a time with high accuracy |
| **Manual review** | Verify semantic correctness | REQUIRED: Human review of token mapping |
| **Stylelint** | Prevent regression | USE: Custom rules catch new hardcoded colors |
| **JSCodeshift** | AST-based transforms | SKIP: Overkill for CSS; more suited for JS |

**Practical Workflow:**
1. Extract inline `<style>` content from template
2. Use AI to convert hardcoded values to `var(--token)` references
3. Review for semantic correctness (is this really `--text-muted`?)
4. Move to appropriate cascade layer
5. Test in both light/dark modes

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| Token Format | CSS Custom Properties | Style Dictionary JSON | Requires build step, JSON->CSS transform |
| Theming | `light-dark()` + data attributes | `prefers-color-scheme` only | No user toggle support |
| Framework | Keep Bootstrap 5 | Migrate to Pico/Open Props | Too disruptive; Bootstrap already integrated |
| Specificity | Cascade Layers | BEM + strict conventions | Doesn't solve 3rd-party override issues |
| Colors | HSL (existing) | OKLCH | Migration cost > benefit for existing palette |
| Responsiveness | Container Queries | Media Queries only | Less component-reusable |

### Open Props Consideration

**What it is:** Pure CSS design token library (by Adam Argyle, Google)
**Why NOT recommended:**

1. Naming conflicts with existing `--bg`, `--text` tokens
2. Different philosophy (utility-first vs semantic)
3. Would require remapping 100+ templates
4. Existing token system is well-designed; no need to replace

**When to use:** Greenfield projects without existing design systems.

---

## Installation / Integration

No installation required - all recommended technologies are native CSS.

### Stylesheet Loading Order

```html
<!-- 1. Bootstrap (CDN) -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet">

<!-- 2. Design Tokens (local) -->
<link href="{{ url_for('static', filename='css/_design-tokens.css') }}"
      rel="stylesheet">

<!-- 3. Component Styles (local) - uses cascade layers internally -->
<link href="{{ url_for('static', filename='css/components.css') }}"
      rel="stylesheet">
```

### Future Enhancement: Cascade Layer Import

When standardizing Bootstrap loading:
```css
/* In a future main.css */
@layer reset, bootstrap, tokens, components, utilities, overrides;

@import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css')
        layer(bootstrap);
```

**Note:** `@import` with `layer()` requires the import to be at the top of the file. This may require restructuring how CSS is loaded in `base.html`.

---

## Migration Priority Matrix

| Phase | Target | Effort | Impact |
|-------|--------|--------|--------|
| **P0** | Standardize Bootstrap 5.3.3 | Low | Enables all other improvements |
| **P1** | Extract 30 worst `<style>` blocks | Medium | Reduces inline CSS by ~30% |
| **P2** | Add cascade layers to `_design-tokens.css` | Low | Safe override management |
| **P3** | Convert hex colors in 100 templates | High | Design consistency |
| **P4** | Implement `light-dark()` for new tokens | Low | Simplified theming |
| **P5** | Add container queries to cards/tables | Medium | Better responsive UX |

---

## Confidence Assessment Summary

| Technology | Confidence | Reason |
|------------|------------|--------|
| CSS Custom Properties | HIGH | Native, 97%+ support, already in use |
| CSS Cascade Layers | HIGH | Native, 96%+ support, well-documented |
| `light-dark()` | MEDIUM | 93% support, but fallback needed until Nov 2026 |
| Bootstrap 5.3 | HIGH | Official docs, stable release |
| Container Queries | HIGH | 95%+ support, standard feature |
| Stylelint | HIGH | Mature tool, active development |
| OKLCH | MEDIUM | Good support, but migration cost for existing HSL |

---

## Sources

### Official Documentation (HIGH confidence)
- [Bootstrap 5.3 CSS Variables](https://getbootstrap.com/docs/5.3/customize/css-variables/)
- [MDN CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [MDN @layer](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@layer)
- [MDN light-dark()](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/light-dark)
- [MDN Container Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_queries)

### Browser Support (HIGH confidence)
- [Can I Use light-dark](https://caniuse.com/mdn-css_types_color_light-dark)
- [Can I Use Container Queries](https://caniuse.com/css-container-queries)

### Industry Best Practices (MEDIUM confidence)
- [CSS-Tricks Design Tokens Guide](https://css-tricks.com/what-are-design-tokens/)
- [CSS-Tricks Cascade Layers](https://css-tricks.com/css-cascade-layers/)
- [Smashing Magazine CSS Custom Properties Strategy](https://www.smashingmagazine.com/2018/05/css-custom-properties-strategy-guide/)
- [Evil Martians OKLCH](https://evilmartians.com/chronicles/oklch-in-css-why-quit-rgb-hsl)
- [LogRocket Container Queries 2026](https://blog.logrocket.com/container-queries-2026/)

### Tooling (HIGH confidence)
- [Stylelint Official](https://stylelint.io/)
- [Open Props](https://open-props.style/) (evaluated, not recommended)

---

## Open Questions

1. **CDN vs Local Bootstrap:** Should Bootstrap be loaded from CDN (current) or bundled locally for reliability?
2. **Legacy Browser Support:** What's the minimum browser version requirement? (Affects `light-dark()` adoption timeline)
3. **Stylelint Integration:** Should linting be added to CI/CD or remain developer-local?

---

*Research produced by GSD Project Researcher agent for CSS Design System Migration milestone.*
