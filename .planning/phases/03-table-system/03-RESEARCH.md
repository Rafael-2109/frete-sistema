# Phase 3: Table System - Research

**Researched:** 2026-01-27
**Domain:** CSS Responsive Tables with Sticky Headers and Theme-Adaptive Hover States
**Confidence:** HIGH

## Summary

This phase focuses on implementing a robust table system that works correctly on both mobile and desktop devices with proper theming. The research analyzed existing table implementations in the codebase (11+ CSS files with table styles) and verified best practices against Bootstrap 5.3 documentation and CSS specifications.

Key findings:
1. The project already has extensive table patterns scattered across module-specific CSS files (carteira-simples.css, extrato.css, custeio.css, etc.) that need consolidation into a centralized component
2. Bootstrap 5.3's `.table-responsive` wrapper provides the foundation for horizontal scroll on mobile
3. CSS `position: sticky` must be applied to `<th>` elements (not `<thead>` or `<tr>`) due to CSS 2.1 spec limitations
4. The existing hover state implementations are inconsistent across modules and some break in dark mode
5. Action buttons in table cells require `min-width` constraints to prevent clipping on mobile

**Primary recommendation:** Create `_tables.css` in `@layer components` that consolidates scattered table styles, implements consistent sticky headers, theme-adaptive hover states, and ensures action buttons remain accessible on mobile devices.

## Standard Stack

### Core (Already in Place)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bootstrap | 5.3.3 | `.table-responsive` wrapper, table variants | Native horizontal scroll, CSS variable-driven theming |
| CSS Cascade Layers | Native | Specificity management via `@layer components` | 96%+ browser support, eliminates !important battles |
| CSS Custom Properties | Native | Theme tokens (`--bg-light`, `--text`, `--border`) | Runtime theming without build step |

### Supporting CSS Properties
| Property | Purpose | Browser Support |
|----------|---------|-----------------|
| `position: sticky` | Fixed headers during vertical scroll | 95%+ (all modern browsers) |
| `overflow-x: auto` | Horizontal scroll on narrow viewports | 99%+ |
| `:where()` selector | Zero specificity for overridable hover states | 94%+ |
| `color-scheme` | Native form/input theming | 95%+ |

### No Additional Libraries Needed
The existing Bootstrap 5.3.3 + CSS Layers stack is complete for this phase.

## Architecture Patterns

### Recommended File Structure
```
app/static/css/
├── main.css                    # Entry point (add _tables.css import)
├── components/
│   ├── _buttons.css           # Exists
│   ├── _cards.css             # Exists
│   ├── _badges.css            # Exists
│   ├── _modals.css            # Exists
│   ├── _forms.css             # Exists
│   └── _tables.css            # NEW: Consolidated table component
└── modules/                    # Keep module-specific overrides minimal
```

### Pattern 1: Sticky Header Implementation
**What:** Apply `position: sticky` to `<th>` elements with proper z-index and background
**When to use:** All data tables with more than ~10 rows
**Why:** `<thead>` and `<tr>` don't support sticky positioning per CSS 2.1 spec

```css
/* Source: CSS-Tricks - Position Sticky and Table Headers */
@layer components {
  .table > thead th {
    position: sticky;
    top: 0;
    background: var(--bg-light);  /* Must have solid background */
    z-index: 10;                   /* Above tbody content */
  }
}
```

**Critical insight:** The `<th>` MUST have a solid background color (not transparent), otherwise content will show through when scrolling.

### Pattern 2: Horizontal Scroll Container
**What:** Wrap table in `.table-responsive` for horizontal scroll on mobile
**When to use:** All tables that may exceed viewport width on mobile (< 768px)

```html
<!-- Bootstrap's recommended structure -->
<div class="table-responsive">
  <table class="table">
    <thead>...</thead>
    <tbody>...</tbody>
  </table>
</div>
```

