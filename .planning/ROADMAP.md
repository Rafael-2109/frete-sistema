# Roadmap: CSS Design System Migration

## Overview

This roadmap migrates the freight management system from scattered inline CSS (1,472 hardcoded hex colors across 106 templates with `<style>` blocks) to a centralized design token system. The approach establishes layer infrastructure first to solve the existing 591 `!important` problem, extracts reusable components, then systematically migrates templates by module priority. Each phase delivers verifiable improvements in dark mode consistency and mobile responsiveness.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Layer Infrastructure** - Establish CSS cascade control and standardize Bootstrap
- [x] **Phase 2: Component Library** - Extract reusable button, card, badge, modal, and form patterns
- [x] **Phase 3: Table System** - Implement responsive tables with sticky headers and mobile scroll
- [x] **Phase 4: Layout Patterns** - Standardize sidebar and grid system
- [ ] **Phase 5: High-Traffic Migration** - Migrate financeiro, carteira, and embarques modules
- [ ] **Phase 6: Medium-Traffic Migration** - Migrate comercial, manufatura, portal, and remaining modules
- [ ] **Phase 7: Cleanup & Polish** - Remove !important declarations, legacy styles, and validate coverage

## Phase Details

### Phase 1: Layer Infrastructure
**Goal**: Establish cascade control via CSS Layers so subsequent work doesn't require !important battles
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):
  1. All CSS loads through `main.css` entry point with explicit `@layer` declarations
  2. Bootstrap 5.3.3 is the ONLY version loaded across all templates (no mixed 5.1.3/5.3.0)
  3. Existing `_design-tokens.css` is wrapped in `@layer tokens` and loads correctly
  4. Dark mode toggle works on all existing templates without flash (FOWT prevention verified)
  5. New CSS file structure exists: `layers/`, `tokens/`, `base/`, `components/`, `modules/`, `utilities/`
**Plans**: 3 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md - Create main.css entry point with @layer declarations and folder structure (Wave 1)
- [x] 01-02-PLAN.md - Standardize Bootstrap 5.3.3 across all 10 templates (Wave 1)
- [x] 01-03-PLAN.md - Wrap existing CSS files in layers and update base.html (Wave 2)

**Note:** Pre-existing `modules/` directory with legacy CSS intentionally kept separate. Will be migrated in Phase 5-6.

### Phase 2: Component Library
**Goal**: Reusable component CSS extracted from inline patterns, available for template migration
**Depends on**: Phase 1
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05
**Success Criteria** (what must be TRUE):
  1. Button variants (primary, secondary, danger, ghost) render correctly in dark and light modes
  2. Card components have consistent borders and shadows using design tokens
  3. Status badges are legible in both themes (no white text on light backgrounds)
  4. Modals follow theme colors automatically (no hardcoded backgrounds)
  5. Form inputs have visible focus states that adapt to theme
**Plans**: 3 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md - Extract button component variants (Wave 1)
- [x] 02-02-PLAN.md - Extract card and badge patterns (Wave 1)
- [x] 02-03-PLAN.md - Extract modal and form patterns (Wave 2)

### Phase 3: Table System
**Goal**: Data tables work correctly on mobile and desktop with proper theming
**Depends on**: Phase 2
**Requirements**: TABL-01, TABL-02, TABL-03, LAYO-01
**Success Criteria** (what must be TRUE):
  1. Tables scroll horizontally on mobile without cutting off content
  2. Long tables have sticky headers that remain visible while scrolling
  3. Table row hover states adapt to current theme (visible in both dark and light)
  4. Action buttons in table rows are fully accessible on mobile (not clipped)
**Plans**: 2 plans in 2 waves

Plans:
- [x] 03-01-PLAN.md - Create base table component with responsive wrapper and action column protection (Wave 1)
- [x] 03-02-PLAN.md - Add sticky headers, theme-adaptive hover states, and main.css integration (Wave 2)

### Phase 4: Layout Patterns
**Goal**: Consistent page structure and navigation across all views
**Depends on**: Phase 3
**Requirements**: LAYO-02 (reinterpreted: navbar mobile responsiveness), LAYO-03
**Success Criteria** (what must be TRUE):
  1. Navbar functions correctly on mobile (collapse, dropdowns, touch targets 44x44px)
  2. Grid system applies consistently (no competing grid implementations)
  3. Content area uses full available width without horizontal overflow
