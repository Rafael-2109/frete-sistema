# Phase 2: Component Library - Research

**Researched:** 2026-01-27
**Domain:** CSS Component Library with Dark/Light Mode Theming
**Confidence:** HIGH

## Summary

This phase focuses on extracting reusable CSS component patterns from inline styles into a centralized component library that functions correctly in both dark and light modes. The research confirms that the existing CSS Layer infrastructure (Phase 1) provides an excellent foundation for component organization.

Key findings:
1. The system already has extensive component styles in `_design-tokens.css` that need to be migrated to `@layer components`
2. Bootstrap 5.3.3 provides native CSS variable support for component customization with `data-bs-theme` attribute
3. The elevation system should follow Material Design principles: surfaces become lighter at higher elevations in dark mode
4. CSS Cascade Layers enable clean organization: `elements` → `modifiers` → `states` pattern for each component

**Primary recommendation:** Extract existing button, card, badge, modal, and form styles from `_design-tokens.css` into individual component files within `@layer components`, using CSS custom properties for theme-aware values.

## Standard Stack

### Core (Already in Place)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bootstrap | 5.3.3 | Base component framework | Native dark mode via `data-bs-theme`, CSS variable-driven theming |
| CSS Cascade Layers | Native | Specificity management | 96%+ browser support, eliminates !important battles |
| CSS Custom Properties | Native | Theme tokens | Runtime theming, no build step required |

### Supporting Patterns
| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| `:where()` selector | Zero specificity states | Hover, focus states that need easy override |
| `:is()` selector | Intentional specificity | Modifier classes that must override defaults |
| `color-scheme` property | Native form theming | Input, select, checkbox native styling |

### No Additional Libraries Needed
The existing stack is complete. Adding UI libraries (Tailwind, etc.) would conflict with the Bootstrap-based system.

## Architecture Patterns

### Recommended Project Structure
```
app/static/css/
├── main.css                    # Entry point (exists)
├── layers/_layer-order.css     # Documentation (exists)
├── tokens/_design-tokens.css   # Design tokens (exists - needs refactoring)
├── base/                       # Bootstrap overrides (exists)
├── components/                 # NEW: Component library
│   ├── _buttons.css           # Button variants, sizes, states
│   ├── _cards.css             # Card variants, hover effects
│   ├── _badges.css            # Badge colors, outline variants
│   ├── _modals.css            # Modal sizes, theme colors
│   └── _forms.css             # Input states, validation, labels
├── modules/                    # Feature-specific (Phase 5+)
├── utilities/                  # Utility classes (exists)
└── legacy/                     # Migration overrides (exists)
```

### Pattern 1: Component Structure with Nested Layers
**What:** Each component file uses nested layers for elements, modifiers, and states
**When to use:** All component CSS files
**Example:**
```css
/* Source: CSS-Tricks - Organizing Design System Component Patterns with CSS Cascade Layers */
@layer components {
  @layer elements, modifiers, states;

  @layer elements {
    .btn {
      /* Base styles using CSS custom properties */
      --_btn-bg: var(--bg-button);
      --_btn-color: var(--text);
      --_btn-border: var(--border);

      background: var(--_btn-bg);
      color: var(--_btn-color);
      border: 1px solid var(--_btn-border);
    }
  }

  @layer modifiers {
    .btn-primary {
      --_btn-bg: var(--amber-55);
      --_btn-color: hsl(0 0% 10%);
      --_btn-border: transparent;
    }
  }

  @layer states {
    .btn:where(:hover) {
      filter: brightness(1.1);
    }
    .btn:where(:focus-visible) {
      outline: 2px solid var(--amber-55);
      outline-offset: 2px;
    }
  }
}
```

### Pattern 2: Elevation System (3 Levels)
**What:** Surface colors that create visual hierarchy through brightness
**When to use:** Cards, modals, dropdowns, tooltips
**Example:**
```css
/* Based on Material Design dark theme principles */
/* Source: Material Design 3 - Elevation */

/* Level 1: Background (page level) */
--bg-background: hsl(0 0% 0%);      /* Dark: #000000 */
--bg-background: hsl(0 0% 95%);     /* Light: #f5f5f5 */

/* Level 2: Surface (cards, containers) */
--bg-surface: hsl(0 0% 5%);         /* Dark: slightly lighter */
--bg-surface: hsl(0 0% 98%);        /* Light: slightly lighter still */

/* Level 3: Elevated (modals, dropdowns, tooltips) */
--bg-elevated: hsl(0 0% 10%);       /* Dark: even lighter */
--bg-elevated: hsl(0 0% 100%);      /* Light: pure white */
```

