# Phase 4: Layout Patterns - Research

**Researched:** 2026-01-27
**Domain:** CSS Layout, Responsive Grid, Sidebar Navigation
**Confidence:** HIGH

## Summary

Phase 4 addresses two remaining layout requirements: **LAYO-02** (sidebar adaptativa) and **LAYO-03** (grid system consistente). After thorough analysis of the codebase, the current system does NOT have a sidebar component - navigation is handled entirely via Bootstrap's top navbar with dropdowns. The primary layout pattern is `container-fluid` with Bootstrap's grid system (`row`/`col-*`), which is already working well.

The key finding is that this phase has **less scope than anticipated**. The system uses a navbar-based navigation pattern (no sidebar to make responsive), and Bootstrap's grid system is already the standard. The main work is:
1. Document the official layout pattern
2. Create a layout module CSS file for any custom layout utilities
3. Ensure no competing grid implementations exist
4. Add overflow protection for content areas

**Primary recommendation:** Create a minimal `_layout.css` component that documents patterns, adds responsive container utilities, and provides overflow protection - rather than implementing a sidebar that doesn't exist in the current design.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Bootstrap 5.3.3 | 5.3.3 | Grid system, containers, responsive utilities | Already standardized in Phase 1 |
| CSS Cascade Layers | native | Specificity control | Already established |
| CSS Custom Properties | native | Theme-aware values | Already established in tokens |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bootstrap Offcanvas | 5.3.3 | Drawer navigation (if sidebar needed) | Future mobile navigation enhancement |
| CSS Grid | native | Complex layouts beyond Bootstrap grid | Dashboard layouts, card grids |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bootstrap Grid | CSS Grid | CSS Grid is more powerful but Bootstrap grid is already consistent across templates |
| Custom sidebar | Bootstrap Offcanvas | Offcanvas adds complexity; current navbar works well |

## Architecture Patterns

### Recommended Project Structure
```
app/static/css/
├── components/
│   └── _layout.css      # NEW: Layout utilities and patterns
├── base/
│   ├── _navbar.css      # Already exists (navigation)
│   └── _bootstrap-overrides.css
└── main.css             # Entry point with @layer imports
```

### Pattern 1: Container Strategy
**What:** Consistent container usage across all templates
**When to use:** Every page layout

Current analysis shows two patterns in use:
- `container-fluid` (full width): Used in dashboards, data-heavy pages
- `container` (max-width centered): Used in forms, settings pages

```html
<!-- Full-width data pages -->
<div class="container-fluid">
    <div class="row">
        <div class="col-12"><!-- content --></div>
    </div>
</div>

<!-- Centered form pages -->
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-8"><!-- form --></div>
    </div>
</div>
```

### Pattern 2: Responsive Grid (Bootstrap Standard)
**What:** Mobile-first column system
**When to use:** All multi-column layouts

```html
<!-- Stats cards row -->
<div class="row mb-4">
    <div class="col-xl-3 col-md-6 mb-3"><!-- card --></div>
    <div class="col-xl-3 col-md-6 mb-3"><!-- card --></div>
    <div class="col-xl-3 col-md-6 mb-3"><!-- card --></div>
    <div class="col-xl-3 col-md-6 mb-3"><!-- card --></div>
</div>
```

### Pattern 3: Content Overflow Protection
**What:** Prevent horizontal overflow in content areas
**When to use:** Any container that may receive dynamic content

```css
.content-area {
    overflow-x: auto;
    max-width: 100%;
}
```

### Anti-Patterns to Avoid
- **Custom grid classes competing with Bootstrap:** Don't create `.custom-col-6` when `.col-6` exists
- **Fixed widths on content containers:** Use `max-width` instead of `width`
- **Hardcoded breakpoints in inline styles:** Use Bootstrap responsive classes or @media in CSS files
- **Overflow hidden without scrolling alternative:** Always provide scroll or wrap option

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Responsive columns | Custom col system | Bootstrap `col-*` classes | Bootstrap handles edge cases, tested cross-browser |
| Container widths | Custom containers | Bootstrap `.container-*` | Consistent breakpoints system-wide |
| Gutters | Manual padding | Bootstrap `g-*` classes | Gap utilities are responsive-ready |
| Mobile navigation | Custom hamburger drawer | Bootstrap Offcanvas | JS interactions, accessibility built-in |
| Flex layouts | Custom flex classes | Bootstrap `d-flex`, `flex-*` | Already available, consistent |

