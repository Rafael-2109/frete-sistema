# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** Todas as telas devem ter cores e contraste funcionais em dark mode E mobile, sem CSS inline hardcoded.
**Current focus:** Phase 6 - Medium-Traffic Migration (IN PROGRESS)

## Current Position

Phase: 6 of 7 (Medium-Traffic Migration)
Plan: 8 of 12 in current phase
Status: In progress
Last activity: 2026-01-27 - Completed 06-08 Pallet Module Migration

Progress: [████████████] 100% (22/21 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: 3.9 min
- Total execution time: 91 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-layer-infrastructure | 3 | 8 min | 2.7 min |
| 02-component-library | 3 | 6 min | 2 min |
| 03-table-system | 2 | 3 min | 1.5 min |
| 04-layout-patterns | 2 | 3 min | 1.5 min |
| 05-high-traffic-migration | 5 | 25 min | 5 min |
| 06-medium-traffic-migration | 8 | 75 min | 9.4 min |

**Recent Trend:**
- Last 5 plans: 06-05 (7 min), 06-06 (6 min), 06-07 (4 min), 06-08 (12 min)
- Trend: Pallet migration larger but follows established patterns

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 1]: Usar CSS Cascade Layers (@layer) para controle de especificidade, evitando guerras de !important
- [Phase 1]: Bootstrap 5.3.3 como versao unica, eliminando mix de versoes 5.1.3/5.3.0
- [Phase 1]: Migrar por modulo, nunca big bang (validado por research que indica tentativa anterior falhou)
- [01-01]: 7-layer order: reset, tokens, base, components, modules, utilities, overrides
- [01-01]: main.css as single entry point - no CSS rules, only @layer and imports
- [01-02]: Keep erro.html and confirmacao.html without Bootstrap JS (static pages)
- [01-03]: Fonts import as unlayered in main.css (available to all layers)
- [01-03]: Original CSS files kept as backup until verified in production
- [01-03]: premium-effects.css and style.css remain separate (migrated in Phase 5)
- [02-01]: CSS custom property API (--_btn-bg, --_btn-color) for component variants
- [02-01]: Use :where() for low-specificity state selectors
- [02-01]: Zero !important in components - layer system handles specificity
- [02-02]: Cards use CSS custom property API (--_card-bg, --_card-border, etc.) for easy overrides
- [02-02]: Badge outline variants use currentColor for border to match text color
- [02-02]: Light mode adjustments for badge contrast (darker green for success)
- [02-03]: Modal background uses --bg-light (3-tier elevation) instead of var(--gradient)
- [02-03]: Custom state classes use CSS custom property override instead of !important
- [02-03]: Extended form support includes checkboxes, radios, switches, floating labels
- [03-01]: Table custom property API (--_table-bg, --_table-color, --_table-border-color)
- [03-01]: Scrollbar 6px height, 3px border-radius for visibility without intrusiveness
- [03-01]: Mobile touch targets 44x44px minimum per WCAG 2.5.5
- [03-02]: Sticky header on th elements (not thead) due to CSS spec limitation
- [03-02]: Z-index hierarchy: corner (11) > header (10) > first column (5)
- [03-02]: Hover uses :where() for low specificity, dark 5% white / light 4% black overlay
- [03-02]: Status rows (success, warning, etc.) use hsla 15% base / 28% hover
- [04-01]: Touch device detection via @media (hover: none) and (pointer: coarse)
- [04-01]: Disable translateX hover effect on touch devices
- [04-01]: Mobile menu max-height with overflow scroll for long menus
- [04-02]: Z-index scale documents Bootstrap defaults (1000-1055) plus custom table values (1005-1011)
- [04-02]: Page structure uses 56px navbar height assumption
- [04-02]: Modern dvh units with calc(100vh - 56px) fallback for older browsers
- [05-01]: Module files placed directly in modules/ folder (not subdirectories)
- [05-01]: Each module file includes token mapping documentation for migration guidance
- [05-04]: Print templates (imprimir_*.html) intentionally excluded from token migration
- [05-04]: CSS color-mix() for keyframe animation darkening instead of hardcoded values
- [05-03]: Use hsla() format over rgba() for consistency with HSL color model in tokens
- [05-03]: Cart-* prefix for carteira-specific semantic classes
- [05-02]: Use hsla colors for non-semantic icon backgrounds (icon variants don't fit success/danger/amber patterns)
- [05-05]: bootstrap-theme-override.css MUST be outside @layer to override Bootstrap CDN
- [05-05]: Remove :root from dark mode selectors to avoid conflicts with light mode
- [05-05]: Cards use --bg-light (100% white in light mode) for proper elevation hierarchy
- [05-05]: .text-accent light mode: hsl(45 100% 28%) for contrast
- [05-05]: Badge overrides needed in bootstrap-theme-override.css for theme-adaptive colors
- [06-01]: Chart color tokens in _bi.css for JS access (--chart-primary, --chart-secondary, etc.)
- [06-02]: No _comercial.css needed - comercial module only had 1 hardcoded color
- [06-02]: SweetAlert colors use hsl() not tokens (JS context doesn't support CSS variables)
- [06-02]: Table row states need [data-bs-theme="dark"] selector with hsla() backgrounds
- [06-03]: Devolucao templates already clean - minimal module CSS needed
- [06-03]: Pedidos templates already clean - no module CSS needed (print excluded per 05-04)
- [06-03]: Monitoramento listar_entregas.html had 39 colors migrated to tokens
- [06-04]: Preserved existing class names in fretes (badge-status-*) to avoid template changes
- [06-04]: Print styles kept hardcoded neutral colors (intentional - no theme on paper)
- [06-05]: Portal brand colors migrated to design system tokens (consistent dark mode)
- [06-05]: Rastreamento uses semantic-success as primary accent (green = delivery tracking brand)
- [06-05]: 8 standalone rastreamento templates deferred to Wave 5 (06-09-PLAN.md)
- [06-06]: ChartColors utility reads --chart-* CSS tokens via getComputedStyle
- [06-06]: MutationObserver watches data-bs-theme for chart auto-update on theme change
- [06-06]: Region/expense type/sector colors defined as CSS tokens for JS access
- [06-07]: JS getCorHex() functions read CSS custom properties with hex fallbacks
- [06-07]: Product colors (Laranja, Prata) kept as hex - represent physical motorcycle colors
- [06-08]: Pallet module CSS extraction (1298 lines) with stat cards, badges, tables
- [06-08]: BEM-like naming for pallet components (.pallet-stat__icon--total)
- [06-08]: controle_pallets/, nf_remessa/, movimentacoes/ templates deferred (254 colors remaining)

### Pending Todos

- Remove original CSS files from root css/ folder after production verification:
  - _design-tokens.css
  - bootstrap-overrides.css
  - navbar.css
  - _utilities.css

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-27
Stopped at: Completed 06-08-PLAN.md (Pallet Module Migration)
Resume file: None

---
*Next step: Continue Phase 6 with remaining tier migrations (06-09 through 06-12)*