### Pattern 3: Theme-Aware Badge Colors
**What:** Badge colors that automatically adjust for WCAG contrast
**When to use:** All semantic badges (success, warning, danger, info)
**Example:**
```css
/* Filled badges with WCAG-compliant contrast */
.badge-success {
  --_badge-bg: hsl(145 65% 40%);
  --_badge-color: hsl(0 0% 100%);
  background: var(--_badge-bg);
  color: var(--_badge-color);
}

/* Light mode adjustment for better contrast */
[data-bs-theme="light"] .badge-success {
  --_badge-bg: hsl(145 65% 35%);  /* Slightly darker */
}

/* Outline variant */
.badge-outline-success {
  background: transparent;
  color: var(--semantic-success);
  border: 1px solid currentColor;
}
```

### Anti-Patterns to Avoid
- **Hardcoded colors:** Never use hex values directly; always use CSS custom properties
- **!important overuse:** The layer system eliminates the need for !important; if you need it, the layer order is wrong
- **Specificity wars:** Use `:where()` for states that should be overridable
- **Duplicate styles:** Current `_design-tokens.css` has component styles that belong in `@layer components`

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Button variants | Custom button classes | Bootstrap's `btn-*` classes + custom properties | Bootstrap handles accessibility, states, accessibility |
| Focus rings | Custom outline styles | `:focus-visible` + `--bs-focus-ring-*` | Native behavior, keyboard vs mouse detection |
| Form validation | Custom error classes | Bootstrap's `is-valid`/`is-invalid` + custom colors | Built-in accessibility, icon support |
| Modal sizes | Custom width classes | Bootstrap's `modal-sm`/`modal-lg`/`modal-xl` | Responsive breakpoints handled |
| Color contrast | Manual calculation | Bootstrap's `text-bg-*` utilities | Auto-contrasting text based on background |

**Key insight:** Bootstrap 5.3 provides CSS variable-based customization for all components. Override the variables, don't recreate the components.

## Common Pitfalls

### Pitfall 1: Breaking Bootstrap's Dark Mode
**What goes wrong:** Hardcoding colors in component CSS overrides Bootstrap's theme switching
**Why it happens:** Developers use hex colors instead of CSS custom properties
**How to avoid:** Always reference `var(--bs-*)` or custom theme tokens (`var(--bg)`, `var(--text)`)
**Warning signs:** Components look correct in one theme but wrong in the other

### Pitfall 2: Badge Contrast Failures
**What goes wrong:** White text on light backgrounds becomes unreadable in light mode
**Why it happens:** Using same badge colors for both themes
**How to avoid:** Define separate badge colors per theme, verify 4.5:1 contrast ratio
**Warning signs:** Squinting to read badge text, accessibility audit failures

### Pitfall 3: Elevation Not Visible in Dark Mode
**What goes wrong:** Cards and modals blend into background, no visual hierarchy
**Why it happens:** Using shadows alone for elevation (shadows invisible on dark backgrounds)
**How to avoid:** Implement Material Design elevation: surfaces get LIGHTER at higher elevations in dark mode
**Warning signs:** Flat-looking interface, difficulty distinguishing layers

### Pitfall 4: Focus States Not Visible
**What goes wrong:** Keyboard users can't see which element is focused
**Why it happens:** Focus outlines blend with component colors in one theme
**How to avoid:** Use high-contrast focus rings (amber/yellow works well against dark AND light)
**Warning signs:** Unable to navigate with Tab key, accessibility violations

### Pitfall 5: !important Proliferation
**What goes wrong:** Adding !important to override previous !important creates unmaintainable CSS
**Why it happens:** Not using CSS layers correctly, wrong layer order
**How to avoid:** Layer order should handle precedence; `components` > `base` by definition
**Warning signs:** More than 5 !important declarations in a component file

