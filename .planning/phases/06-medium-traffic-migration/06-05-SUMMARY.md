---
phase: 06-medium-traffic-migration
plan: 05
status: complete
subsystem: portal-rastreamento-modules
tags: [portal, rastreamento, sendas, atacadao, tenda, design-tokens, css-modules, dark-mode]
dependency_graph:
  requires: ["06-01"]
  provides:
    - portal-design-tokens
    - rastreamento-base-templates-tokens
    - portal-css-module
    - rastreamento-css-module
  affects: ["06-09"]
tech_stack:
  patterns:
    - "CSS @layer modules for portal styles"
    - "CSS @layer modules for rastreamento styles"
    - "HSL color values in JS for Leaflet markers"
    - "Design token extraction to CSS modules"
key_files:
  created: []
  modified:
    - app/static/css/modules/_portal.css
    - app/static/css/modules/_rastreamento.css
    - app/templates/portal/sendas/verificacao.html
    - app/templates/portal/sendas/exportacao.html
    - app/templates/portal/sendas/gerenciar_sessao.html
    - app/templates/portal/sendas_sessao.html
    - app/templates/portal/central_portais.html
    - app/templates/rastreamento/detalhes.html
    - app/templates/rastreamento/monitoramento.html
    - app/templates/rastreamento/dashboard.html
decisions:
  - id: portal-brand-colors
    decision: "Migrate brand-specific colors (Sendas/Atacadao/Tenda) to design system tokens instead of preserving brand colors"
    rationale: "Ensures consistent dark mode support across all portal submodules"
  - id: rastreamento-green-accent
    decision: "Use semantic-success as primary accent for rastreamento module (green = delivery tracking brand)"
    rationale: "Maintains delivery tracking visual identity while using design system tokens"
  - id: standalone-rastreamento-deferred
    decision: "8 standalone rastreamento templates deferred to Wave 5 (06-09-PLAN.md)"
    rationale: "Per plan specification - standalone templates are separate concern"
metrics:
  duration: ~7min
  completed: 2026-01-27
---

# Phase 06 Plan 05: Portal/Rastreamento Migration Summary

Portal module (32 templates) and rastreamento base-extending templates (3) migrated to design tokens with CSS extraction to module files.

## What Changed

### Task 1: Portal Module Migration

**Portal CSS Module** (`_portal.css`):
- Upload/drag-drop area styles with design tokens
- Status badge classes (confirmado, pendente, nao-encontrado, divergencia, exportado)
- Summary cards with semantic color variants
- Export cards for Sendas exportacao
- Session status cards with gradient backgrounds (valid/invalid/none)
- History items with semantic border colors
- Dark mode adjustments for status badges

**Portal Templates Migrated**:
- `sendas/verificacao.html` - 21 colors removed, using CSS classes
- `sendas/exportacao.html` - 15 colors removed, linked to _portal.css
- `sendas/gerenciar_sessao.html` - Standalone template linked to main.css
- `sendas_sessao.html` - JS color literals converted to hsl()
- `central_portais.html` - Animation keyframe colors converted to hsl()

### Task 2: Rastreamento Base-Extending Templates

**Rastreamento CSS Module** (`_rastreamento.css`):
- Map container styles (#mapa, #mapa-detalhes, #mapa-monitoramento)
- Timeline component (detalhes.html)
- Status cards with gradient backgrounds (rastr-status-card)
- Metric boxes for KPI display
- Monitoramento layout grid
- Stats row cards
- Alerta dificuldade component with pulse animation
- Lista rastreamentos sidebar
- Status badges (ativo, proximo, entregue, dificuldade)
- Modal dificuldade styles
- Leaflet marker overrides
- Loading overlay with dark mode support
- Card rastreamento hover effects

**Templates Migrated**:
- `detalhes.html` - 15 colors, timeline, status cards
- `monitoramento.html` - 30 colors, stats, alerts, lists
- `dashboard.html` - 10 colors, status badges

**NOT Modified** (deferred to 06-09):
- `aceite_lgpd.html`
- `canhoto_upload.html`
- `iniciar.html`
- `rastrear_base.html`
- `rastrear_full.html`
- `rastrear_minimal.html`
- `resultado_ocr.html`
- `status_motorista.html`

## Commits

| Hash | Message |
|------|---------|
| b6f94ba6 | feat(06-05): migrate portal module to design tokens |
| 9afa73af | feat(06-05): migrate rastreamento base-extending templates to design tokens |

## Verification Results

1. Portal templates hardcoded colors: **0** (was 62)
2. Rastreamento base-extending templates: **0** (was 55)
3. CSS modules with @layer modules: **verified**
4. Standalone rastreamento templates: **unchanged** (preserved for Wave 5)

## Token Mapping Applied

### Portal Module
| Original | Token |
|----------|-------|
| #fff | var(--bg-light) |
| #f8f9fa | var(--bg) |
| #212529 | var(--text) |
| #6c757d | var(--text-muted) |
| #dee2e6 | var(--border) |
| #28a745 | var(--semantic-success) |
| #dc3545 | var(--semantic-danger) |
| #ffc107 | var(--amber-50) |
| #007bff | var(--accent) |

### Rastreamento Module
| Original | Token |
|----------|-------|
| #28a745 | var(--semantic-success) - primary accent |
| #17a2b8 | hsl(188, 78%, 41%) - info/entregue |
| #ffc107 | var(--amber-50) - proximo/warning |
| #dc3545 | var(--semantic-danger) - dificuldade |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

- All portal submodules (Sendas, Atacadao, Tenda) ready for dark mode
- Rastreamento base-extending templates ready for dark mode
- 8 standalone rastreamento templates queued for 06-09-PLAN.md (Wave 5)
- No blockers identified
