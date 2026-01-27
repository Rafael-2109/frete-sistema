# CSS Architecture for Flask/Jinja2 Design System Migration

**Project:** Frete Sistema (Nacom Goya)
**Researched:** 2026-01-26
**Overall Confidence:** HIGH (based on codebase analysis + current best practices)

---

## Executive Summary

This document defines the CSS architecture for migrating 363 templates with 106 inline `<style>` blocks to a standardized design system. The architecture leverages CSS Cascade Layers for specificity control, maintains a no-build-tools approach with pure CSS, and provides a clear migration path from scattered styles to centralized modules.

---

## Recommended Architecture

### Visual Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CASCADE LAYERS ORDER                         │
│  (Earlier layers = Lower priority | Later layers = Higher priority) │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   @layer reset      →  Browser normalization                        │
│   @layer tokens     →  Design tokens (colors, spacing, typography)  │
│   @layer base       →  Bootstrap overrides, global element styles   │
│   @layer components →  Reusable UI components (.btn, .card, etc.)   │
│   @layer modules    →  Page/feature-specific styles                 │
│   @layer utilities  →  Single-purpose utility classes               │
│   @layer overrides  →  Legacy/inline style migration (temporary)    │
│                                                                     │
│   [Unlayered CSS]   →  Highest priority (avoid except emergencies)  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Layer | Responsibility | Files | Communicates With |
|-------|---------------|-------|-------------------|
| `reset` | Browser normalization | `_reset.css` | None (foundation) |
| `tokens` | Design tokens, CSS variables | `_design-tokens.css` | All other layers consume tokens |
| `base` | Bootstrap overrides, typography, global elements | `bootstrap-overrides.css`, `_base.css` | Consumes tokens |
| `components` | Reusable UI components | `_components.css`, `modules/shared/*.css` | Consumes tokens, base styles |
| `modules` | Feature/page-specific styles | `modules/<feature>/*.css` | Consumes tokens, components |
| `utilities` | Atomic utility classes | `_utilities.css` | Consumes tokens |
| `overrides` | Legacy migration layer | `_legacy.css` (temporary) | Override anything |

---

## File/Folder Structure Recommendation

### Current Structure (AS-IS)

```
app/static/css/
├── _design-tokens.css          # ✓ Good foundation
├── _utilities.css              # ✓ Keep
├── bootstrap-overrides.css     # ✓ Imports tokens
├── navbar.css                  # Component (move to modules)
├── contas_receber.css          # Legacy module CSS
├── financeiro/
│   ├── premium-effects.css
│   └── extrato.css
└── modules/
    ├── carteira/               # ✓ Good pattern
    │   ├── agrupados.css
    │   └── ...
    ├── analises/
    ├── custeio/
    ├── manufatura/
    └── margem/
```

### Recommended Structure (TO-BE)

```
app/static/css/
│
├── main.css                    # Entry point - imports all in order
│
├── layers/                     # Layer definitions
│   ├── _layer-order.css        # @layer reset, tokens, base, components, modules, utilities, overrides;
│   └── _reset.css              # Minimal reset (optional, Bootstrap handles most)
│
├── tokens/
│   ├── _design-tokens.css      # All CSS custom properties (existing)
│   └── _color-aliases.css      # Semantic color mappings (optional)
│
├── base/
│   ├── _bootstrap-overrides.css  # Bootstrap customizations (existing)
│   ├── _typography.css           # Font families, sizes, weights
│   └── _forms.css                # Form element defaults
│
├── components/                   # Shared/reusable components
│   ├── _buttons.css              # Button variants
│   ├── _cards.css                # Card styles
│   ├── _badges.css               # Badge system
│   ├── _tables.css               # Table variants
│   ├── _modals.css               # Modal styles
│   ├── _alerts.css               # Alert variants
│   ├── _dropdowns.css            # Dropdown menus
│   └── _navbar.css               # Navigation (moved from root)
│
├── utilities/
│   ├── _spacing.css              # Margin/padding utilities
│   ├── _text.css                 # Text utilities
│   ├── _backgrounds.css          # Background utilities
│   ├── _borders.css              # Border utilities
│   └── _utilities.css            # Existing utilities (refactor over time)
│
├── modules/                      # Feature-specific styles
│   ├── carteira/                 # ✓ Already exists
│   │   ├── agrupados.css
│   │   ├── workspace-montagem.css
│   │   └── separacao-animations.css
│   ├── financeiro/               # ✓ Partially exists
│   │   ├── dashboard.css
│   │   ├── extrato.css
│   │   ├── cnab.css              # Consolidate CNAB styles
│   │   └── premium-effects.css
│   ├── embarques/
│   ├── recebimento/
│   ├── comercial/
│   ├── estoque/
│   ├── portaria/
│   └── [other modules]/
│
└── legacy/
    └── _inline-overrides.css     # Temporary: migrated inline styles
```