```css
/* Enhancement: Visible scrollbar for scroll indication */
@layer components {
  .table-responsive {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;  /* Smooth scroll on iOS */
  }

  /* Scrollbar styling for visibility */
  .table-responsive::-webkit-scrollbar {
    height: 6px;
  }
  .table-responsive::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 3px;
  }
}
```

### Pattern 3: Theme-Adaptive Hover States
**What:** Hover colors that provide visible feedback in both dark and light modes
**When to use:** All interactive table rows

```css
/* Source: Prior decisions from Phase 2 */
@layer components {
  /* Use CSS custom property API for easy theme adaptation */
  .table > tbody > tr {
    --_table-hover-bg: hsla(0 0% 50% / 0.05);
    transition: background-color 0.15s ease;
  }

  /* Low specificity with :where() for easy override */
  .table > tbody > tr:where(:hover) {
    background-color: var(--_table-hover-bg);
  }

  /* Theme-specific hover intensities */
  [data-bs-theme="dark"] .table > tbody > tr {
    --_table-hover-bg: hsla(0 0% 100% / 0.05);  /* Lighter overlay on dark */
  }

  [data-bs-theme="light"] .table > tbody > tr {
    --_table-hover-bg: hsla(0 0% 0% / 0.03);    /* Darker overlay on light */
  }
}
```

### Pattern 4: Action Button Cell Protection
**What:** Ensure action buttons in table cells are never clipped on mobile
**When to use:** Any table with action buttons (edit, delete, view, etc.)

```css
@layer components {
  /* Action column that never shrinks below button requirements */
  .table td.table-actions,
  .table th.table-actions {
    min-width: 100px;      /* Minimum space for 2 small buttons */
    white-space: nowrap;   /* Prevent button text wrapping */
  }

  /* Action buttons inside tables */
  .table .btn-table-action {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
  }
}
```

### Anti-Patterns to Avoid

1. **Applying sticky to `<thead>` or `<tr>`:** Doesn't work per CSS 2.1 spec. Always target `<th>`.

2. **Transparent header backgrounds:** Content will show through during scroll. Always use solid color.

3. **Hardcoded hover colors:** Use CSS custom properties that adapt to theme.

4. **!important on table styles:** The layer system should handle precedence.

5. **Missing overflow container:** Without `.table-responsive`, tables will clip or break layout on mobile.

6. **Inconsistent z-index:** When combining sticky header + sticky first column, use proper z-index hierarchy:
   - `tbody td`: base (no z-index)
   - `tbody td:first-child` (sticky column): z-index: 5
   - `thead th`: z-index: 10
   - `thead th:first-child` (corner): z-index: 11

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Horizontal scroll on mobile | Custom scroll implementation | Bootstrap's `.table-responsive` | Handles breakpoints, touch scrolling, accessibility |
| Table hover states | Custom hover classes | Bootstrap's `.table-hover` + custom properties | Built-in, consistent behavior |
| Table striped rows | Manual alternating colors | Bootstrap's `.table-striped` + custom properties | Handles edge cases, accessibility |
| Responsive breakpoints | Custom media queries | Bootstrap's `.table-responsive-{sm\|md\|lg}` | Consistent with framework breakpoints |
| Row status colors | Hardcoded background colors | Bootstrap's `.table-success`, `.table-warning` + custom properties | Theme-aware, consistent palette |

**Key insight:** Bootstrap 5.3 provides CSS variable-based customization for all table features. Override the `--bs-table-*` variables instead of recreating the components.

## Common Pitfalls

### Pitfall 1: Sticky Header Not Working
**What goes wrong:** `position: sticky` appears to have no effect
**Why it happens:**
- Applied to `<thead>` or `<tr>` instead of `<th>`
- Parent container has `overflow: hidden` (breaks sticky context)
- Missing explicit `top: 0` value
**How to avoid:**
- Always apply sticky to `<th>` elements
- Ensure `.table-responsive` uses `overflow: auto`, not `overflow: hidden`
- Explicitly set `top: 0` (or the offset from sticky navbar)
**Warning signs:** Header scrolls with content instead of staying fixed

