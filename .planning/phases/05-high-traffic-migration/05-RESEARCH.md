# Phase 5: High-Traffic Migration - Research

**Researched:** 2026-01-27
**Domain:** CSS Migration, Template Refactoring, Print Styles
**Confidence:** HIGH

## Summary

Phase 5 migrates three priority modules (financeiro, carteira, embarques) to the design system. This research analyzed 46 templates across these modules, counting hardcoded colors, inline styles, and identifying migration patterns.

Key findings:
1. **Financeiro** has the most work (23 templates, 210 hardcoded colors, 190 inline styles)
2. **Embarques** print templates require special handling (must work without CSS variables for print)
3. **Carteira** templates (dashboard, agrupados) already use many design tokens - mainly badge/status colors need migration
4. Several templates (cnab400_*) already define dark mode rules with `[data-theme="dark"]` but use hardcoded hex colors instead of tokens
5. The **component CSS system is mature** - `_tables.css`, `_badges.css`, `_buttons.css` all have custom property APIs ready for use

**Primary recommendation:** Migrate per-file within each module, extracting inline `<style>` blocks to module-specific CSS files that use the layer system. Print views should use a `@media print` block that forces light mode colors.

## Module Analysis

### Financeiro Module (23 templates)

| Template | Hardcoded Colors | Inline Styles | Complexity |
|----------|------------------|---------------|------------|
| `cnab400_lote_detalhe.html` | 79 | 2 | HIGH - custom status badges, tabs |
| `cnab400_hub.html` | 46 | 1 | MEDIUM - stat cards, tables |
| `cnab400_sem_match.html` | 42 | 2 | MEDIUM - similar to cnab400_hub |
| `dashboard.html` | 20 | 1 | MEDIUM - section cards, links |
| `exportar_hub.html` | 6 | - | LOW - fallback colors only |
| `contas_receber.html` | 6 | 2 | LOW |
| `baixas_hub.html` | 4 | 35 | MEDIUM - many inline styles |
| `crud_abatimentos.html` | 2 | 30 | MEDIUM |
| Other templates | ~5 total | ~110 total | LOW each |

**Total:** 210 hardcoded colors, 190 inline style attributes

**Pattern observed:** Most templates already use CSS variables as fallbacks (e.g., `var(--text-muted, #6c757d)`). Migration involves removing the fallback values and ensuring tokens cover all cases.

**Existing CSS infrastructure:**
- `app/static/css/financeiro/extrato.css` - Extrato module styles
- `app/static/css/financeiro/premium-effects.css` - Visual effects (already theme-aware)

### Carteira Module (14 templates + 3 partials + JS files)

| Template | Hardcoded Colors | Inline Styles | Complexity |
|----------|------------------|---------------|------------|
| `agrupados_balanceado.html` | ~30 in CSS | 15 | HIGH - complex filters, badges |
| `mapa_pedidos.html` | 26 | 9 | MEDIUM - map markers |
| `simples.html` | - | 43 | MEDIUM - inline only |
| `programacao_em_lote.html` | 1 | 10 | LOW |
| `dashboard.html` | 0 | 2 | LOW - already uses tokens |
| Other templates | ~20 total | ~35 total | LOW each |

**Total:** 81 hardcoded colors (many in JS files), 115 inline style attributes

**Key observation:** Carteira templates use semantic classes (`badge-status`, `badge-status-accent`) that are already defined in `_badges.css`. JS files like `carteira-agrupada.js` and `workspace-montagem.js` also contain hardcoded colors for dynamic styling.

**JS files needing review:**
- `workspace-montagem.js` (7 colors)
- `carteira-agrupada.js` (2 colors)
- `modal-separacoes.js` (4 colors)
- `separacao-manager.js` (6 colors)
- `utils/notifications.js` (18 colors)
- `agendamento/atacadao/portal-atacadao.js` (8 colors)

### Embarques Module (9 templates)

