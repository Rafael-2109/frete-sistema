# Phase 1: Layer Infrastructure - Research

**Researched:** 2026-01-26
**Domain:** CSS Cascade Layers, Bootstrap 5 Integration, Design Token Architecture
**Confidence:** HIGH

## Summary

Phase 1 establishes cascade control via CSS Layers (`@layer`) to eliminate specificity wars before any template migration work begins. The current codebase has **591 `!important` declarations across 14 CSS files** and **multiple Bootstrap versions** (5.1.3, 5.3.0, 5.3.2) causing inconsistent behavior.

The project already has a solid foundation with `_design-tokens.css` (711 lines, HSL-based) and `bootstrap-overrides.css` that imports it via `@import`. The infrastructure work involves:
1. Creating a `main.css` entry point with explicit `@layer` order declaration
2. Wrapping existing files in appropriate layers
3. Standardizing Bootstrap to 5.3.3 across all templates
4. Establishing the folder structure for subsequent phases

**Primary recommendation:** Create `main.css` with 7-layer cascade order (`reset, tokens, base, components, modules, utilities, overrides`), wrap `_design-tokens.css` in `@layer tokens`, wrap `bootstrap-overrides.css` in `@layer base`, and standardize all Bootstrap references to 5.3.3.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| CSS Cascade Layers | Native CSS | Specificity control without `!important` | 96%+ browser support since March 2022, W3C standard |
| Bootstrap | 5.3.3 | UI framework with CSS variable hooks | Latest stable, native `data-bs-theme` dark mode support |
| CSS Custom Properties | Level 1 | Design token implementation | 97%+ browser support, already in use in project |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Font Awesome | 6.4.0 | Icons | Already loaded in base.html |
| Google Fonts | - | Typography (IBM Plex Sans, Space Grotesk, JetBrains Mono) | Already imported in bootstrap-overrides.css |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@layer` (native CSS) | Sass `@use` | `@layer` is native, no build tool needed |
| Bootstrap 5.3.3 | Tailwind CSS | Bootstrap already deeply integrated, migration cost too high |

**Installation:**
```html
<!-- Bootstrap 5.3.3 (CDN) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
```

## Architecture Patterns

### Recommended CSS File Structure

```
app/static/css/
├── main.css              # Entry point with @layer order declaration
├── layers/
│   └── _layer-order.css  # @layer reset, tokens, base, components, modules, utilities, overrides;
├── tokens/
│   └── _design-tokens.css  # Existing file, wrapped in @layer tokens
├── base/
│   ├── _reset.css          # Optional minimal reset
│   ├── _typography.css     # Typography from bootstrap-overrides.css
│   └── _bootstrap-overrides.css  # Current bootstrap-overrides.css, in @layer base
├── components/
│   ├── _buttons.css        # Phase 2
│   ├── _cards.css          # Phase 2
│   └── ...
├── modules/                # Existing structure preserved
│   ├── carteira/
│   ├── financeiro/
│   ├── manufatura/
│   └── ...
├── utilities/
│   └── _utilities.css      # Existing _utilities.css
└── legacy/                 # Temporary during migration
    └── _inline-overrides.css
```

### Pattern 1: Layer Order Declaration

**What:** Establish cascade priority at the top of main.css
**When to use:** ALWAYS - must be first CSS rule loaded
**Example:**
```css
/* Source: MDN @layer documentation */
/* main.css - Entry point */

/* 1. Establish layer order (lowest to highest priority) */
@layer reset, tokens, base, components, modules, utilities, overrides;

/* 2. Import files into their layers */
@import url('./tokens/_design-tokens.css') layer(tokens);
@import url('./base/_bootstrap-overrides.css') layer(base);
@import url('./utilities/_utilities.css') layer(utilities);

/* Note: @import must precede all other rules except @charset and @layer statements */
```

### Pattern 2: Wrapping Existing CSS in Layers

**What:** Convert existing CSS files to use layer declarations
**When to use:** When migrating existing CSS without restructuring
**Example:**
```css
/* _design-tokens.css - Add layer wrapper */
@layer tokens {
    :root {
        --bg-dark: hsl(0 0% 0%);
        --bg: hsl(0 0% 5%);
        /* ... existing content ... */
    }
}
```

### Pattern 3: Module-specific Layers (Nested)

**What:** Use nested layers for module isolation
**When to use:** Phase 3+ when migrating templates
**Example:**
```css
/* main.css */
@layer modules {
    @layer carteira, financeiro, manufatura;
}

