---
phase: 06-medium-traffic-migration
plan: 04
subsystem: ui-theming
tags: [css-migration, design-tokens, recebimento, fretes]

dependency_graph:
  requires:
    - "06-01"
  provides:
    - recebimento-module-tokens
    - fretes-module-tokens
  affects:
    - "06-05"
    - "07-xx"

tech_stack:
  added: []
  patterns:
    - module-css-extraction
    - hsla-color-functions
    - semantic-class-naming
    - dark-mode-overrides

files:
  key_files_created:
    - "app/static/css/modules/_recebimento.css"
    - "app/static/css/modules/_fretes.css"
  key_files_modified:
    - "app/templates/recebimento/central_compras.html"
    - "app/templates/recebimento/central_fiscal.html"
    - "app/templates/recebimento/primeira_compra.html"
    - "app/templates/recebimento/divergencias.html"
    - "app/templates/recebimento/preview_consolidacao.html"
    - "app/templates/fretes/visualizar_frete.html"
    - "app/templates/fretes/listar_fretes.html"
    - "app/templates/fretes/analise_diferencas.html"

decisions:
  - decision: "Preserve existing class names in fretes templates"
    rationale: "Avoid breaking changes by using existing badge-status-* class names in module CSS"
    context: "fretes"

metrics:
  duration: "~25 minutes"
  completed: "2026-01-27"
  colors_removed: 71
  inline_styles_addressed: 195
---

# Phase 06 Plan 04: Recebimento/Fretes Migration Summary

JWT auth with refresh rotation using jose library - Migrated recebimento (43 colors, 100 inline styles) and fretes (28 colors, 95 inline styles) modules to use design tokens with styles extracted to module CSS files.

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Migrate recebimento module (43 colors, 100 inline styles) | e1bf81e6 | Done |
| 2 | Migrate fretes module (28 colors, 95 inline styles) | c71cfd64 | Done |

## Recebimento Module Migration

### Styles Extracted to _recebimento.css

1. **Hub Dashboard Grid**: `.compras-dashboard-grid`, `.fiscal-dashboard-grid`
2. **Icon Variants**: `.fin-section-card__icon--blue`, `--green`, `--purple`, `--amber`
3. **NF Grouping Rows**: `.rec-row-blue`, `.rec-row-gray`, `.rec-border-blue`, `.rec-border-gray`
4. **NF Separator**: `.rec-nf-separator` with gradient background
5. **Timeline**: `.rec-timeline`, `.rec-timeline-item`
6. **Border Utilities**: `.rec-border-left-success`, `--warning`, `--info`, `--primary`

### Templates Migrated

- `central_compras.html` - Hub page with 4 icon variants migrated
- `central_fiscal.html` - Hub page with 3 icon variants migrated
- `primeira_compra.html` - Row alternation with NF grouping
- `divergencias.html` - Row alternation with NF grouping
- `preview_consolidacao.html` - Timeline and border left utilities

## Fretes Module Migration

### Styles Extracted to _fretes.css

1. **Status Badges**: `.badge-status-*` (pendente, tratativa, aprovado, rejeitado, pago, lancado, cancelado)
2. **Valor Badges**: `.badge-valor-*` (positivo, negativo, info, calculado, destaque)
3. **Odoo Badges**: `.badge-odoo-ok`, `.badge-odoo-pendente` with dark mode text fix
4. **Card/Table Theme**: `.card-header-theme`, `.table-thead-theme`
5. **Border Left**: `.border-left-success`, `--info`, `--warning`
6. **Dark Mode Tables**: `.table-success`, `.table-warning` with hsla backgrounds
7. **Print Styles**: Neutral colors for print media

### Templates Migrated

- `visualizar_frete.html` - All status badges and card headers
- `listar_fretes.html` - All status badges and table themes
- `analise_diferencas.html` - Gradient headers and print styles

## Verification Results

| Check | Result |
|-------|--------|
| Hardcoded colors in recebimento | 0 remaining |
| Hardcoded colors in fretes | 0 remaining |
| _recebimento.css lines | 153 |
| _fretes.css lines | 270 |
| @layer modules declaration | Present in both files |

## Technical Decisions

1. **Preserved existing class names**: Used `badge-status-*` instead of `frt-badge-status--*` to avoid template changes
2. **HSL color functions**: Used `hsla()` for semi-transparent backgrounds (e.g., table row states)
3. **Dark mode text color fix**: Added `[data-bs-theme="dark"] .badge-odoo-pendente { color: hsl(210 11% 15%); }` for warning badges
4. **Print styles**: Kept hardcoded neutral colors for print media (intentional - no theme switching on paper)

## Deviations from Plan

None - plan executed exactly as written.

## Files Changed

### Created
- `app/static/css/modules/_recebimento.css` (153 lines)
- `app/static/css/modules/_fretes.css` (270 lines)

### Modified
- 5 recebimento templates (inline styles removed)
- 3 fretes templates (inline styles removed)

## Next Phase Readiness

Ready for:
- Phase 06-05: Portal module migration
- Phase 07: Low-traffic module migration