| Template | Hardcoded Colors | Inline Styles | Complexity |
|----------|------------------|---------------|------------|
| `imprimir_completo.html` | 32 | 62 | HIGH - print layout |
| `imprimir_embarque.html` | 26 | 45 | HIGH - print layout |
| `imprimir_separacao.html` | 14 | 24 | MEDIUM - print layout |
| `listar_embarques.html` | 0 | 9 | LOW |
| `visualizar_embarque.html` | 5 | 17 | LOW |
| Other templates | ~2 total | ~4 total | LOW |

**Total:** 79 hardcoded colors, 161 inline style attributes

**CRITICAL:** Print templates (`imprimir_*`) are standalone HTML documents that do NOT extend `base.html`. They:
- Use their own `<style>` blocks
- Must render correctly when printed (no dark mode)
- Use white background with black text
- Should NOT be migrated to CSS variables for print reliability

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Design Tokens | native | CSS custom properties | Already established in `_design-tokens.css` |
| CSS Layers | native | Specificity control | Layer order: tokens < base < components < modules |
| Bootstrap 5.3.3 | 5.3.3 | Base component styles | Already standardized |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Module CSS files | - | Module-specific overrides | When styles can't be generalized |
| `@media print` | - | Print-specific styles | Embarques print templates |

### Already Available Components
From previous phases, these are ready for use:
- `_tables.css` - Table with sticky headers, hover states, status row colors
- `_buttons.css` - Button variants with custom property API
- `_badges.css` - Badge variants with theme-aware colors
- `_cards.css` - Card with hover glow effect
- `_forms.css` - Input styling with focus states
- `_modals.css` - Modal backdrop and content styles
- `_layout.css` - Layout utilities and z-index scale

## Architecture Patterns

### Recommended File Structure for Migrated Modules
```
app/static/css/
├── modules/
│   ├── _financeiro.css      # Module-specific overrides
│   ├── _carteira.css        # Module-specific overrides
│   └── _embarques.css       # Module-specific (not print)
└── main.css                 # Import modules in @layer modules
```

### Pattern 1: Extract Inline Styles to Module CSS
**What:** Move `<style>` blocks from templates to module CSS files
**When to use:** Any template with >10 lines of CSS in `{% block extra_css %}`
**Example:**

**Before (in template):**
```html
{% block extra_css %}
<style>
.cnab-stat { background: #fff; color: #1a1a2e; }
</style>
{% endblock %}
```

**After (in _financeiro.css):**
```css
@layer modules {
.cnab-stat {
    background: var(--bg-light);
    color: var(--text);
}
}
```

### Pattern 2: Token Replacement with Semantic Mapping
**What:** Replace hardcoded colors with appropriate design tokens
**When to use:** Every hardcoded color that isn't print-specific

**Color mapping table:**
| Hardcoded | Token | Context |
|-----------|-------|---------|
| `#fff`, `#ffffff` | `var(--bg-light)` | Backgrounds |
| `#1a1a2e`, `#212529` | `var(--text)` | Primary text |
| `#6c757d` | `var(--text-muted)` | Secondary text |
| `#e0e0e0`, `#dee2e6` | `var(--border)` | Borders |
| `#f8f9fa` | `var(--bg)` | Card backgrounds |
| `#28a745` | `var(--semantic-success)` | Success states |
| `#dc3545` | `var(--semantic-danger)` | Danger states |
| `#ffc107`, `#d39e00` | `var(--amber-50)` | Warnings |
| `#4a6cf7`, `#007bff` | `var(--amber-55)` | Primary accent |

### Pattern 3: Print Template Handling
**What:** Keep print templates with hardcoded light mode colors
**When to use:** `imprimir_*.html` templates
**Rationale:** Print stylesheets must be reliable across all printers; CSS variables may not evaluate correctly in all print contexts.

**Strategy for print templates:**
1. Keep hardcoded colors for print reliability
2. Ensure colors have good contrast on paper
3. Use `@media print` to force light appearance
4. No dark mode for print templates

### Pattern 4: CSS Variable Fallback Cleanup
**What:** Remove fallback values from CSS variables once tokens are imported
**When to use:** Templates that already use `var(--token, #fallback)` syntax

**Before:**
```css
color: var(--text-muted, #6c757d);
```