**Plans**: 2 plans in 1 wave

Plans:
- [x] 04-01-PLAN.md - Optimize navbar for mobile touch usability (Wave 1)
- [x] 04-02-PLAN.md - Create layout utilities with overflow protection and z-index scale (Wave 1)

### Phase 5: High-Traffic Migration
**Goal**: Priority modules (financeiro, carteira, embarques) fully migrated to design system
**Depends on**: Phase 4
**Requirements**: MIGR-01 (partial), MIGR-02 (partial), MIGR-04
**Success Criteria** (what must be TRUE):
  1. Financeiro dashboard and all child templates use tokens (no hardcoded colors)
  2. Carteira templates (dashboard, agrupados) use tokens for colors while preserving layout
  3. Embarques templates (listar, visualizar) work in both themes; print templates (imprimir_*) keep hardcoded light colors
  4. All migrated templates pass dark mode visual inspection
  5. All migrated templates work on mobile (tested on real device or accurate emulation)
**Plans**: 5 plans in 3 waves

Plans:
- [ ] 05-01-PLAN.md - Create module CSS files and integrate into main.css (Wave 1)
- [ ] 05-02-PLAN.md - Migrate financeiro templates (dashboard, cnab400_hub, cnab400_lote_detalhe) (Wave 2)
- [ ] 05-03-PLAN.md - Migrate carteira templates (dashboard, agrupados_balanceado) (Wave 2)
- [ ] 05-04-PLAN.md - Migrate embarques templates (listar, visualizar) - print templates EXCLUDED (Wave 2)
- [ ] 05-05-PLAN.md - Visual verification checkpoint (Wave 3)

**Note:** Print templates (imprimir_*.html) are intentionally EXCLUDED from migration. They keep hardcoded light mode colors for print reliability. JS files with hardcoded colors are DEFERRED to Phase 6.

### Phase 6: Medium-Traffic Migration
**Goal**: Remaining modules (comercial, manufatura, portal, estoque, recebimento, etc.) migrated
**Depends on**: Phase 5
**Requirements**: MIGR-01 (partial), MIGR-02 (partial)
**Success Criteria** (what must be TRUE):
  1. Comercial templates use design tokens
  2. Manufatura production views use tokens while preserving semantic color coding
  3. Portal templates use tokens
  4. Estoque, recebimento, portaria, and remaining modules use tokens
  5. All migrated templates pass dark mode and mobile tests
**Plans**: TBD

Plans:
- [ ] 06-01: Migrate comercial module templates
- [ ] 06-02: Migrate manufatura module templates
- [ ] 06-03: Migrate portal and remaining modules

### Phase 7: Cleanup & Polish
**Goal**: Remove technical debt, validate complete coverage, prevent regression
**Depends on**: Phase 6
**Requirements**: MIGR-03, MIGR-01 (remaining), MIGR-02 (remaining)
**Success Criteria** (what must be TRUE):
  1. !important declarations reduced to under 50 (from 591) or justified as intentional
  2. All 106 templates with inline `<style>` blocks have styles extracted to CSS files
  3. Hardcoded hex colors reduced to near-zero (from 1,472)
  4. CSS coverage audit shows no orphaned rules
  5. Stylelint or equivalent prevents regression in future development
**Plans**: TBD

Plans:
- [ ] 07-01: Audit and reduce !important declarations
- [ ] 07-02: Final template cleanup and legacy removal
- [ ] 07-03: CSS coverage audit and prevention tooling

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Layer Infrastructure | 3/3 | Complete | 2026-01-27 |
| 2. Component Library | 3/3 | Complete | 2026-01-27 |
| 3. Table System | 2/2 | Complete | 2026-01-27 |
| 4. Layout Patterns | 2/2 | Complete | 2026-01-27 |
| 5. High-Traffic Migration | 0/5 | Not started | - |
| 6. Medium-Traffic Migration | 0/3 | Not started | - |
| 7. Cleanup & Polish | 0/3 | Not started | - |

---
*Roadmap created: 2026-01-26*
*Phase 1 planned: 2026-01-26*
*Total phases: 7 | Total plans: 20*