/* modules/carteira/agrupados.css */
@layer modules.carteira {
    .carteira-card { /* ... */ }
}
```

### Anti-Patterns to Avoid

- **Adding more `!important`:** Use layer order instead. Layers solve specificity without `!important`.
- **Mixing `@import` positions:** All `@import` statements must be at the top, after `@layer` declarations.
- **Anonymous layers for shared styles:** Always name layers for maintainability.
- **Loading CSS after main.css:** All CSS should flow through `main.css` entry point.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Specificity control | Complex selector chains | `@layer` | Native browser feature, zero runtime cost |
| Dark mode | Separate stylesheet | `data-bs-theme` + CSS variables | Bootstrap 5.3+ built-in, already working |
| Flash prevention | Custom JS | Inline script in `<head>` | Already exists in base.html (lines 19-27) |
| Theme persistence | Custom storage | `localStorage` + theme-manager.js | Already implemented, works with tab sync |

**Key insight:** The project already has working infrastructure for dark mode and theme persistence. Phase 1 only needs to organize CSS loading, not rebuild theme functionality.

## Common Pitfalls

### Pitfall 1: @import Order Violation

**What goes wrong:** Browser ignores `@import` statements placed after regular rules.
**Why it happens:** CSS spec requires `@import` to precede all other rules except `@charset` and `@layer` statements.
**How to avoid:** In `main.css`, use this order:
1. `@layer` statement declarations (order definition)
2. `@import` statements with `layer()` function
3. Regular CSS rules (if any)

**Warning signs:** Styles not applying, browser dev tools showing ignored `@import`.

### Pitfall 2: Bootstrap Version Mismatch

**What goes wrong:** CSS variable hooks work in some templates but not others.
**Why it happens:** Current codebase has mixed versions:
- `base.html`: Bootstrap 5.3.2
- `mapa_pedidos.html`, `gerenciar_sessao.html`: Bootstrap 5.1.3
- `rastreamento/*.html`, `programacao_linhas_print.html`: Bootstrap 5.3.0

**How to avoid:** Standardize ALL templates to 5.3.3. Search for `bootstrap@5.` and update every occurrence.

**Warning signs:** `data-bs-theme` not working on specific pages, CSS variables undefined.

### Pitfall 3: Inline @import in bootstrap-overrides.css

**What goes wrong:** Current `bootstrap-overrides.css` uses `@import url('./_design-tokens.css')` which loads tokens INSIDE the base layer instead of tokens layer.
**Why it happens:** `@import` within a file inherits that file's layer context.
**How to avoid:** Move all `@import` statements to `main.css` entry point with explicit layer specification.

**Warning signs:** Token specificity lower than expected, tokens not overriding Bootstrap defaults.

### Pitfall 4: Standalone Templates Bypassing main.css

**What goes wrong:** Templates that don't extend `base.html` load Bootstrap directly without design system.
**Why it happens:** These are standalone pages (rastreamento, print templates) with their own `<head>`.

**Standalone templates identified:**
- `app/templates/rastreamento/rastreamento_ativo.html`
- `app/templates/rastreamento/upload_canhoto.html`
- `app/templates/rastreamento/questionario_entrega.html`
- `app/templates/rastreamento/erro.html`
- `app/templates/rastreamento/aceite_lgpd.html`
- `app/templates/rastreamento/confirmacao.html`
- `app/templates/carteira/mapa_pedidos.html`
- `app/templates/portal/sendas/gerenciar_sessao.html`
- `app/templates/manufatura/programacao_linhas_print.html`

**How to avoid:** Create a minimal `main-standalone.css` for these pages, or update them to use base.html.

**Warning signs:** Standalone pages with broken theme, inconsistent styling.

## Code Examples

### Example 1: main.css Entry Point

```css
/* Source: MDN @layer documentation + project requirements */
/**
 * main.css - CSS Entry Point
 *
 * Layer Priority (lowest to highest):
 * 1. reset     - Browser normalization
 * 2. tokens    - Design tokens (colors, spacing, typography)
 * 3. base      - Bootstrap overrides, global defaults
 * 4. components - Reusable UI components (buttons, cards, etc.)
 * 5. modules   - Feature-specific styles (carteira, financeiro, etc.)
 * 6. utilities - Utility classes (spacing, visibility, etc.)
 * 7. overrides - Temporary migration overrides (remove when complete)
 */