---

## Import Order and Cascade Strategy

### Entry Point: `main.css`

```css
/* ═══════════════════════════════════════════════════════════════════════
   MAIN.CSS - Entry Point
   All imports in strict cascade order
   ═══════════════════════════════════════════════════════════════════════ */

/* 1. Layer Order Declaration (MUST be first) */
@layer reset, tokens, base, components, modules, utilities, overrides;

/* 2. Reset Layer */
@import url('./layers/_reset.css') layer(reset);

/* 3. Design Tokens Layer */
@import url('./tokens/_design-tokens.css') layer(tokens);

/* 4. Base Layer - Bootstrap Overrides */
@import url('./base/_bootstrap-overrides.css') layer(base);
@import url('./base/_typography.css') layer(base);
@import url('./base/_forms.css') layer(base);

/* 5. Components Layer */
@import url('./components/_buttons.css') layer(components);
@import url('./components/_cards.css') layer(components);
@import url('./components/_badges.css') layer(components);
@import url('./components/_tables.css') layer(components);
@import url('./components/_modals.css') layer(components);
@import url('./components/_alerts.css') layer(components);
@import url('./components/_dropdowns.css') layer(components);
@import url('./components/_navbar.css') layer(components);

/* 6. Utilities Layer */
@import url('./utilities/_utilities.css') layer(utilities);

/* 7. Legacy/Override Layer (temporary during migration) */
@import url('./legacy/_inline-overrides.css') layer(overrides);
```

### Template-Level Loading (base.html)

```html
<head>
    <!-- 1. CDN: Bootstrap (loads first, lowest priority) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">

    <!-- 2. CDN: Icons and third-party -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css">

    <!-- 3. Design System: Main entry point -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}?v=7">

    <!-- 4. Module-specific CSS (per-page, loaded via Jinja block) -->
    {% block extra_css %}{% endblock %}
</head>
```

### Template-Specific Styles (individual templates)

```jinja2
{% block extra_css %}
<!-- Module CSS loaded at module layer priority -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/modules/financeiro/dashboard.css') }}?v=7">
{% endblock %}
```

### CSS Module File Structure

```css
/* ═══════════════════════════════════════════════════════════════════════
   modules/financeiro/dashboard.css
   Feature: Central Financeira Dashboard
   Layer: modules (loaded at module priority)
   ═══════════════════════════════════════════════════════════════════════ */

@layer modules {
    /* Dashboard-specific styles */
    .fin-dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: var(--space-4);
    }

    .fin-card-stat {
        background: var(--gradient);
        border: var(--border-card);
        border-radius: var(--radius-lg);
    }

    /* Module-specific variants */
    .fin-card-stat.fin-success {
        border-left: 4px solid var(--semantic-success);
    }
}
```

---

## Data Flow Direction (CSS Cascade)

