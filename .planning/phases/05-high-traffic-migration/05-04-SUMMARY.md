---
phase: 05-high-traffic-migration
plan: 04
subsystem: ui
tags: [css, design-tokens, dark-mode, embarques, print]

# Dependency graph
requires:
  - phase: 05-01
    provides: Module CSS infrastructure and _embarques.css file
provides:
  - Embarques list and detail templates migrated to design tokens
  - Print templates intentionally excluded (documented)
  - Signature field CSS class for theme-adaptive styling
affects: [05-05, phase-6]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Print templates excluded from token migration for reliability"
    - "CSS color-mix() for keyframe animation darkening"

key-files:
  created: []
  modified:
    - app/templates/embarques/visualizar_embarque.html
    - app/static/css/modules/_embarques.css

key-decisions:
  - "Use CSS color-mix() for pulse animation darkening instead of hardcoded values"
  - "Extract inline signature field styles to .emb-signature-field class"
  - "Print templates (imprimir_*.html) intentionally excluded from migration"

patterns-established:
  - "Print exclusion pattern: templates not extending base.html keep hardcoded light colors"
  - "Signature field pattern: .emb-signature-field for transparent input with bottom border"

# Metrics
duration: 2min
completed: 2026-01-27
---

# Phase 5 Plan 4: Embarques Templates Migration Summary

**Migrated embarques templates (listar, visualizar) to design tokens, excluding print templates for print reliability**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-27T14:22:03Z
- **Completed:** 2026-01-27T14:24:03Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Removed all hardcoded hex colors from visualizar_embarque.html (5 colors)
- Converted @keyframes pulse-red animation to use CSS variables
- Created .emb-signature-field class for theme-adaptive signature inputs
- Verified listar_embarques.html already compliant (0 hardcoded colors)
- Documented print template exclusion in _embarques.css

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate listar_embarques.html and visualizar_embarque.html** - `6b5a74a1` (feat)

**Note:** Task 2 was verification-only (no file changes needed)

## Files Created/Modified

- `app/templates/embarques/visualizar_embarque.html` - Replaced hardcoded colors with CSS variables
- `app/static/css/modules/_embarques.css` - Added embarques-specific classes and print exclusion documentation

## Decisions Made

1. **CSS color-mix() for animation darkening** - Used `color-mix(in srgb, var(--bs-danger) 80%, black)` instead of hardcoded `#b02a37` for the pulse animation's 50% keyframe
2. **Print templates excluded** - imprimir_completo.html (32), imprimir_embarque.html (26), imprimir_separacao.html (14) keep hardcoded colors for print reliability

## Deviations from Plan

None - plan executed exactly as written.

## Print Template Verification

Print templates verified as intentionally excluded:

| Template | Hardcoded Colors | Status |
|----------|------------------|--------|
| imprimir_completo.html | 32 | Excluded (expected 30+) |
| imprimir_embarque.html | 26 | Excluded |
| imprimir_separacao.html | 14 | Excluded |

These templates do NOT extend base.html and should NOT be migrated to tokens.

## Issues Encountered

None - listar_embarques.html was already compliant with 0 hardcoded colors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Embarques module templates (non-print) now support dark mode
- Print templates maintain reliable light-mode output for all printers
- Ready for remaining wave 2 plans (05-02, 05-03, 05-05)

---
*Phase: 05-high-traffic-migration*
*Completed: 2026-01-27*