**Key insight:** Bootstrap 5.3.3 already provides comprehensive layout utilities. The goal is standardization and documentation, not creation of new systems.

## Common Pitfalls

### Pitfall 1: Overflow Breaking Table Scroll
**What goes wrong:** Parent container with `overflow: hidden` prevents table horizontal scroll
**Why it happens:** Attempting to contain content, accidentally clips scrollable children
**How to avoid:** Use `overflow-x: auto` on `.table-responsive` wrapper, not on parent containers
**Warning signs:** Tables cut off on mobile despite `.table-responsive` class

### Pitfall 2: Competing Container Widths
**What goes wrong:** Content has unexpected width constraints
**Why it happens:** Multiple nested containers each applying max-width
**How to avoid:** Single container at page level, internal divs use full width
**Warning signs:** Content narrower than viewport on desktop

### Pitfall 3: Z-index Conflicts with Navbar
**What goes wrong:** Dropdowns, modals, or sticky elements appear under navbar
**Why it happens:** Navbar z-index (1030) conflicts with other positioned elements
**How to avoid:** Document z-index scale: modals (1055) > offcanvas (1045) > navbar (1030) > sticky (1020)
**Warning signs:** Elements disappearing behind other elements on scroll

### Pitfall 4: Grid Breakpoint Inconsistency
**What goes wrong:** Layout breaks at unexpected screen sizes
**Why it happens:** Mixing Bootstrap breakpoints (sm, md, lg) inconsistently
**How to avoid:** Standard pattern: `col-xl-3 col-md-6 mb-3` for 4-column cards
**Warning signs:** Columns stacking at wrong viewport widths

## Code Examples

### Container and Grid (verified Bootstrap 5.3.3 pattern)
```html
<!-- Source: Bootstrap 5.3 documentation -->
<div class="container-fluid">
    <div class="row mb-4">
        <div class="col-12">
            <h1 class="h3 mb-0">Page Title</h1>
        </div>
    </div>
    <div class="row g-3">
        <div class="col-xl-3 col-md-6">
            <div class="card h-100"><!-- card content --></div>
        </div>
    </div>
</div>
```

### Layout CSS Module (proposed)
```css
@layer components {
/* ═══════════════════════════════════════════════════════════════
   LAYOUT - Page structure and containers
   ═══════════════════════════════════════════════════════════════ */

/* Content area overflow protection */
.nc-content {
    overflow-x: auto;
    max-width: 100%;
}

/* Full-height page layout */
.nc-page {
    min-height: calc(100vh - 56px); /* Account for navbar height */
    display: flex;
    flex-direction: column;
}

.nc-page-content {
    flex: 1;
}

/* Z-index scale documentation */
/*
   1055 - Modals
   1050 - Modal backdrop
   1045 - Offcanvas
   1040 - Offcanvas backdrop
   1030 - Navbar (fixed)
   1020 - Sticky elements
   1010 - Table sticky headers
   1000 - Dropdowns
*/

} /* End @layer components */
```

