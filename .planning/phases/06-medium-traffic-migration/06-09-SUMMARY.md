---
phase: 06
plan: 09
subsystem: rastreamento-standalone
tags: [standalone, design-tokens, dark-mode, css-variables, rastreamento, devolucao]
dependency-graph:
  requires:
    - 06-01 # Design tokens established
  provides:
    - standalone CSS for mobile-first rastreamento pages
    - dark mode support for 9 standalone templates
    - self-contained design tokens (no base.html dependency)
  affects: []
tech-stack:
  added: []
  patterns:
    - Self-contained CSS with duplicated tokens for standalone pages
    - CSS custom properties for all colors
    - data-bs-theme attribute for dark mode detection
key-files:
  created:
    - app/static/css/modules/_rastreamento-standalone.css
  modified:
    - app/static/css/main.css
    - app/templates/rastreamento/aceite_lgpd.html
    - app/templates/rastreamento/app_inicio.html
    - app/templates/rastreamento/confirmacao.html
    - app/templates/rastreamento/erro.html
    - app/templates/rastreamento/questionario_entrega.html
    - app/templates/rastreamento/rastreamento_ativo.html
    - app/templates/rastreamento/scanner_qrcode.html
    - app/templates/rastreamento/upload_canhoto.html
    - app/templates/devolucao/termo_descarte.html
decisions:
  - id: standalone-tokens
    summary: Standalone pages include duplicated design tokens (no base.html dependency)
  - id: dark-mode-attr
    summary: All standalone templates use data-bs-theme="light" attribute for future dark mode
  - id: green-brand
    summary: Green primary (--standalone-primary) preserved for delivery tracking brand
  - id: print-hardcoded
    summary: termo_descarte.html keeps hardcoded colors for print (black/white on paper)
metrics:
  duration: 7 min
  completed: 2026-01-27
---

# Phase 6 Plan 09: Standalone Templates Migration Summary

Self-contained CSS with design tokens for 9 standalone templates without base.html dependency

## Summary

Migrated 8 rastreamento templates and 1 devolucao template to use CSS custom properties instead of hardcoded colors. Created a self-contained CSS file with duplicated design tokens since standalone pages don't load main.css or base.html.

## Tasks Completed

### Task 1: Create standalone CSS file with design tokens
- Created `_rastreamento-standalone.css` with ~900 lines of self-contained styles
- Includes duplicated design tokens for light/dark modes
- Components: cards, buttons, forms, status indicators, upload areas, loading overlays
- Green primary theme (--standalone-primary) for delivery tracking branding
- Added import to main.css for consistency

**Commit:** `29f24370` - feat(06-09): create standalone CSS for rastreamento templates

### Task 2: Migrate standalone templates to use design tokens
Migrated 9 templates:
- `aceite_lgpd.html` - LGPD consent page (20+ colors migrated)
- `questionario_entrega.html` - Delivery questionnaire (32+ colors migrated)
- `rastreamento_ativo.html` - Active tracking page (17 colors migrated)
- `upload_canhoto.html` - Receipt upload (13 colors migrated)
- `scanner_qrcode.html` - QR code scanner
- `confirmacao.html` - Delivery confirmation
- `erro.html` - Error page
- `app_inicio.html` - App landing page
- `termo_descarte.html` - Disposal term (print template - link added, print styles kept hardcoded)

For each template:
1. Added `data-bs-theme="light"` attribute to `<html>`
2. Added CSS link to `_rastreamento-standalone.css`
3. Replaced hardcoded colors with CSS custom properties
4. Preserved green branding (delivery tracking theme)

**Commit:** `4b3cbe80` - feat(06-09): migrate standalone templates to design tokens

## Verification Results

- Hardcoded colors reduced from 100+ to near-zero
- All 9 templates include CSS link
- All 9 templates have data-bs-theme attribute
- Green theme preserved in all templates

## Key Artifacts

### Files Created
1. `app/static/css/modules/_rastreamento-standalone.css`
   - Self-contained design tokens (light + dark)
   - Component styles (cards, buttons, forms, status indicators)
   - ~900 lines with extensive comments

### Files Modified
- 9 HTML templates (added CSS link, data-bs-theme, replaced colors)
- `app/static/css/main.css` (added import)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Duplicated tokens in standalone CSS | Standalone pages don't load main.css; need self-contained styles |
| data-bs-theme="light" default | Prepares for future dark mode toggle; currently all pages light |
| Green primary preserved | Delivery tracking brand color (green = success = delivered) |
| Print styles hardcoded | termo_descarte.html is print template; colors need to be black/white on paper |

## Technical Details

### Standalone CSS Token Structure

```css
:root {
  --standalone-bg: hsl(210, 17%, 98%);
  --standalone-bg-light: hsl(0, 0%, 100%);
  --standalone-text: hsl(210, 11%, 15%);
  --standalone-text-muted: hsl(210, 7%, 46%);
  --standalone-primary: hsl(145, 63%, 42%);  /* Green brand */
  --standalone-secondary: hsl(162, 73%, 46%);
  /* ... status colors, gradients ... */
}

[data-bs-theme="dark"] {
  /* Dark mode overrides with teal-shifted greens */
}
```

### Template Migration Pattern

```html
<!-- Before -->
<html lang="pt-BR">
<style>
  body { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); }
</style>

<!-- After -->
<html lang="pt-BR" data-bs-theme="light">
<link rel="stylesheet" href="{{ url_for('static', filename='css/modules/_rastreamento-standalone.css') }}">
<style>
  body { background: linear-gradient(135deg, var(--standalone-primary) 0%, var(--standalone-secondary) 100%); }
</style>
```

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for:
- 06-10: Compras module migration
- 06-11: Remaining tier migrations
- 06-12: Final cleanup and verification