```
┌──────────────────────────────────────────────────────────────────┐
│                     CSS VARIABLE FLOW                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   _design-tokens.css                                             │
│   ├─── :root { --amber-55: hsl(45 95% 55%); }                   │
│   │                                                              │
│   └─► base/_bootstrap-overrides.css                              │
│       ├─── .btn-primary { background: var(--amber-55); }        │
│       │                                                          │
│       └─► components/_buttons.css                                │
│           ├─── .btn-action { ... uses tokens ... }              │
│           │                                                      │
│           └─► modules/carteira/agrupados.css                    │
│               └─── .badge-filtro { ... uses tokens ... }        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     STYLE OVERRIDE FLOW                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Priority: LOW ────────────────────────────────────────► HIGH   │
│                                                                  │
│   Bootstrap  →  tokens  →  base  →  components  →  modules  →    │
│                                                            ↓     │
│                              utilities  →  overrides  →  inline  │
│                                                                  │
│   Layer priority ALWAYS beats selector specificity!              │
│   A simple selector in `utilities` beats complex in `base`       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Handling Template-Specific Styles

### Pattern 1: Module CSS Files (Recommended)

For templates with substantial custom styles (>20 lines), create dedicated module files:

```
# Template: app/templates/financeiro/dashboard.html
# CSS: app/static/css/modules/financeiro/dashboard.css

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/modules/financeiro/dashboard.css') }}?v=7">
{% endblock %}
```

### Pattern 2: Shared Module Components

For styles shared across multiple templates in a module:

```
# Shared across all financeiro templates:
app/static/css/modules/financeiro/_shared.css

# Template-specific:
app/static/css/modules/financeiro/dashboard.css
app/static/css/modules/financeiro/extrato.css
app/static/css/modules/financeiro/cnab.css
```

### Pattern 3: Inline Styles (Temporary/Small)

For truly one-off styles (<10 lines) during migration:

```jinja2
{% block extra_css %}
<style>
@layer modules {
    /* Page-specific override - document why */
    .special-table-layout { grid-template-columns: 1fr 2fr 1fr; }
}
</style>
{% endblock %}
```

### Pattern 4: Component Extensions

For custom component variants specific to a feature:

```css
/* modules/carteira/agrupados.css */
@layer modules {
    /* Extends base .badge component for carteira filters */
    .badge-filtro {
        /* Base styles */
    }

    /* Carteira-specific badge states */
    .badge-filtro.badge-agendamento-sem { ... }
    .badge-filtro.badge-agendamento-com { ... }
}
```

---

## Migration Path from Inline Styles

### Phase 1: Audit and Categorize (Week 1)

1. **Count**: 106 templates with `<style>` blocks identified
2. **Categorize** by size and reusability:
   - **Small** (<10 lines): Consider keeping inline with `@layer`
   - **Medium** (10-50 lines): Extract to module CSS
   - **Large** (>50 lines): Extract and refactor into components
   - **Shared**: Identify duplicate patterns across templates

### Phase 2: Create Layer Infrastructure (Week 1)

1. Create `main.css` with layer order declaration
2. Create folder structure (`layers/`, `tokens/`, `base/`, `components/`, `utilities/`, `modules/`, `legacy/`)
3. Move existing `_design-tokens.css` content to use `@layer tokens`
4. Wrap `bootstrap-overrides.css` content in `@layer base`

### Phase 3: Extract Component Styles (Week 2-3)

1. Identify repeated patterns across inline styles
2. Extract to `components/` folder:
   - Buttons variants → `_buttons.css`
   - Card patterns → `_cards.css`
   - Table styles → `_tables.css`
   - Badge systems → `_badges.css`

### Phase 4: Migrate Module Styles (Week 3-6)

Priority order by template count:
1. **financeiro/** (15+ templates) - Week 3
2. **carteira/** (already partially migrated) - Week 3
3. **embarques/** (10+ templates) - Week 4
4. **comercial/** (8+ templates) - Week 4
5. **manufatura/** (12+ templates) - Week 5
6. **portal/** (15+ templates) - Week 5
7. **Remaining modules** - Week 6

### Phase 5: Remove Legacy Layer (Week 7)

1. Verify all inline styles migrated
2. Remove `legacy/_inline-overrides.css`
3. Remove `overrides` from layer order
4. Update `?v=` cache parameter

---

## Migration Checklist Per Template

```markdown
## Migration: [template_name.html]