@layer reset, tokens, base, components, modules, utilities, overrides;

/* Tokens */
@import url('./tokens/_design-tokens.css') layer(tokens);

/* Base */
@import url('./base/_bootstrap-overrides.css') layer(base);
@import url('./base/_navbar.css') layer(base);

/* Utilities */
@import url('./utilities/_utilities.css') layer(utilities);

/* Module imports happen via {% block extra_css %} in templates */
```

### Example 2: Wrapping _design-tokens.css

```css
/* _design-tokens.css - Add layer wrapper around existing content */
@layer tokens {
    /* All existing content goes here */
    :root {
        /* Accent colors */
        --amber-28: hsl(45 100% 28%);
        --amber-40: hsl(45 100% 40%);
        /* ... rest of file ... */
    }

    [data-bs-theme="dark"],
    [data-theme="dark"] {
        /* Dark mode tokens */
    }

    [data-bs-theme="light"],
    [data-theme="light"] {
        /* Light mode tokens */
    }

    /* ... rest of existing content ... */
}
```

### Example 3: Updated base.html CSS Loading

```html
<head>
  <!-- Bootstrap 5.3.3 (standardized) -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css">

  <!-- Design System Entry Point (replaces individual CSS imports) -->
  <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">

  <!-- Flash prevention script (keep as-is) -->
  <script>
    (function() {
      var saved = localStorage.getItem('nacom-theme');
      var theme = saved || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
      document.documentElement.setAttribute('data-bs-theme', theme);
      document.documentElement.setAttribute('data-theme', theme);
    })();
  </script>

  {% block extra_css %}{% endblock %}
