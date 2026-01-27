# Phase 6: Medium-Traffic Migration - Research

**Researched:** 2026-01-27
**Domain:** CSS Migration, Template Refactoring, JS Color Tokens
**Confidence:** HIGH

## Summary

Phase 6 migrates the remaining modules not covered in Phase 5 to the design system. This research analyzed 307 templates across 31 modules, identifying 1,189 hardcoded colors and 739 inline style attributes. The analysis revealed significant variation in module complexity and identified several special cases requiring distinct handling strategies.

Key findings:
1. **Pallet v2** is the largest migration target (554 hardcoded colors across 14 templates) with a consistent inline CSS pattern
2. **Rastreamento** templates (8 of 11) are **standalone public-facing pages** that don't extend base.html
3. **Manufatura** templates already use Bootstrap CSS variables (`var(--bs-*)`) - partial theme-aware already
4. **BI module** uses Chart.js with hardcoded colors for visualizations
5. **JS files** contain 51 hardcoded colors that need migration (deferred from Phase 5)
6. **Print templates** (7 total across modules) should remain with hardcoded colors per Phase 5 decision

**Primary recommendation:** Migrate in waves by complexity tier, starting with low-complexity modules to build momentum, then tackling high-complexity modules (pallet v2, rastreamento) that require special patterns.

## Module Analysis Summary

### Tier 1: HIGH Complexity (500+ colors or special handling required)