### Pitfall 2: Content Showing Through Sticky Header
**What goes wrong:** When scrolling, table content is visible behind the header
**Why it happens:** Header background is transparent or semi-transparent
**How to avoid:** Use solid background color on `<th>` elements: `background: var(--bg-light)`
**Warning signs:** "Ghost" text appearing behind header during scroll

### Pitfall 3: Hover State Invisible in One Theme
**What goes wrong:** Hover effect works in dark mode but not visible in light mode (or vice versa)
**Why it happens:** Hardcoded hover color that only contrasts against one background
**How to avoid:** Use theme-aware hover colors with CSS custom properties
**Warning signs:** Squinting to see if row is being hovered

### Pitfall 4: Action Buttons Clipped on Mobile
**What goes wrong:** Edit/Delete buttons are cut off or unreachable on small screens
**Why it happens:**
- No `min-width` on action column
- Table width set to 100% forces columns to shrink
- No horizontal scroll container
**How to avoid:**
- Wrap in `.table-responsive` for horizontal scroll
- Set `min-width` on action columns
- Use `white-space: nowrap` on button cells
**Warning signs:** Users report "can't click delete button on phone"

### Pitfall 5: Z-Index Conflicts with Sticky Headers
**What goes wrong:** Sticky header appears behind dropdowns or other overlays
**Why it happens:** Z-index not coordinated across components
**How to avoid:** Use consistent z-index scale:
- Table sticky header: z-index: 10
- Dropdowns: z-index: 1000 (Bootstrap default)
- Modals: z-index: 1050+ (Bootstrap default)
**Warning signs:** Dropdown menus appearing behind table header

### Pitfall 6: Scattered Table Styles
**What goes wrong:** Each module has its own table styling, causing inconsistency
**Why it happens:** Organic growth without centralized component
**Current state in codebase:** 11+ files with table styles found:
- `_design-tokens.css` (tokens layer - should only have tokens)
- `_bootstrap-overrides.css` (base layer)
- `contas_receber.css`
- `extrato.css`
- `custeio.css`
- `carteira-simples.css`
- `agrupados.css`
- `workspace-montagem.css`
- `margem.css`
- `macro-projecao.css`
- `drilldown.css`
**How to avoid:** Create centralized `_tables.css` component, migrate common patterns
**Warning signs:** "It looks different on this page" reports

## Code Examples

### Example 1: Complete Table Component
```css
/* Source: Bootstrap 5.3 Docs + CSS-Tricks Sticky Headers */
@layer components {
  /* ═══════════════════════════════════════════════════════════════════════════
     TABLE BASE
     ═══════════════════════════════════════════════════════════════════════════ */

  .table {
    --_table-bg: var(--bg-light);
    --_table-color: var(--text);
    --_table-border-color: var(--border);
    --_table-hover-bg: hsla(0 0% 50% / 0.05);

    background-color: var(--_table-bg);
    color: var(--_table-color);
    border-color: var(--_table-border-color);
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     STICKY HEADER
     ═══════════════════════════════════════════════════════════════════════════ */

  .table > thead th {
    position: sticky;
    top: 0;
    background: var(--bg-light);
    color: var(--text);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border-bottom: 2px solid var(--border);
    z-index: 10;
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     HOVER STATES (theme-adaptive)
     ═══════════════════════════════════════════════════════════════════════════ */

  .table > tbody > tr {
    transition: background-color 0.15s ease;
  }

  .table > tbody > tr:where(:hover) {
    background-color: var(--_table-hover-bg);
  }

  /* Dark mode: lighter overlay */
  [data-bs-theme="dark"] .table {
    --_table-hover-bg: hsla(0 0% 100% / 0.05);
  }

  /* Light mode: darker overlay */
  [data-bs-theme="light"] .table {
    --_table-hover-bg: hsla(0 0% 0% / 0.04);
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     RESPONSIVE CONTAINER
     ═══════════════════════════════════════════════════════════════════════════ */

  .table-responsive {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  /* Styled scrollbar for visibility */
  .table-responsive::-webkit-scrollbar {
    height: 6px;
  }

  .table-responsive::-webkit-scrollbar-track {
    background: transparent;
  }

  .table-responsive::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 3px;
  }

  .table-responsive::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     ACTION COLUMN
     ═══════════════════════════════════════════════════════════════════════════ */

  .table td.table-actions,
  .table th.table-actions {
    min-width: 100px;
    white-space: nowrap;
    text-align: right;
  }

  .table .btn-table-action {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    margin-left: 0.25rem;
  }

  .table .btn-table-action:first-child {
    margin-left: 0;
  }
}
```