</head>
```

### Example 4: Module CSS with Layer

```css
/* modules/carteira/agrupados.css */
@layer modules {
    /* All existing content wrapped */
    .carteira-container { /* ... */ }
    .carteira-table { /* ... */ }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Specificity wars with `!important` | CSS Cascade Layers | March 2022 | Eliminates need for `!important` |
| Separate dark/light stylesheets | `data-bs-theme` attribute | Bootstrap 5.3.0 (May 2023) | Single stylesheet, CSS variables |
| CSS preprocessors for variables | CSS Custom Properties | 2016+ (97% support) | No build step needed |
| Multiple CSS link tags | Single entry point with @import | Always available | Better cache control, explicit order |

**Deprecated/outdated:**
- Bootstrap 5.1.x: Lacks `data-bs-theme` support, CSS variable hooks incomplete
- `@import` without `layer()`: Loses cascade control benefits

## Open Questions

1. **Standalone templates migration strategy**
   - What we know: 9 templates load Bootstrap directly without base.html
   - What's unclear: Should they use a separate `main-standalone.css` or be converted to extend base.html?
   - Recommendation: Document in Phase 1, defer decision to Phase 3 when migrating those specific templates

2. **Font loading optimization**
   - What we know: Google Fonts loaded via `@import` in bootstrap-overrides.css
   - What's unclear: Should fonts move to main.css or stay in base layer?
   - Recommendation: Keep in base layer for now, font loading is not blocking cascade control

## Sources

### Primary (HIGH confidence)
- **MDN Web Docs @layer** - https://developer.mozilla.org/en-US/docs/Web/CSS/@layer (syntax, layer order, imports, nesting)
- **Codebase analysis** - Direct file reading of base.html, _design-tokens.css, bootstrap-overrides.css, navbar.css, theme-manager.js
- **Bootstrap 5.3 docs** - CSS variables and color modes (via Context7 in prior research)

### Secondary (MEDIUM confidence)
- **Can I Use** - Browser support data for Cascade Layers (96.7%), referenced in SUMMARY.md

### Tertiary (LOW confidence)
- None used for this phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - CSS Cascade Layers is W3C standard with 96%+ browser support, Bootstrap 5.3.3 is latest stable
- Architecture: HIGH - Based on direct codebase analysis, MDN documentation for @layer patterns
- Pitfalls: HIGH - All pitfalls identified from actual codebase issues (Bootstrap versions verified via grep, @import location verified in bootstrap-overrides.css)

**Research date:** 2026-01-26
**Valid until:** 2026-02-26 (30 days - stable CSS features)

---

## Appendix: Current State Inventory

### Bootstrap Versions Found

| Template | Version | Action Required |
|----------|---------|-----------------|
| `base.html` | 5.3.2 | Update to 5.3.3 |
| `carteira/mapa_pedidos.html` | 5.1.3 | Update to 5.3.3 |
| `portal/sendas/gerenciar_sessao.html` | 5.1.3 | Update to 5.3.3 |
| `rastreamento/rastreamento_ativo.html` | 5.3.0 | Update to 5.3.3 |
| `rastreamento/upload_canhoto.html` | 5.3.0 | Update to 5.3.3 |
| `rastreamento/questionario_entrega.html` | 5.3.0 | Update to 5.3.3 |
| `rastreamento/erro.html` | 5.3.0 | Update to 5.3.3 |
| `rastreamento/aceite_lgpd.html` | 5.3.0 | Update to 5.3.3 |
| `rastreamento/confirmacao.html` | 5.3.0 | Update to 5.3.3 |
| `manufatura/programacao_linhas_print.html` | 5.3.0 | Update to 5.3.3 |

### Current CSS Loading Order in base.html

```
1. Bootstrap 5.3.2 (CDN)
2. Font Awesome 6.4.0 (CDN)
3. Toastr CSS (CDN)
4. bootstrap-overrides.css (local) - contains @import for _design-tokens.css
5. navbar.css (local)
6. financeiro/premium-effects.css (local)
7. style.css (local)
8. {% block extra_css %} (per-page)
```

### !important Count by File

| File | Count | Priority |
|------|-------|----------|
| `modules/carteira/agrupados.css` | 209 | High (Phase 3) |
| `_design-tokens.css` | 89 | High (Phase 1) |
| `bootstrap-overrides.css` | 83 | High (Phase 1) |
| `contas_receber.css` | 69 | Medium (Phase 4) |
| `_utilities.css` | 36 | Medium (Phase 1) |
| `modules/carteira/carteira-simples.css` | 33 | Medium (Phase 3) |
| `modules/custeio/custeio.css` | 22 | Low (Phase 4) |
| `modules/carteira/workspace-montagem.css` | 20 | Medium (Phase 3) |
| `financeiro/extrato.css` | 12 | Low (Phase 3) |
| `modules/carteira/separacao-animations.css` | 7 | Low (Phase 3) |
| `navbar.css` | 4 | Low (Phase 1) |
| `modules/manufatura/macro-projecao.css` | 4 | Low (Phase 4) |
| `modules/margem/margem.css` | 2 | Low (Phase 4) |
| `modules/analises/drilldown.css` | 1 | Low (Phase 4) |
| **TOTAL** | **591** | |

### Existing Folder Structure

```
app/static/css/
├── _design-tokens.css      # 711 lines, HSL-based tokens
├── _utilities.css          # Utility classes
├── bootstrap-overrides.css # 646 lines, Bootstrap customization
├── contas_receber.css      # Legacy module CSS
├── navbar.css              # Navbar component
├── README.md               # Documentation
├── financeiro/
│   ├── extrato.css
│   └── premium-effects.css
└── modules/
    ├── analises/
    │   └── drilldown.css
    ├── carteira/
    │   ├── agrupados.css
    │   ├── carteira-simples.css
    │   ├── separacao-animations.css
    │   └── workspace-montagem.css
    ├── custeio/
    │   └── custeio.css
    ├── manufatura/
    │   └── macro-projecao.css
    └── margem/
        └── margem.css
```

### Dark Mode Infrastructure (Already Working)

| Component | Location | Status |
|-----------|----------|--------|
| Flash prevention script | `base.html` lines 19-27 | Working |
| Theme toggle button | `base.html` lines 604-610 | Working |
| Theme manager JS | `static/js/theme-manager.js` | Working (248 lines) |
| Token variables | `_design-tokens.css` | Working (dark/light variants) |
| LocalStorage key | `nacom-theme` | Working |
| Tab sync | `theme-manager.js` storage event | Working |