| Module | Templates | Hardcoded Colors | Inline Styles | Special Considerations |
|--------|-----------|------------------|---------------|------------------------|
| **pallet** | 24 | 554 | 47 | v2/ templates have extensive inline CSS blocks |
| **rastreamento** | 11 | 139 | 26 | 8 standalone templates (don't extend base.html) |
| **motochefe** | 47 | 97 | 108 | Separate subsystem, 2 print templates |

### Tier 2: MEDIUM Complexity (50-150 colors)

| Module | Templates | Hardcoded Colors | Inline Styles | Special Considerations |
|--------|-----------|------------------|---------------|------------------------|
| **bi** | 4 | 92 | 13 | Chart.js integration, gradient backgrounds |
| **portal** | 32 | 62 | 28 | Sendas/Atacadao/Tenda submodules |
| **recebimento** | 14 | 43 | 100 | High inline styles, fiscal forms |
| **monitoramento** | 8 | 39 | 13 | Single high-color template |
| **fretes** | 39 | 28 | 95 | High inline styles, audit views |

### Tier 3: LOW Complexity (<50 colors)

| Module | Templates | Hardcoded Colors | Inline Styles | Special Considerations |
|--------|-----------|------------------|---------------|------------------------|
| **comercial** | 8 | 27 | 37 | - |
| **manufatura** | 21 | 26 | 61 | Already uses var(--bs-*), 1 print template |
| **pedidos** | 14 | 20 | 97 | 1 print template |
| **devolucao** | 5 | 16 | 43 | 1 standalone (termo_descarte.html) |
| **estoque** | 7 | 12 | 25 | - |
| **cotacao** | 6 | 6 | 10 | - |
| **producao** | 8 | 5 | 4 | - |
| **custeio** | 8 | 4 | 39 | - |
| **integracoes** | 7 | 3 | - | TagPlus views |
| **portaria** | 5 | 2 | 9 | - |

### Tier 4: MINIMAL (0 colors, tokens only needed)

| Module | Templates | Inline Styles | Notes |
|--------|-----------|---------------|-------|
| **separacao** | 2 | - | Already clean |
| **faturamento** | 8 | 20 | No hardcoded colors |
| **localidades** | 5 | - | Clean |
| **auth** | 6 | - | Clean |
| **metricas** | 1 | - | Clean |
| **relatorios_fiscais** | 2 | - | Clean |
| **transportadoras** | 2 | - | Clean |
| **permissions** | 2 | - | Clean |
| **tabelas** | 5 | - | Clean |
| **cadastros_agendamento** | 3 | - | Clean |
| **odoo** | 4 | 1 | Clean |
| **veiculos** | 1 | - | Clean |
| **vinculo** | 3 | - | Clean |
| **main** | 1 | - | Clean |

## Special Cases

### 1. Standalone Templates (Rastreamento)

8 templates don't extend base.html - they are public-facing mobile pages for delivery tracking:

```
app/templates/rastreamento/
├── aceite_lgpd.html          (standalone, 20 colors)
├── app_inicio.html           (standalone, 3 colors)
├── confirmacao.html          (standalone, 3 colors)
├── erro.html                 (standalone, 2 colors)
├── questionario_entrega.html (standalone, 32 colors)
├── rastreamento_ativo.html   (standalone, 17 colors)
├── scanner_qrcode.html       (standalone, 4 colors)
├── upload_canhoto.html       (standalone, 13 colors)
├── detalhes.html             (extends base)
├── monitoramento.html        (extends base)
└── dashboard.html            (extends base)
```

**Strategy:** Create `_rastreamento-standalone.css` with self-contained design tokens for these pages. They need a green theme (success color primary) instead of amber.

### 2. Print Templates (7 total)

Per Phase 5 decision [05-04], print templates should keep hardcoded colors:

```
app/templates/embarques/imprimir_*.html          (already excluded in Phase 5)
app/templates/manufatura/programacao_linhas_print.html
app/templates/motochefe/produtos/motos/imprimir_devolucao.html
app/templates/motochefe/vendas/pedidos/imprimir.html
app/templates/pedidos/imprimir_separacao_antecipado.html
```

**Strategy:** Skip these templates. Mark as "intentionally excluded" in documentation.

### 3. Pallet v2 Templates

The pallet v2 system uses a consistent pattern of extensive inline CSS blocks with:
- Stat cards (`.stat-card`, `.stat-icon`)
- Status colors (`.status-badge--*`)
- Page headers with breadcrumbs
- Table styling

**Pattern observed (from direcionamento.html):**
```css
.stat-icon.total { background: #e8f4fd; color: #0d6efd; }
.stat-icon.transportadora { background: #cff4fc; color: #0dcaf0; }
.stat-icon.cliente { background: #d1e7dd; color: #198754; }
```

**Strategy:** Create `_pallet.css` with shared component styles. Extract common patterns:
- `.pallet-stat-*` variants for stat card icons
- `.pallet-status-*` for status badges
- `.pallet-page-header` for page headers

### 4. BI Module (Chart.js)

BI templates use Chart.js with hardcoded colors in JS:
```javascript
backgroundColor: 'rgba(102, 126, 234, 0.1)',
borderColor: 'rgba(102, 126, 234, 1)',
```

**Strategy:** Create a `ChartColors` utility that reads CSS custom properties:
```javascript
const ChartColors = {
  primary: getComputedStyle(document.documentElement).getPropertyValue('--chart-primary'),
  // ...
};
```

Add chart-specific tokens to design system.

### 5. Manufatura (Partially Theme-Aware)

Manufatura templates already use Bootstrap CSS variables:
```css
background-color: var(--bs-tertiary-bg, #f8f9fa);
color: var(--bs-body-color);
```

**Strategy:** Verify existing variables work in dark mode. Replace any remaining hardcoded colors with design tokens. May require minimal work.

## JavaScript Files with Hardcoded Colors

From Phase 5 deferral, these JS files need migration:

| File | Colors | Pattern |
|------|--------|---------|
| `carteira-simples.js` | 20 | Inline styles with `!important`, Odoo tag colors |
| `portal-async-integration.js` | 20 | Status toast colors, progress indicators |
| `programacao-lote.js` | 4 | Status colors |
| `carteira-service.js` | 3 | Badge colors |
| `analises-drilldown.js` | 2 | Chart colors |
| `contas_receber_comparativo.js` | 1 | Single color |
| `capacitor/gps-service-hibrido.js` | 1 | Map marker |

**Total:** 51 hardcoded colors across 7 JS files

**Strategy for JS colors:**
1. For inline styles: Replace with CSS classes when possible
2. For dynamic colors: Read from CSS custom properties using `getComputedStyle`
3. For Odoo tag colors: Map to design tokens (already has defined color palette)

**Example migration pattern:**
```javascript
// Before
element.style.setProperty('background-color', '#dc3545', 'important');

// After - Option 1: CSS class
element.classList.add('bg-danger');

// After - Option 2: Read token
const dangerColor = getComputedStyle(document.documentElement)
  .getPropertyValue('--semantic-danger').trim();
element.style.backgroundColor = dangerColor;
```

## Standard Stack

### Core (Established in Phase 1-5)
| Component | Version | Purpose | Already Available |
|-----------|---------|---------|-------------------|
| Design Tokens | native | CSS custom properties | `_design-tokens.css` |
| CSS Layers | native | Specificity control | 7-layer system in `main.css` |
| Bootstrap 5.3.3 | 5.3.3 | Base component styles | CDN + overrides |

### Module CSS Files (Pattern from Phase 5)
| File | Purpose |
|------|---------|
| `_financeiro.css` | Financeiro module overrides |
| `_carteira.css` | Carteira module overrides |
| `_embarques.css` | Embarques module overrides |

### New Module Files Needed
| File | Templates Covered | Estimated Lines |
|------|-------------------|-----------------|
| `_pallet.css` | 24 pallet templates | 300-400 |
| `_rastreamento.css` | 3 base-extending templates | 50-100 |
| `_rastreamento-standalone.css` | 8 standalone templates | 200-300 |
| `_bi.css` | 4 BI templates + chart tokens | 100-150 |
| `_portal.css` | 32 portal templates | 100-150 |
| `_recebimento.css` | 14 recebimento templates | 150-200 |
| `_fretes.css` | 39 fretes templates | 100-150 |
| `_motochefe.css` | 45 non-print motochefe | 200-250 |
| `_manufatura.css` | 20 non-print manufatura | 50-100 |

## Architecture Patterns

### Pattern 1: Module CSS File Structure (From Phase 5)

```css
/**
 * _[module].css - [Module] Module Overrides
 *
 * Token mapping:
 * - Use var(--bg-light) for card backgrounds
 * - Use var(--text) for primary text
 * - Use var(--text-muted) for secondary text
 * - Use var(--border) for borders
 * - Use var(--semantic-success/danger) for status colors
 *
 * HSL color reference:
 * - Success: hsla(145 65% 40% / alpha)
 * - Danger:  hsla(0 70% 50% / alpha)
 * - Warning/Amber: hsla(45 100% 50% / alpha)
 */

@layer modules {

  /* Component styles here */

} /* End @layer modules */
```

### Pattern 2: Standalone Template Migration

For templates that don't extend base.html, inject design tokens directly:

```html
<!DOCTYPE html>
<html lang="pt-BR" data-bs-theme="light">
<head>
    <!-- Include design tokens inline or via link -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/tokens/_design-tokens.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/modules/_rastreamento-standalone.css') }}">
    <style>
        /* Use tokens */
        body {
            background: var(--semantic-success);
            color: var(--text);
        }
    </style>
</head>
```

### Pattern 3: JS Color Token Access

```javascript
// Utility for reading CSS tokens in JS
const DesignTokens = {
  get(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(`--${name}`).trim();
  },

  // Semantic colors
  success: () => DesignTokens.get('semantic-success'),
  danger: () => DesignTokens.get('semantic-danger'),
  warning: () => DesignTokens.get('amber-50'),

  // Status colors
  odooTagColors: {
    0: () => DesignTokens.get('text-muted'),
    1: () => DesignTokens.get('semantic-danger'),
    // ... etc
  }
};
```

### Anti-Patterns to Avoid

- **Don't migrate print templates** - Keep hardcoded for reliability
- **Don't create module-specific tokens** - Use existing `_design-tokens.css` values
- **Don't use `!important` in module CSS** - Layer system handles specificity
- **Don't mix inline tokens with inline hardcoded** - Either all tokens or all hardcoded
- **Don't break standalone page structure** - Rastreamento needs to work without base.html

## Token Mapping Reference

| Hardcoded Color | Design Token | Usage Context |
|-----------------|--------------|---------------|
| `#fff`, `#ffffff` | `var(--bg-light)` | Card/container backgrounds |
| `#f8f9fa` | `var(--bg)` | Page backgrounds |
| `#212529` | `var(--text)` | Primary text |
| `#6c757d` | `var(--text-muted)` | Secondary text |
| `#dee2e6`, `#e0e0e0` | `var(--border)` | Borders |
| `#28a745`, `#198754` | `var(--semantic-success)` | Success states |
| `#dc3545` | `var(--semantic-danger)` | Danger/error states |
| `#ffc107` | `var(--amber-50)` | Warning/attention |
| `#007bff`, `#0d6efd` | `var(--amber-55)` | Primary accent |
| `#17a2b8`, `#0dcaf0` | `var(--bs-info)` | Info states |
| `#667eea`, `#764ba2` | Gradient: `var(--gradient)` | Headers |

## Common Pitfalls

### Pitfall 1: Standalone Template Dark Mode

**What goes wrong:** Standalone templates don't inherit theme from base.html
**Why it happens:** No `[data-bs-theme]` attribute set
**How to avoid:** Add theme attribute to html element, include theme toggle if needed
**Warning signs:** Standalone pages always appear in light mode

### Pitfall 2: Chart.js Color Updates

**What goes wrong:** Charts don't update colors when theme changes
**Why it happens:** Chart.js caches colors at render time
**How to avoid:** Listen for theme change event, call `chart.update()`
**Warning signs:** Charts have wrong colors after theme toggle

### Pitfall 3: Pallet v2 Template Duplication

**What goes wrong:** Similar CSS blocks duplicated across 14 templates
**Why it happens:** Copy-paste development without extraction
**How to avoid:** Extract common patterns to `_pallet.css` first, then reference
**Warning signs:** Same class definitions in multiple template `<style>` blocks

### Pitfall 4: JS Inline Style Specificity

**What goes wrong:** Token-based styles overridden by old `!important` inline styles
**Why it happens:** JS uses `setProperty('...', '!important')` to override table row classes
**How to avoid:** Remove `!important` from JS, use specific CSS selectors instead
**Warning signs:** Dynamic elements ignore theme colors

### Pitfall 5: Green Theme for Rastreamento

**What goes wrong:** Rastreamento uses green (success) as primary, not amber
**Why it happens:** Module has different brand identity
**How to avoid:** Create rastreamento-specific CSS variables or accept amber for consistency
**Warning signs:** Visual inconsistency with existing rastreamento pages

## Migration Order Recommendation

### Wave 1: Low-Complexity Clean-up (Est. 2-3 hours)
1. **Tier 4 modules** (minimal or zero colors) - Verify already clean
2. **Tier 3 low** (producao, portaria, integracoes) - Quick wins
3. **manufatura** - Already partially theme-aware, minimal changes

### Wave 2: Medium Templates (Est. 4-6 hours)
4. **comercial** (27 colors, 8 templates) - Standard patterns
5. **estoque** (12 colors, 7 templates) - Standard patterns
6. **cotacao** (6 colors, 6 templates) - Standard patterns
7. **custeio** (4 colors, 8 templates) - Standard patterns
8. **devolucao** (16 colors, 5 templates) - 1 standalone to handle

### Wave 3: High-Volume Modules (Est. 6-8 hours)
9. **recebimento** (43 colors, 100 inline) - Many inline styles
10. **fretes** (28 colors, 95 inline) - Many inline styles
11. **pedidos** (20 colors, 97 inline) - 1 print template to skip
12. **portal** (62 colors, 28 inline) - Multiple submodules
13. **monitoramento** (39 colors, 1 template) - Single high-color template

### Wave 4: Complex Modules (Est. 8-10 hours)
14. **bi** (92 colors) - Chart.js integration required
15. **motochefe** (97 colors, 47 templates) - Large module, 2 print templates
16. **pallet v2** (554 colors, 14 templates) - Largest single effort

### Wave 5: Special Cases (Est. 4-6 hours)
17. **rastreamento standalone** (139 colors, 8 templates) - Standalone pattern
18. **JS files** (51 colors, 7 files) - Different migration approach

**Total estimated effort:** 24-33 hours

## Open Questions

1. **Rastreamento theme identity**
   - What we know: Uses green as primary color, different from amber theme
   - What's unclear: Should it adopt amber or keep green identity?
   - Recommendation: Keep green for rastreamento (public-facing, established brand)

2. **BI Chart colors in dark mode**
   - What we know: Chart.js uses hardcoded RGBA colors
   - What's unclear: What colors should charts use in dark mode?
   - Recommendation: Create chart-specific tokens, test readability

3. **Motochefe as separate system**
   - What we know: Large subsystem with own templates (47)
   - What's unclear: Is it actively used? Priority level?
   - Recommendation: Verify usage before investing in migration

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: grep and file inspection
- Phase 5 RESEARCH.md and PLAN files
- Existing module CSS files (`_carteira.css`, `_financeiro.css`, `_embarques.css`)

### Secondary (MEDIUM confidence)
- Phase 5 decisions from STATE.md

### Tertiary (LOW confidence)
- Effort estimates based on Phase 5 velocity (may vary)

## Metadata

**Confidence breakdown:**
- Module analysis: HIGH - Direct grep counts and file inspection
- Token mapping: HIGH - Based on established Phase 5 patterns
- Migration order: MEDIUM - Based on complexity heuristics
- Effort estimates: LOW - Extrapolated from Phase 5, actual may vary
- JS migration: LOW - Identified but not deeply analyzed

**Research date:** 2026-01-27
**Valid until:** 60 days (stable patterns, established infrastructure)
