---
phase: 06-medium-traffic-migration
plan: 03
subsystem: devolucao-pedidos-monitoramento
tags: [css-modules, design-tokens, template-migration]
dependency_graph:
  requires: ["06-01"]
  provides: ["devolucao-module-css", "monitoramento-module-css", "token-migration-devolucao-pedidos-monitoramento"]
  affects: ["06-09"]
tech_stack:
  added: []
  patterns: ["module-css-extraction", "design-token-migration"]
file_tracking:
  key_files:
    created:
      - app/static/css/modules/_devolucao.css
      - app/static/css/modules/_monitoramento.css
    modified:
      - app/static/css/main.css
      - app/templates/monitoramento/listar_entregas.html
decisions:
  - id: "06-03-01"
    context: "Devolucao base-extending templates already clean"
    choice: "Created module CSS with border-left accent styles for stat cards only"
    rationale: "Templates already use Bootstrap classes, minimal extraction needed"
  - id: "06-03-02"
    context: "Pedidos templates already clean except print template"
    choice: "No module CSS needed for pedidos, print template excluded per Phase 5 decision"
    rationale: "Templates use Bootstrap classes, imprimir_separacao_antecipado.html intentionally uses hardcoded colors for print"
  - id: "06-03-03"
    context: "Monitoramento listar_entregas.html had 39 hardcoded colors"
    choice: "Migrated all colors to design tokens, created _monitoramento.css module"
    rationale: "Inline styles needed for obs-inline-input and filter navbar, extracted to module CSS"
metrics:
  duration: "4.4 min"
  completed: "2026-01-27"
---

# Phase 06 Plan 03: Devolucao/Pedidos/Monitoramento Migration Summary

**One-liner:** Migrated devolucao/pedidos/monitoramento modules, creating module CSS files and replacing 39 hardcoded colors with design tokens in listar_entregas.html.

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Migrate devolucao module | 98fcc8f6 | DONE |
| 2 | Migrate pedidos and monitoramento modules | f20425eb | DONE |

## Key Changes

### Task 1: Devolucao Module

**Files created:**
- `app/static/css/modules/_devolucao.css` - Border-left accent styles for stat cards, loading overlay

**Findings:**
- Devolucao base-extending templates (depara/index.html, ocorrencias/index.html, ocorrencias/detalhe.html, registro/modal_nfd.html) already use Bootstrap classes
- No hardcoded colors found - templates were already clean
- termo_descarte.html is a standalone print template - deferred to Wave 5 (06-09-PLAN.md)

**Module CSS includes:**
- `.border-left-primary/success/warning/danger/info/secondary` accent classes
- Loading overlay styles for ocorrencias index

### Task 2: Pedidos and Monitoramento Modules

**Pedidos findings:**
- All templates already clean (use Bootstrap classes)
- imprimir_separacao_antecipado.html excluded per Phase 5 decision [05-04]
- jQuery selectors (#badgePendentes, etc.) are not color codes - false positives in grep
- No module CSS needed for pedidos

**Monitoramento migration:**
- `app/static/css/modules/_monitoramento.css` created
- `app/templates/monitoramento/listar_entregas.html` migrated:
  - 39 hardcoded colors replaced with design tokens
  - obs-inline-input: #e0e0e0, #fafafa, #495057, #adb5bd -> var(--border), var(--bg), var(--text), var(--text-muted)
  - Status indicators: #6c757d, #28a745, #dc3545 -> var(--text-muted), var(--semantic-success), var(--semantic-danger)
  - Filter navbar: #ffffff, #212529, #1a2942, #2d4a6a, #f0f6fc -> var(--bg-light), var(--text), var(--border)
  - Clear filter button: #ffc107, #ffeb3b -> var(--amber-55), var(--amber-60)
  - Spinner: #dee2e6, #6c757d -> var(--border), var(--text-muted)
  - Dark theme overrides now use design tokens

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

```bash
# Devolucao templates (excluding standalone) - PASS
grep -r "#[0-9a-fA-F]\{3,6\}" app/templates/devolucao/ --include="*.html" | grep -v "{#" | grep -v "termo_descarte" | wc -l
# Result: 0

# Pedidos templates (excluding print) - PASS
grep -r "#[0-9a-fA-F]\{3,6\}" app/templates/pedidos/ --include="*.html" | grep -v "{#" | grep -v "imprimir" | wc -l
# Result: 4 (all jQuery selectors, not colors)

# Monitoramento templates - PASS
grep -r "#[0-9a-fA-F]\{3,6\}" app/templates/monitoramento/ --include="*.html" | grep -v "{#" | wc -l
# Result: 1 (jQuery selector #accordionEntregas, not a color)

# Module CSS files exist - PASS
ls app/static/css/modules/_devolucao.css
ls app/static/css/modules/_monitoramento.css

# Special cases NOT modified - PASS
ls app/templates/devolucao/termo_descarte.html  # exists, unchanged
grep "style=" app/templates/pedidos/imprimir_separacao_antecipado.html | head -1  # still has inline styles
```

## Files Changed

### Created
- `app/static/css/modules/_devolucao.css` (64 lines)
- `app/static/css/modules/_monitoramento.css` (145 lines)

### Modified
- `app/static/css/main.css` - Added devolucao and monitoramento module imports
- `app/templates/monitoramento/listar_entregas.html` - 39 colors migrated to tokens

## Next Phase Readiness

Ready to proceed with 06-04-PLAN.md (agente, cadastros, custos_extra modules).

### Dependencies Satisfied
- Module CSS infrastructure from 06-01 working correctly
- Import pattern established and verified
- Token migration patterns proven across module types