- [ ] Identify inline `<style>` block content
- [ ] Categorize styles (component, module, utility, override)
- [ ] Check if styles duplicate existing CSS
- [ ] Move to appropriate CSS file with @layer
- [ ] Update template to use {% block extra_css %} if needed
- [ ] Replace inline styles with class names
- [ ] Test dark mode
- [ ] Test light mode
- [ ] Increment cache version
```

---

## Build Order Implications

### No Build Tools Required

This architecture uses native CSS features:
- `@import` for modular loading
- `@layer` for cascade control
- CSS custom properties for theming
- No preprocessor (SCSS, Less) required
- No bundler (Webpack, Vite) required

### Performance Considerations

1. **HTTP/2 multiplexing**: Modern browsers handle multiple CSS files efficiently
2. **Single entry point**: `main.css` imports all, single request cascade
3. **Module loading**: Per-page CSS loads only when needed via `extra_css` block
4. **Cache strategy**: Version query parameters (`?v=7`) for cache busting

### Browser Support

- CSS Cascade Layers: Chrome 99+, Firefox 97+, Safari 15.4+ (March 2022+)
- All modern browsers support this architecture
- No polyfills needed for target audience (business users on modern browsers)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Nested @import Chains

```css
/* BAD: Creates waterfall loading */
/* file-a.css */
@import url('./file-b.css');

/* file-b.css */
@import url('./file-c.css');  /* Browser must wait for file-b */
```

**Instead**: Single-level imports in `main.css`

### Anti-Pattern 2: !important Wars

```css
/* BAD: Escalating specificity */
.btn-primary { background: blue !important; }
.special-btn.btn-primary { background: green !important !important; }
```

**Instead**: Use layers - higher layer always wins regardless of specificity

### Anti-Pattern 3: Unlayered Overrides

```css
/* BAD: Unlayered CSS beats ALL layers */
.my-override { color: red; }  /* This will override @layer utilities */
```

**Instead**: Always wrap in appropriate layer

### Anti-Pattern 4: Inline Styles in Jinja Templates

```jinja2
<!-- BAD: Hardcoded colors -->
<div style="background-color: #28a745; color: white;">
```

**Instead**: Use semantic classes

```jinja2
<div class="bg-status-success text-white">
```

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Layer Architecture | HIGH | CSS Cascade Layers well-documented, browser support stable |
| Folder Structure | HIGH | Based on existing successful modules (carteira, financeiro) |
| Migration Path | MEDIUM | 106 templates is significant scope, timeline may vary |
| Performance | HIGH | HTTP/2 + single entry point proven effective |
| Dark/Light Mode | HIGH | Existing token system already supports theming |

---

## Sources

### Architecture Research
- [Rethinking Modular CSS and Build-Free Design Systems](https://gomakethings.com/rethinking-modular-css-and-build-free-design-systems/)
- [Organizing Design System Component Patterns With CSS Cascade Layers](https://css-tricks.com/organizing-design-system-component-patterns-with-css-cascade-layers/)
- [CSS Cascade Layers Guide](https://css-tricks.com/css-cascade-layers/)
- [Integrating CSS Cascade Layers To An Existing Project](https://www.smashingmagazine.com/2025/09/integrating-css-cascade-layers-existing-project/)

### Flask/Jinja2 Best Practices
- [How To Structure a Large Flask Application - Best Practices 2025](https://dev.to/gajanan0707/how-to-structure-a-large-flask-application-best-practices-for-2025-9j2)
- [Flask Project Structure Best Practices](https://muneebdev.com/flask-project-structure-best-practices/)

### Codebase Analysis
- Existing `_design-tokens.css` (711 lines, comprehensive HSL token system)
- Existing `modules/carteira/agrupados.css` (1240 lines, well-structured module)
- Existing `bootstrap-overrides.css` (646 lines, Bootstrap customizations)
- 363 total templates, 106 with inline `<style>` blocks

---

## Next Steps

1. **Create layer infrastructure** - `main.css` and folder structure
2. **Wrap existing CSS in layers** - No functional change, just layer declarations
3. **Extract shared components** - Buttons, cards, badges, tables
4. **Migrate high-priority modules** - financeiro, carteira, embarques
5. **Establish migration pattern** - Document and standardize approach
6. **Track progress** - Checklist per template, weekly reviews