**After:**
```css
color: var(--text-muted);
```

### Anti-Patterns to Avoid
- **Don't migrate print templates to tokens:** Keep `imprimir_*.html` with hardcoded colors
- **Don't create module-specific tokens:** Use existing `_design-tokens.css` values
- **Don't use `!important` in modules layer:** Layer system handles specificity
- **Don't inline CSS in templates:** Extract to module CSS files

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status badges | Custom badge styles | `.badge-status-*` classes | Already in `_badges.css` |
| Table hover | Custom hover CSS | `.table > tbody > tr:hover` | Already in `_tables.css` |
| Card hover glow | Custom shadow | `.card` base styles | Already in `_cards.css` |
| Button variants | Custom gradients | `.btn-primary`, `.btn-secondary` | Already in `_buttons.css` |
| Dark mode toggle | Custom `[data-theme]` vars | `[data-bs-theme]` selectors | Bootstrap 5.3 standard |

**Key insight:** Most visual patterns are already solved in the component library. Migration is mostly about **removing duplicate inline styles** and **using existing classes**.

## Common Pitfalls

### Pitfall 1: Breaking Print Templates
**What goes wrong:** Print output has wrong colors or no styling
**Why it happens:** CSS variables not evaluated correctly in print context
**How to avoid:** Keep `imprimir_*.html` with hardcoded light mode colors
**Warning signs:** Print preview shows black boxes or missing backgrounds

### Pitfall 2: Layer Order Violations
**What goes wrong:** Module styles don't override component defaults
**Why it happens:** CSS in wrong layer or not using layers at all
**How to avoid:** Always wrap module CSS in `@layer modules { }`
**Warning signs:** Styles require `!important` to work

### Pitfall 3: JavaScript Hardcoded Colors
**What goes wrong:** Dynamic elements don't respect theme
**Why it happens:** JS sets `element.style.backgroundColor = '#hex'` directly
**How to avoid:** Use CSS classes or read token values via `getComputedStyle`
**Warning signs:** Dynamically added elements have wrong colors in dark mode

### Pitfall 4: Fallback Value Drift
**What goes wrong:** Fallback values diverge from actual token values
**Why it happens:** Tokens updated but fallbacks in templates not synced
**How to avoid:** Remove fallbacks entirely once tokens are confirmed working
**Warning signs:** Slight color differences between static and dynamic content

### Pitfall 5: Mobile Layout Breaks
**What goes wrong:** Tables or cards overflow on mobile
**Why it happens:** Fixed widths in inline styles
**How to avoid:** Use responsive classes, `max-width: 100%`, `.table-responsive`
**Warning signs:** Horizontal scroll on entire page instead of just table

## Code Examples

### Module CSS File (verified pattern from Phase 1-4)
```css
/* app/static/css/modules/_financeiro.css */
@layer modules {

/* ═══════════════════════════════════════════════════════════════
   FINANCEIRO MODULE - Component overrides
   ═══════════════════════════════════════════════════════════════ */

/* CNAB Status Badges - Semantic colors */
.status-badge--importado {
    background: hsla(0 0% 50% / 0.1);
    color: var(--text-muted);
}
.status-badge--aguardando {
    background: hsla(45 90% 50% / 0.15);
    color: var(--amber-50);
}
.status-badge--concluido {
    background: hsla(145 50% 35% / 0.15);
    color: var(--semantic-success);
}
.status-badge--erro {
    background: hsla(0 70% 50% / 0.15);
    color: var(--semantic-danger);
}

/* Dashboard section cards */
.fin-section-card {
    background: var(--bg-light);
    border: 1px solid var(--border);
}

.fin-section-link:hover {
    background: var(--amber-50);
    color: hsl(45 100% 20%);
}

} /* End @layer modules */
```

### Template After Migration
```html
{% block extra_css %}
{# Styles moved to modules/_financeiro.css #}
{% endblock %}

{% block content %}
<div class="cnab-container">
    <header class="cnab-header">
        <h1 class="cnab-header__title">
            <i class="fas fa-file-invoice-dollar text-primary"></i>
            CNAB400
        </h1>
    </header>
    <!-- Uses .table with design system styling -->
    <div class="table-responsive">
        <table class="table">
            <!-- ... -->
        </table>
    </div>
</div>
{% endblock %}
```

