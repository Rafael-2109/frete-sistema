---
phase: 05-high-traffic-migration
plan: 02
subsystem: financeiro-templates
tags: [css-migration, design-tokens, financeiro, cnab400, dark-mode]

dependency-graph:
  requires: [05-01]
  provides:
    - financeiro-dashboard-tokens
    - cnab400-hub-tokens
    - cnab400-lote-detalhe-tokens
    - financeiro-module-css
  affects: [05-05]

tech-stack:
  added: []
  patterns:
    - module-css-extraction
    - design-token-migration
    - semantic-badge-classes

file-tracking:
  created:
    - app/static/css/modules/_financeiro.css (1001 lines)
  modified:
    - app/templates/financeiro/dashboard.html
    - app/templates/financeiro/cnab400_hub.html
    - app/templates/financeiro/cnab400_lote_detalhe.html

decisions:
  - key: icon-color-variants
    choice: Use hsla colors for non-semantic icon backgrounds
    reason: Icon backgrounds need semantic meaning but don't fit success/danger/amber patterns

metrics:
  duration: 4 min
  completed: 2026-01-27
---

# Phase 5 Plan 02: Financeiro Templates Migration Summary

**One-liner:** Migrated financeiro dashboard and CNAB400 templates to design tokens, extracting 1001 lines of CSS with 121 token references.

## What Was Done

### Task 1: Migrate financeiro/dashboard.html
- **Status:** Complete
- **Commit:** e2f82c10
- **Changes:**
  - Removed 20+ hardcoded hex colors from inline `<style>` block
  - Extracted all styles to `app/static/css/modules/_financeiro.css`
  - Added semantic icon variants: custos, receber, pagar, fretes, faturamento, contabil, conciliacao
  - Replaced inline style attribute on conciliacao icon with CSS class
  - Template now references external CSS via main.css imports

### Task 2: Migrate CNAB400 templates
- **Status:** Complete
- **Commit:** 78d32378
- **Changes:**
  - cnab400_hub.html: Removed 46 hardcoded colors
  - cnab400_lote_detalhe.html: Removed 79 hardcoded colors
  - Removed `[data-theme="dark"]` CSS custom property overrides (design tokens handle this)
  - Added semantic badge classes: status-badge, match-badge, extrato-badge, ocorrencia-badge
  - Dark mode now works automatically via design token system

## Verification Results

| Check | Result | Expected |
|-------|--------|----------|
| dashboard.html hardcoded colors | 0 | 0 |
| cnab400_hub.html hardcoded colors | 0 | 0 |
| cnab400_lote_detalhe.html hardcoded colors | 0 | 0 |
| _financeiro.css token usages | 121 | 20+ |
| _financeiro.css lines | 1001 | 50+ |

## Commits

| Hash | Message |
|------|---------|
| e2f82c10 | feat(05-02): migrate financeiro dashboard to design tokens |
| 78d32378 | feat(05-02): migrate CNAB400 templates to design tokens |

## Key Files Created/Modified

### Created
- `app/static/css/modules/_financeiro.css` - Complete financeiro module styles (1001 lines)
  - Dashboard grid and card styles (.fin-*)
  - CNAB container, header, stats, table styles (.cnab-*)
  - Lote container, header, stats, table styles (.lote-*)
  - Status badges with 7 variants (importado, aguardando, aprovado, etc.)
  - Match badges with 8 variants (encontrado, sem_match, processado, etc.)
  - Extrato badges with 5 variants
  - Occurrence badges for CNAB codes
  - Alert boxes (warning, success)
  - Error tooltips
  - Button variants (primary, success, outline)

### Modified
- `app/templates/financeiro/dashboard.html` - Removed inline styles, added CSS class references
- `app/templates/financeiro/cnab400_hub.html` - Removed inline styles, uses external CSS
- `app/templates/financeiro/cnab400_lote_detalhe.html` - Removed inline styles, uses external CSS

## Deviations from Plan

None - plan executed exactly as written.

## Design Token Mapping

| Original Pattern | Design Token |
|-----------------|--------------|
| #fff, #ffffff | var(--bg-light) |
| #1a1a2e, #212529 | var(--text) |
| #6c757d | var(--text-muted) |
| #e0e0e0, #dee2e6 | var(--border) |
| #28a745 | var(--semantic-success) |
| #dc3545 | var(--semantic-danger) |
| #ffc107 | var(--amber-50) |
| #4a6cf7 (primary blue) | var(--amber-55) (accent) |
| rgba(x,x,x,0.x) | hsla(x x% x% / 0.x) |

## Next Phase Readiness

- [x] All templates compile without errors
- [x] Dark mode works via design token system
- [x] No inline style blocks remain
- [x] All styles in @layer modules

Ready for visual verification and Plan 05-05 (Additional Financeiro Templates).