## Code Examples

### Example 1: Complete Button Component
```css
/* Source: Bootstrap 5.3 Docs + CSS-Tricks Cascade Layers */
@layer components {
  /* Button base using CSS custom properties */
  .btn {
    --_btn-padding-y: 0.375rem;
    --_btn-padding-x: 0.75rem;
    --_btn-font-size: 1rem;
    --_btn-bg: var(--bg-button);
    --_btn-color: var(--text);
    --_btn-border-color: var(--border);
    --_btn-border-radius: var(--radius-md);

    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: var(--_btn-padding-y) var(--_btn-padding-x);
    font-size: var(--_btn-font-size);
    font-weight: 600;
    background: var(--_btn-bg);
    color: var(--_btn-color);
    border: 1px solid var(--_btn-border-color);
    border-radius: var(--_btn-border-radius);
    transition: all 0.15s ease;
    cursor: pointer;
  }

  /* Sizes */
  .btn-sm {
    --_btn-padding-y: 0.25rem;
    --_btn-padding-x: 0.5rem;
    --_btn-font-size: 0.875rem;
  }

  .btn-lg {
    --_btn-padding-y: 0.5rem;
    --_btn-padding-x: 1rem;
    --_btn-font-size: 1.125rem;
  }

  /* Primary variant */
  .btn-primary {
    --_btn-bg: var(--amber-55);
    --_btn-color: hsl(0 0% 10%);
    --_btn-border-color: transparent;
  }

  /* States using :where() for easy override */
  .btn:where(:hover:not(:disabled)) {
    filter: brightness(1.1);
  }

  .btn:where(:focus-visible) {
    outline: 2px solid var(--amber-55);
    outline-offset: 2px;
  }

  .btn:where(:disabled) {
    opacity: 0.65;
    cursor: not-allowed;
  }
}
```

### Example 2: Card with Elevation and Semantic Variants
```css
@layer components {
  .card {
    --_card-bg: var(--bg);  /* Surface level */
    --_card-border: var(--border);
    --_card-radius: var(--radius-lg);
    --_card-shadow: var(--shadow);

    background: var(--_card-bg);
    border: 1px solid var(--_card-border);
    border-radius: var(--_card-radius);
    box-shadow: var(--_card-shadow);
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  /* Hover effect */
  .card:where(:hover) {
    border-color: var(--amber-50);
    box-shadow: 0 0 6px 1px hsla(50 100% 55% / 0.4);
  }

  /* Semantic variants - border accent */
  .card-success {
    border-left: 3px solid var(--semantic-success);
  }

  .card-warning {
    border-left: 3px solid var(--amber-50);
  }

  .card-danger {
    border-left: 3px solid var(--semantic-danger);
  }

  /* Card structure */
  .card-header {
    padding: 1rem;
    border-bottom: 1px solid var(--_card-border);
    background: transparent;
  }

  .card-body {
    padding: 1rem;
    color: var(--text);
  }

  .card-footer {
    padding: 1rem;
    border-top: 1px solid var(--_card-border);
    background: transparent;
  }
}
```

### Example 3: Form Input States
```css
@layer components {
  .form-control,
  .form-select {
    --_input-bg: var(--bg-light);
    --_input-border: var(--border);
    --_input-color: var(--text);
    --_input-focus-border: var(--amber-50);
    --_input-focus-shadow: 0 0 6px 1px hsla(50 100% 55% / 0.6);

    background: var(--_input-bg);
    border: 1px solid var(--_input-border);
    color: var(--_input-color);
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  /* Focus state */
  .form-control:where(:focus),
  .form-select:where(:focus) {
    border-color: var(--_input-focus-border);
    box-shadow: var(--_input-focus-shadow);
    outline: none;
  }

  /* Validation states */
  .form-control.is-valid,
  .form-select.is-valid {
    --_input-border: var(--semantic-success);
    --_input-focus-shadow: 0 0 6px 1px hsla(145 65% 40% / 0.4);
  }

  .form-control.is-invalid,
  .form-select.is-invalid {
    --_input-border: var(--semantic-danger);
    --_input-focus-shadow: 0 0 6px 1px hsla(0 70% 50% / 0.4);
  }

  /* Disabled state */
  .form-control:where(:disabled),
  .form-select:where(:disabled) {
    opacity: 0.65;
    cursor: not-allowed;
  }

  /* Required field indicator */
  .form-label.required::after {
    content: " *";
    color: var(--semantic-danger);
  }
}
```