### Print Template (keep hardcoded)
```html
<!-- imprimir_embarque.html - DO NOT MIGRATE -->
<style>
    body {
        font-family: Arial, sans-serif;
        color: #000;           /* Keep hardcoded black */
        background: white;     /* Keep hardcoded white */
    }
    .header {
        background-color: #007bff;  /* Keep hardcoded */
        color: white;
    }
    @media print {
        body { background: white !important; }
    }
</style>
```

### JavaScript Token Access (for dynamic styling)
```javascript
// Instead of: element.style.backgroundColor = '#28a745';
// Use CSS classes or read computed values:

// Option 1: Toggle classes
element.classList.add('bg-success');

// Option 2: Read token value if needed
const root = document.documentElement;
const successColor = getComputedStyle(root).getPropertyValue('--semantic-success');
element.style.backgroundColor = successColor;
```

## Migration Approach

### Recommended: Per-Module, Per-File Strategy

**Phase 5.1: Financeiro Module**
1. Create `app/static/css/modules/_financeiro.css`
2. Migrate `dashboard.html` first (lowest complexity, validates pattern)
3. Migrate `cnab400_hub.html` and `cnab400_lote_detalhe.html` (similar patterns)
4. Migrate remaining templates
5. Verify dark mode on all templates

**Phase 5.2: Carteira Module**
1. Create `app/static/css/modules/_carteira.css`
2. Migrate `dashboard.html` (mostly done, cleanup only)
3. Migrate `agrupados_balanceado.html` (preserve layout, change colors only)
4. Audit JS files for hardcoded colors (defer to Phase 6 or separate task)

**Phase 5.3: Embarques Module**
1. Create `app/static/css/modules/_embarques.css`
2. Migrate `listar_embarques.html` and `visualizar_embarque.html`
3. **DO NOT migrate** `imprimir_*.html` - verify print still works
4. Test print views in Chrome print preview

### Verification Checklist
- [ ] Dark mode toggle works on all migrated templates
- [ ] No hardcoded #hex colors in migrated templates (except print)
- [ ] Print templates still render correctly on paper
- [ ] Mobile scroll works on all tables
- [ ] No `!important` added in module CSS
- [ ] All new CSS is in `@layer modules`

## Open Questions

1. **JS hardcoded colors - Phase 5 or defer?**
   - What we know: 50+ hardcoded colors in JS files
   - What's unclear: Effort required, whether to use CSS classes or read tokens
   - Recommendation: Defer JS migration to Phase 6 or separate task

2. **Print template dark mode bypass**
   - What we know: Print templates must not use dark mode
   - What's unclear: Whether base.html injects dark theme class
   - Recommendation: Print templates don't extend base.html, so no issue

3. **Module CSS loading strategy**
   - What we know: Can add to main.css or load per-page
   - What's unclear: Performance impact of loading all modules
   - Recommendation: Add to main.css since files are small (<5KB each)

## Sources

### Primary (HIGH confidence)
- Codebase analysis: Direct inspection of 46 templates
- `app/static/css/` - Component CSS files with established patterns
- `_design-tokens.css` - Token definitions and theme variations
- Phase 1-4 research documents in `.planning/phases/`

### Secondary (MEDIUM confidence)
- Bootstrap 5.3 documentation - Theme color system
- MDN CSS variables - Print media behavior

### Tertiary (LOW confidence)
- Community patterns for CSS variable print handling

## Metadata

**Confidence breakdown:**
- Module analysis: HIGH - Direct file inspection with grep counts
- Migration patterns: HIGH - Based on established Phase 1-4 patterns
- Print handling: MEDIUM - Based on best practices, not tested
- JS migration: LOW - Identified but not deeply analyzed

**Research date:** 2026-01-27
**Valid until:** 60 days (stable patterns, CSS infrastructure complete)