### Responsive Offcanvas (if future sidebar needed)
```html
<!-- Source: Bootstrap 5.3 documentation -->
<button class="btn btn-primary d-lg-none"
        type="button"
        data-bs-toggle="offcanvas"
        data-bs-target="#sidebarOffcanvas">
    <i class="fas fa-bars"></i>
</button>

<div class="offcanvas-lg offcanvas-start"
     tabindex="-1"
     id="sidebarOffcanvas">
    <div class="offcanvas-header">
        <h5>Navigation</h5>
        <button type="button" class="btn-close" data-bs-dismiss="offcanvas"></button>
    </div>
    <div class="offcanvas-body">
        <!-- sidebar content -->
    </div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed sidebar | Responsive offcanvas | Bootstrap 5.2 | Better mobile UX |
| Float-based grids | Flexbox/Grid | Bootstrap 4→5 | Simpler, more reliable |
| jQuery layout plugins | CSS-only solutions | 2020+ | Better performance |
| Viewport units vh | Dynamic viewport dvh | 2023 | Mobile address bar handling |

**Deprecated/outdated:**
- `.row > .col-*` with negative margins for gutters (now use gap utilities)
- Fixed-width sidebar in pixels (use responsive units or offcanvas)

## Codebase Analysis

### Current Layout Situation

**Navigation Pattern:** Top navbar only (no sidebar)
- `app/templates/base.html` line 35-620: Navbar with dropdown menus
- Mobile: Collapses to hamburger menu using Bootstrap collapse
- No sidebar implementation exists

**Container Usage (328 occurrences across templates):**
- `container-fluid`: Majority of pages (dashboards, lists, data views)
- `container`: Forms, authentication pages, settings

**Grid Classes (from analysis):**
- Standard Bootstrap patterns: `col-xl-3 col-md-6`, `col-12`, `col-md-8`
- Consistent breakpoint strategy already in place
- No competing custom grid implementations found

**Existing CSS Grid Usage:**
- `app/static/css/financeiro/extrato.css`: Uses CSS Grid for card layouts
- `app/static/css/modules/`: Flex-based layouts, no grid conflicts
- Pattern: `repeat(auto-fit, minmax(160px, 1fr))` for responsive cards

### Templates Analyzed
- `base.html`: Main layout structure
- `main/dashboard.html`: Full-width with stat cards
- `carteira/dashboard.html`: Full-width with action buttons
- 106 total templates use consistent `container-fluid` or `container`

## Requirements Interpretation

### LAYO-02: Sidebar adaptativa ao tamanho de tela
**Analysis:** The system does NOT have a sidebar. Navigation is navbar-based.
**Recommendation:** Mark as N/A or reinterpret as "navigation adapts to screen size" - which already works via Bootstrap collapse.
**Alternative:** If sidebar is actually needed in future, use Bootstrap Offcanvas pattern.

### LAYO-03: Grid system consistente em todas as telas
**Analysis:** Bootstrap grid IS already consistent. No competing implementations found.
**Recommendation:** Document the standard pattern, create layout utilities file for future extensions.

## Open Questions

1. **Should we implement a sidebar?**
   - What we know: Current design uses navbar dropdowns, which works
   - What's unclear: Whether stakeholders want a sidebar navigation style
   - Recommendation: Treat as N/A for v1, can add via Offcanvas in v2

2. **dvh units for mobile**
   - What we know: Dynamic viewport units handle mobile address bar better
   - What's unclear: Browser support for older devices in user base
   - Recommendation: Use `min-height: 100vh` as fallback, `min-height: 100dvh` if supported (97%+ support in 2026)

## Scope Recommendation

**Minimal Phase 4 Scope:**
1. Create `_layout.css` component file (documentation + utilities)
2. Document z-index scale
3. Add content overflow protection utilities
4. Verify no layout regressions in templates
5. Update REQUIREMENTS.md to clarify LAYO-02 interpretation

**NOT in scope:**
- Creating a sidebar (doesn't exist in current design)
- Changing navigation pattern (navbar works well)
- Replacing Bootstrap grid with CSS Grid (Bootstrap is standard)

## Sources

### Primary (HIGH confidence)
- Bootstrap 5.3 Documentation - Layout/Grid: https://getbootstrap.com/docs/5.3/layout/grid
- Bootstrap 5.3 Documentation - Containers: https://getbootstrap.com/docs/5.3/layout/containers
- Bootstrap 5.3 Documentation - Offcanvas: https://getbootstrap.com/docs/5.3/components/offcanvas
- Context7 /websites/getbootstrap_5_3 - queried for grid, containers, responsive patterns

### Secondary (MEDIUM confidence)
- MDN CSS Grid Layout: https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout/Common_grid_layouts
- Codebase analysis of 106 templates and CSS files

### Tertiary (LOW confidence)
- WebSearch for CSS layout best practices 2026 (used for validation, not primary source)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Bootstrap 5.3.3 already standardized in Phase 1
- Architecture: HIGH - Patterns observed directly from codebase analysis
- Pitfalls: MEDIUM - Based on common issues, not codebase-specific bugs

**Research date:** 2026-01-27
**Valid until:** 60 days (stable patterns, no rapid changes expected)