### Example 4: Modal with Elevation
```css
@layer components {
  .modal-content {
    --_modal-bg: var(--bg-light);  /* Elevated level */
    --_modal-border: var(--border);
    --_modal-shadow: 0 4px 8px hsla(0 0% 0% / 0.15), 0 8px 16px hsla(0 0% 0% / 0.2);

    background: var(--_modal-bg);
    border: 1px solid var(--_modal-border);
    box-shadow: var(--_modal-shadow);
  }

  .modal-header {
    border-bottom: 1px solid var(--_modal-border);
    color: var(--text);
  }

  .modal-body {
    color: var(--text);
  }

  .modal-footer {
    border-top: 1px solid var(--_modal-border);
  }

  /* Sizes (Bootstrap handles width) */
  /* .modal-sm: 300px, .modal-lg: 800px, .modal-xl: 1140px */
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `!important` overrides | CSS Cascade Layers | 2022 (96%+ support) | Clean specificity management |
| Sass color functions | Native CSS `color-mix()` | 2023 | No build step for color manipulation |
| Media queries for responsive | Container queries | 2023 | Component-scoped responsive design |
| Viewport-based breakpoints | `@container` queries | 2023 | Components adapt to container, not viewport |
| Manual dark mode toggle | `color-scheme` + `prefers-color-scheme` | 2021 | Native system preference detection |

**Deprecated/Outdated:**
- Using `@import` without `layer()` - now creates unlayered CSS with highest priority
- Bootstrap 4.x color utilities - replaced by `text-bg-*` in Bootstrap 5.2+
- Manual focus styles - use `:focus-visible` for keyboard-only focus indication

## Open Questions

1. **Existing Component Styles Migration**
   - What we know: `_design-tokens.css` contains 700+ lines including button, card, badge, modal styles
   - What's unclear: Should we migrate ALL component styles to `_buttons.css`, `_cards.css`, etc., or create new files and deprecate the token versions?
   - Recommendation: Extract to component files, leave token file with only design tokens (colors, spacing, typography)

2. **Outline Badge Implementation**
   - What we know: User wants `badge-outline-*` variants (e.g., `badge-outline-success`)
   - What's unclear: Should outlined badges have the same background in both themes, or adapt?
   - Recommendation: Transparent background with colored border and text; text color adapts per theme for contrast

## Sources

### Primary (HIGH confidence)
- [Context7 /websites/getbootstrap_5_3](https://getbootstrap.com/docs/5.3/) - Bootstrap 5.3 CSS variables, color modes, buttons, cards, modals, forms, badges
- [CSS-Tricks: Organizing Design System Component Patterns with CSS Cascade Layers](https://css-tricks.com/organizing-design-system-component-patterns-with-css-cascade-layers/) - Layer organization pattern
- [Modern CSS for Dynamic Component-Based Architecture](https://moderncss.dev/modern-css-for-dynamic-component-based-architecture/) - Custom property API patterns

### Secondary (MEDIUM confidence)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - WCAG contrast requirements (4.5:1 for text)
- [Material Design Dark Theme Documentation](https://github.com/material-components/material-components-android/blob/master/docs/theming/Dark.md) - Elevation overlay concept
- [Material Design 3 Elevation](https://m3.material.io/styles/elevation/applying-elevation) - Surface hierarchy principles

### Tertiary (LOW confidence)
- [The Modern CSS Toolkit 2026](https://www.nickpaolini.com/blog/modern-css-toolkit-2026) - General CSS best practices (WebSearch only)
- [Atlassian Design System Elevation](https://atlassian.design/foundations/elevation/) - Alternative elevation approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Bootstrap 5.3 docs and MDN confirm all capabilities
- Architecture: HIGH - CSS-Tricks article verified with official CSS Layer spec
- Pitfalls: MEDIUM - Based on codebase analysis and common dark mode issues
- Elevation system: MEDIUM - Material Design principles well-documented but exact values need testing

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (stable domain, 30 days)
