---
phase: 06-medium-traffic-migration
plan: 02
subsystem: ui
tags: [design-tokens, css-variables, dark-mode, templates, jinja2]

# Dependency graph
requires:
  - phase: 05-high-traffic-migration
    provides: Design tokens infrastructure, token mapping patterns
  - phase: 06-01
    provides: Module CSS structure, _bi.css example
provides:
  - 7 modules migrated from hardcoded colors to design tokens
  - Templates render correctly in both light and dark modes
  - Zero hardcoded hex colors in migrated templates
affects: [06-03, 06-04, 06-05, 07-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Replace #hex with var(--token) for background, text, border colors"
    - "Use hsl() for SweetAlert colors (not theme-dependent)"
    - "Add dark mode overrides for table row states"

key-files:
  created: []
  modified:
    - "app/templates/comercial/lista_clientes.html"
    - "app/templates/estoque/listar_movimentacoes.html"
    - "app/templates/estoque/saldo_estoque.html"
    - "app/templates/producao/listar_palletizacao_novo.html"
    - "app/templates/producao/listar_palletizacao.html"
    - "app/templates/custeio/comissao.html"
    - "app/templates/portaria/historico.html"
    - "app/templates/portaria/cadastrar_motorista.html"
    - "app/templates/integracoes/tagplus_correcao_pedidos.html"
    - "app/templates/integracoes/tagplus_vincular_nfs.html"

key-decisions:
  - "No separate _comercial.css needed - only 1 hardcoded color in module"
  - "SweetAlert colors use hsl() instead of design tokens (JS context, not CSS)"
  - "cotacao templates had no actual hardcoded colors (data-bs-parent attributes are HTML IDs, not CSS)"

patterns-established:
  - "Token mapping: #fff -> var(--bg-light), #f8f9fa -> var(--bg)"
  - "Token mapping: #212529 -> var(--text), #6c757d -> var(--text-muted)"
  - "Token mapping: #dee2e6/#ddd/#ccc -> var(--border)"
  - "SweetAlert pattern: Use hsl(H S% L%) for button colors"
  - "Table row states: Add [data-bs-theme='dark'] selector with hsla() for subtle backgrounds"

# Metrics
duration: 15min
completed: 2026-01-27
---

# Phase 6 Plan 02: Tier 3 Modules Migration Summary

**Migrated 7 low-complexity modules (comercial, estoque, cotacao, producao, custeio, portaria, integracoes) from hardcoded hex colors to design tokens for dark mode support**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-27T15:48:00Z
- **Completed:** 2026-01-27T16:03:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Migrated all 7 tier 3 modules to use design tokens
- Zero hardcoded hex colors remain in migrated templates (excluding HTML ID attributes)
- All templates now support both light and dark modes via CSS variables
- Established patterns for future template migrations

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate comercial module** - `1c5476e5` (feat)
2. **Task 2: Migrate estoque, cotacao, producao, custeio, portaria, integracoes** - `b492e1bb` (feat)

## Files Created/Modified

### comercial (1 change)
- `app/templates/comercial/lista_clientes.html` - Replace #212529 with var(--text) in badge-warning

### estoque (2 files, multiple changes)
- `app/templates/estoque/listar_movimentacoes.html` - Replace dropdown suggestion colors, SweetAlert colors
- `app/templates/estoque/saldo_estoque.html` - Replace table hover and status colors

### producao (2 files)
- `app/templates/producao/listar_palletizacao_novo.html` - Replace header bg, product code/name colors
- `app/templates/producao/listar_palletizacao.html` - Replace SweetAlert button colors

### custeio (1 file)
- `app/templates/custeio/comissao.html` - Replace autocomplete suggestion box colors

### portaria (2 files)
- `app/templates/portaria/historico.html` - Replace text-dark on bg-warning
- `app/templates/portaria/cadastrar_motorista.html` - Replace webcam border color

### integracoes (2 files)
- `app/templates/integracoes/tagplus_correcao_pedidos.html` - Replace produtos-detail background
- `app/templates/integracoes/tagplus_vincular_nfs.html` - Replace table-success and hover colors with dark mode support

## Decisions Made
- **No _comercial.css file needed:** Original plan suggested creating one, but comercial only had 1 hardcoded color - simpler to fix inline
- **cotacao module already clean:** Investigation revealed cotacao's "hex colors" were actually `data-bs-parent="#accordionFretes"` HTML attributes, not CSS colors
- **SweetAlert uses hsl() not tokens:** SweetAlert colors are set via JavaScript confirmButtonColor/cancelButtonColor properties, which don't support CSS variables. Using hsl() format for consistency but values are static

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added dark mode support for integracoes/tagplus_vincular_nfs.html table-success**
- **Found during:** Task 2 (integracoes migration)
- **Issue:** Simple token replacement would break table row highlighting in dark mode
- **Fix:** Added [data-bs-theme="dark"] selector with hsla() background color
- **Files modified:** app/templates/integracoes/tagplus_vincular_nfs.html
- **Verification:** Dark mode class properly dims the success highlight
- **Committed in:** b492e1bb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Auto-fix ensures dark mode works correctly for table states. No scope creep.

## Issues Encountered
None - all token replacements straightforward following established patterns from Phase 5

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tier 3 modules complete, ready for Tier 2 and Tier 1 migrations
- Token mapping patterns established and documented
- Dark mode support verified in migrated templates

---
*Phase: 06-medium-traffic-migration*
*Completed: 2026-01-27*