### Example 2: Sticky Header + Sticky First Column
```css
/* Source: CSS-Tricks - A table with both sticky header and sticky first column */
@layer components {
  /* When you need multi-directional sticky */
  .table-sticky-both > thead th {
    position: sticky;
    top: 0;
    background: var(--bg-light);
    z-index: 10;
  }

  .table-sticky-both > thead th:first-child {
    left: 0;
    z-index: 11;  /* Corner cell highest */
  }

  .table-sticky-both > tbody td:first-child {
    position: sticky;
    left: 0;
    background: var(--bg-light);
    z-index: 5;
  }

  /* Border to indicate frozen column */
  .table-sticky-both > tbody td:first-child {
    border-right: 2px solid var(--border);
  }
}
```

### Example 3: Table Row Status Colors (Theme-Aware)
```css
/* Source: Existing patterns in _bootstrap-overrides.css */
@layer components {
  /* Reset Bootstrap table vars for custom control */
  .table-success,
  .table-warning,
  .table-primary,
  .table-light {
    --bs-table-bg: transparent;
    --bs-table-accent-bg: transparent;
    color: var(--text);
  }

  /* Success - subtle green tint */
  .table-success {
    --_row-bg: hsla(145 50% 35% / 0.15);
    --_row-hover-bg: hsla(145 50% 35% / 0.28);
    background-color: var(--_row-bg);
  }

  .table-success:hover {
    background-color: var(--_row-hover-bg);
  }

  /* Warning - subtle amber tint */
  .table-warning {
    --_row-bg: hsla(50 100% 50% / 0.08);
    --_row-hover-bg: hsla(50 100% 50% / 0.15);
    background-color: var(--_row-bg);
  }

  .table-warning:hover {
    background-color: var(--_row-hover-bg);
  }

  /* Primary - subtle amber tint (for EMBARCADO status) */
  .table-primary {
    --_row-bg: hsla(45 80% 50% / 0.06);
    --_row-hover-bg: hsla(45 80% 50% / 0.12);
    background-color: var(--_row-bg);
  }

  .table-primary:hover {
    background-color: var(--_row-hover-bg);
  }
}
```

### Example 4: Mobile-Friendly Action Buttons
```css
/* Ensure buttons are always accessible on mobile */
@layer components {
  /* Minimum touch target size per WCAG 2.5.5 */
  @media (max-width: 767.98px) {
    .table .btn-table-action {
      min-width: 44px;
      min-height: 44px;
      padding: 0.5rem;
    }

    /* Stack buttons vertically on very narrow screens */
    .table td.table-actions {
      min-width: 50px;
    }

    .table td.table-actions .btn-group {
      flex-direction: column;
      gap: 0.25rem;
    }
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sticky on `<thead>` | Sticky on `<th>` cells | Always (CSS spec) | Only reliable method |
| `!important` overrides | CSS Cascade Layers | 2022 (96%+ support) | Clean specificity |
| Hardcoded hover colors | CSS custom properties | 2023 | Theme-aware |
| Horizontal scroll with JS | CSS `overflow-x: auto` | Always | Native, accessible |
| Fixed column widths | Flexible with `min-width` | 2020+ | Responsive-first |

**Deprecated/Outdated:**
- Using `position: fixed` for table headers (breaks document flow, not recommended)
- JavaScript-based horizontal scroll detection (use CSS scroll indicators instead)
- Applying sticky to `<thead>` or `<tr>` (never worked, won't work)

## Open Questions

1. **Navbar Offset for Sticky Headers**
   - What we know: The navbar uses `position: sticky` at top: 0
   - What's unclear: Tables in the main content area may need `top: [navbar-height]` to avoid overlap
   - Recommendation: Check navbar height (~60px based on existing CSS) and adjust table header `top` value accordingly for pages where table is directly below navbar

2. **Module-Specific Table Overrides**
   - What we know: 11+ files have table styles; some are truly module-specific (e.g., `macro-projecao.css` has multi-row headers with color groups)
   - What's unclear: Which styles should migrate to component vs. remain in modules?
   - Recommendation: Migrate common patterns (sticky header, hover, responsive) to `_tables.css`; keep visual customizations (color groups, special layouts) in modules

3. **Existing !important Usage**
   - What we know: `_bootstrap-overrides.css` uses `!important` on some table styles
   - What's unclear: Will removing them break existing pages?
   - Recommendation: Test on key pages (carteira, financeiro, custeio) after migration

## Sources

### Primary (HIGH confidence)
- [Context7 /twbs/bootstrap](https://github.com/twbs/bootstrap) - Bootstrap 5.3 table documentation, responsive tables, CSS variables
- [CSS-Tricks: Position Sticky and Table Headers](https://css-tricks.com/position-sticky-and-table-headers/) - Authoritative guide on sticky header implementation
- [CSS-Tricks: A table with both sticky header and sticky first column](https://css-tricks.com/a-table-with-both-a-sticky-header-and-a-sticky-first-column/) - Multi-directional sticky patterns

### Secondary (MEDIUM confidence)
- [Smashing Magazine: Accessible Front-End Patterns For Responsive Tables](https://www.smashingmagazine.com/2022/12/accessible-front-end-patterns-responsive-tables-part1/) - Accessibility patterns
- [Adrian Roselli: Fixed Table Headers](https://adrianroselli.com/2020/01/fixed-table-headers.html) - Accessibility considerations
- [MDN: table-layout](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/table-layout) - CSS specification reference
- [Medium: Multi-Directional Sticky CSS](https://medium.com/@ashutoshgautam10b11/multi-directional-sticky-css-and-horizontal-scroll-in-tables-41fc25c3ce8b) - 2026 patterns

### Tertiary (LOW confidence)
- [LogRocket: Creating responsive data tables with CSS](https://blog.logrocket.com/creating-responsive-data-tables-css/) - General patterns
- [Accessibility Developer Guide: Responsive tables](https://www.accessibility-developer-guide.com/examples/tables/responsive/) - ARIA patterns for stacked layouts

## Existing Codebase Patterns

The following files contain table styling that should be analyzed for consolidation:

| File | Pattern | Migrate to Component? |
|------|---------|----------------------|
| `tokens/_design-tokens.css` | Basic `.table` styling | YES - move to components |
| `base/_bootstrap-overrides.css` | Table status colors, hover | YES - partially |
| `modules/carteira/carteira-simples.css` | Sticky header, responsive | Reference pattern |
| `modules/financeiro/extrato.css` | Sticky header, hover effects | Reference pattern |
| `modules/custeio/custeio.css` | Sticky column (`.table-sticky`) | Keep in module |
| `modules/manufatura/macro-projecao.css` | Multi-row header with color groups | Keep in module |
| `modules/carteira/agrupados.css` | Table status overrides | Consolidate with component |
| `contas_receber.css` | Custom `.table-contas` styling | Keep for now, refactor later |

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Bootstrap 5.3 docs and codebase analysis confirm approach
- Architecture patterns: HIGH - CSS-Tricks and MDN verify sticky header behavior
- Pitfalls: HIGH - Based on codebase analysis and verified CSS specifications
- Mobile button accessibility: MEDIUM - Best practices verified, specific touch target sizes from WCAG

**Research date:** 2026-01-27
**Valid until:** 2026-02-27 (stable domain, 30 days)
