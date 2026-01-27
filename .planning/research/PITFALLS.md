# CSS Migration Pitfalls

**Domain:** CSS Design System Migration (Inline Styles to Design Tokens)
**Project Context:** Flask/Jinja2 freight system with 102+ templates, Bootstrap 5, dark mode
**Researched:** 2026-01-26
**Confidence:** HIGH (based on project analysis + industry patterns)

---

## Critical Pitfalls

Mistakes that cause rewrites, regressions, or project failure.

---

### Pitfall 1: The Big Bang Migration

**What goes wrong:** Attempting to migrate all 102 templates simultaneously, replacing all inline styles in one massive refactor.

**Why it happens:**
- Desire to "clean up everything at once"
- Underestimating the scope (this project has 1,280+ inline style occurrences across 233 files)
- Previous failed attempt suggests this was tried before

**Consequences:**
- Visual regressions across entire application
- QA nightmare - impossible to test all screens
- Rollback becomes all-or-nothing
- Team loses confidence in migration

**Warning signs:**
- PRs touching 50+ templates at once
- "Let's just replace all the inline styles this weekend"
- No visual regression testing in place

**Prevention:**
1. **Migrate incrementally** - one module/feature at a time
2. **Establish migration order** based on traffic and criticality
3. **Create a "migration complete" checklist** per template
4. **Never migrate without visual regression tests** in place first

**Phase to address:** Phase 1 (Foundation) - establish incremental strategy before any template work

---

### Pitfall 2: The `!important` Cascade

**What goes wrong:** Using `!important` to override Bootstrap styles leads to a chain reaction requiring more `!important` declarations to override your own overrides.

**Why it happens:**
- Bootstrap 5 has high specificity in many places
- Quick fix mentality: "just add `!important` to make it work"
- Current codebase already has 591 `!important` declarations across 14 CSS files

**Consequences:**
- CSS becomes increasingly difficult to override
- Specificity wars escalate
- Dark mode overrides become fragile
- New features require even more `!important`

**Warning signs (currently present in project):**
```css
/* From _design-tokens.css - already has 89 !important */
.btn-primary {
    background: var(--amber-55) !important;
    color: hsl(0 0% 10%) !important;
    border: none !important;
}
```
- Every new component needs `!important` to work
- Styles only work in specific load orders

**Prevention:**
1. **Use CSS `@layer`** to control cascade order without `!important`
   ```css
   @layer bootstrap, tokens, components, utilities;
   ```
2. **Leverage Bootstrap's CSS custom properties** instead of overriding classes
3. **Increase selector specificity strategically** rather than using `!important`
4. **Audit and reduce existing `!important` usage** before adding more

**Phase to address:** Phase 1 (Foundation) - implement `@layer` before component migration

---

### Pitfall 3: Dark Mode Regression - The "FOWT" Problem

**What goes wrong:** Users see "Flash of Wrong Theme" (FOWT) where the page briefly shows the wrong theme before JavaScript corrects it.

**Why it happens:**
- Theme stored in localStorage, applied via JavaScript
- CSS loads before JavaScript executes
- Server-side rendering doesn't know user's theme preference

**Consequences:**
- Jarring visual experience on every page load
- Professional appearance suffers
- Users may think site is broken

**Warning signs:**
- Project already has flash prevention script in `base.html`:
  ```html
  <script>
    (function() {
      var saved = localStorage.getItem('nacom-theme');
      var theme = saved || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
      document.documentElement.setAttribute('data-bs-theme', theme);
    })();
  </script>
  ```
- But inline styles don't respect theme variables, causing partial flash

**Prevention:**
1. **Ensure flash-prevention script runs BEFORE CSS loads** (already done)
2. **Never use hardcoded colors** - always use CSS variables
3. **Test theme toggle without network cache** (hard refresh)
4. **Replace inline styles with classes** that use CSS variables

**Phase to address:** All phases - every template migration must verify dark mode

---

### Pitfall 4: Bootstrap Specificity Conflicts

**What goes wrong:** Custom CSS doesn't apply because Bootstrap's specificity is higher, or Bootstrap updates break custom overrides.

**Why it happens:**
- Bootstrap uses multiple classes and element selectors
- Custom CSS often uses single class selectors
- Load order matters: custom CSS must come after Bootstrap

**Consequences:**
- Styles appear to "not work" randomly
- Same class behaves differently in different contexts
- Debugging becomes time-consuming

**Warning signs:**
- DevTools shows custom CSS crossed out
- Styles work in isolation but not in templates
- Need to add classes like `.my-app .my-component` for specificity

**Current evidence from project:**
```css
/* bootstrap-overrides.css - battling Bootstrap specificity */
.table > thead th {
    background: var(--bg-light) !important;
    color: var(--text) !important;
    /* ... */
}
```

**Prevention:**
1. **Load order matters:** Bootstrap CSS → Design Tokens → Component CSS → Utilities
2. **Use Bootstrap's CSS custom properties** where possible:
   ```css
   :root {
     --bs-body-bg: var(--bg-dark);
     --bs-body-color: var(--text);
   }
   ```
3. **Match Bootstrap's selector structure** when overriding
4. **Consider using `@layer`** to control cascade without specificity battles

**Phase to address:** Phase 1 (Foundation) - establish correct load order and layer structure

---

### Pitfall 5: Inline Style Override Brittleness

**What goes wrong:** Inline styles in HTML have highest specificity and cannot be overridden by CSS classes without `!important` or JavaScript.

**Why it happens:**
- Legacy code uses inline styles for "quick fixes"
- Dynamic values generated in Python/Jinja2
- Copy-paste from external examples

**Evidence from project:**
```css
/* bootstrap-overrides.css - attempting to override inline styles */
.badge[style*="background-color: #28a745"] {
    background-color: var(--semantic-success) !important;
}
```
This selector targets elements with specific inline styles - a fragile workaround.

**Consequences:**
- Dark mode doesn't work for inline-styled elements
- Consistent theming impossible
- CSS file grows with attribute selectors

**Warning signs:**
- 1,280 `style=` occurrences in templates
- CSS contains `[style*="..."]` selectors
- Theme toggle leaves some elements unchanged

**Prevention:**
1. **Extract inline styles to CSS classes** (primary migration work)
2. **For dynamic values, use CSS custom properties:**
   ```html
   <!-- Instead of: -->
   <div style="width: {{ percent }}%">

   <!-- Use: -->
   <div style="--progress: {{ percent }}%" class="progress-bar">
   ```
   ```css
   .progress-bar { width: var(--progress); }
   ```
3. **Create utility classes** for common inline patterns
4. **Audit templates for hardcoded colors** before migration

**Phase to address:** Phase 2+ (Component Migration) - systematic template review

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or maintenance burden.

---

### Pitfall 6: Token Naming Inconsistency

**What goes wrong:** Different naming conventions across tokens create confusion and misuse.

**Why it happens:**
- Multiple developers, different naming preferences
- Evolution over time without refactoring
- Copy-paste from different sources

**Evidence from project's `_design-tokens.css`:**
```css
/* Inconsistent naming patterns */
--bg-dark: ...       /* Semantic: purpose-based */
--gray-50: ...       /* Primitive: value-based */
--amber-55: ...      /* Brand: color + lightness */
--semantic-success:  /* Prefixed category */
```

**Prevention:**
1. **Document naming convention** before adding tokens
2. **Use three-tier structure:** primitives → semantic → component
   ```css
   /* Tier 1: Primitives (never use directly in components) */
   --color-gray-800: hsl(0 0% 8%);

   /* Tier 2: Semantic (use in components) */
   --color-bg-surface: var(--color-gray-800);

   /* Tier 3: Component (optional, specific overrides) */
   --card-bg: var(--color-bg-surface);
   ```
3. **Lint for direct primitive usage** in component CSS

**Phase to address:** Phase 1 (Foundation) - establish naming convention in style guide

---

### Pitfall 7: Mobile Responsiveness Regression

**What goes wrong:** Migrated components break on mobile devices - tables overflow, buttons get cut off on iPhone.

**Why it happens:**
- Desktop-first development
- Inline styles often include fixed widths
- Bootstrap responsive classes removed during "cleanup"

**Project context:** Mobile responsiveness issues explicitly mentioned as current problem

**Warning signs:**
- Tables horizontal scroll not working
- Touch targets too small
- Content cut off on small screens

**Prevention:**
1. **Test on real devices** during migration, not just DevTools
2. **Preserve Bootstrap responsive classes** (`.table-responsive`, breakpoint utilities)
3. **Use relative units** (`rem`, `%`, `vw`) not fixed pixels
4. **Create mobile-specific utility classes:**
   ```css
   /* Already exists in project */
   @media (max-width: 768px) {
     .table-mobile-stack td {
       display: block;
       text-align: right;
     }
   }
   ```
5. **iPhone-specific testing:** Safari has unique scrolling behavior

**Phase to address:** Phase 2 (Component Migration) - include mobile testing in acceptance criteria

---

### Pitfall 8: Missing Print Styles

**What goes wrong:** Print functionality breaks after CSS migration because print styles weren't updated.

**Evidence from project:** Print styles exist but are minimal:
```css
@media print {
    body {
        background: white !important;
        color: black !important;
    }
    /* ... */
}
```

**Project has print-heavy templates:**
- `embarques/imprimir_completo.html` (62 style occurrences)
- `embarques/imprimir_embarque.html` (45 style occurrences)
- `embarques/imprimir_separacao.html` (24 style occurrences)

**Prevention:**
1. **Audit print templates** before CSS changes
2. **Test print preview** after each template migration
3. **Use `@media print` in component CSS**, not just global
4. **Preserve inline styles for print** if they're intentional for PDF generation

**Phase to address:** Phase 3 (Polish) - dedicated print stylesheet review

---

### Pitfall 9: CSS Variable Fallback Neglect

**What goes wrong:** CSS variables without fallbacks cause invisible elements in edge cases.

**Why it happens:**
- Variables not defined in all contexts
- Older browsers don't support CSS variables
- JavaScript theme setting hasn't run yet

**Consequences:**
- White text on white background
- Missing borders
- Invisible buttons

**Prevention:**
1. **Always provide fallbacks** for critical visual properties:
   ```css
   .button {
     background: var(--bg-button, #262626);
     color: var(--text, #f2f2f2);
   }
   ```
2. **Define variables on `:root`** not just `[data-theme]`
3. **Test with CSS variables disabled** in DevTools

**Phase to address:** Phase 1 (Foundation) - add fallbacks during token audit

---

### Pitfall 10: Third-Party Library Conflicts

**What goes wrong:** Libraries like DataTables, Toastr, or Select2 don't respect your design tokens.

**Project uses:**
- Bootstrap 5.3.2
- Toastr
- jQuery Mask
- HTMX

**Warning signs:**
- Library components look "off" after migration
- Modals or dropdowns have wrong colors
- Third-party CSS loaded after custom CSS

**Prevention:**
1. **Audit all third-party CSS** in `base.html`
2. **Create override styles** for each library:
   ```css
   /* toastr overrides */
   .toast {
     background: var(--bg-light) !important;
     color: var(--text) !important;
   }
   ```
3. **Load third-party CSS before custom CSS**
4. **Pin library versions** to prevent surprise updates

**Phase to address:** Phase 2 (Component Migration) - create library override file

---

## Minor Pitfalls

Mistakes that cause annoyance but are easily fixable.

---

### Pitfall 11: Orphaned CSS Rules

**What goes wrong:** CSS rules remain after HTML is updated, bloating stylesheets.

**Prevention:**
- Use CSS coverage tools (Chrome DevTools)
- Run PurgeCSS in build process
- Document which templates use which CSS files

**Phase to address:** Phase 3 (Polish) - CSS audit and cleanup

---

### Pitfall 12: Inconsistent Border Radius

**What goes wrong:** Some components use `4px`, others use `0.5rem`, others use tokens.

**Current evidence:**
```css
--radius-sm: 0.25rem;
--radius-md: 0.5rem;
--radius-lg: 1rem;
```

**Prevention:**
- Enforce token usage via stylelint
- Search and replace hardcoded values
- Create utility classes: `.rounded-sm`, `.rounded-md`, `.rounded-lg`

**Phase to address:** Phase 2 (Component Migration) - enforce during template review

---

### Pitfall 13: Comment and Documentation Drift

**What goes wrong:** CSS comments become outdated as code evolves.

**Evidence:** `_design-tokens.css` has extensive comments that may drift:
```css
/*  HIERARQUIA DE LUMINOSIDADE (4 TONS DISTINTOS):
    - body:    --bg-dark   (0% dark / 90% light)
    ...
*/
```

**Prevention:**
- Update comments when updating code
- Keep documentation minimal but accurate
- Use self-documenting variable names

**Phase to address:** All phases - enforce during code review

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Foundation | `!important` escalation, load order issues | Implement `@layer`, audit existing `!important`, document cascade strategy |
| Token System | Naming inconsistency, missing fallbacks | Define naming convention upfront, add fallbacks to all tokens |
| Component Migration | Breaking mobile, breaking print, inline style residue | Test on real devices, check print preview, systematic template review |
| Dark Mode | FOWT, hardcoded colors missed | Preserve flash-prevention script, audit for `#hex` values in templates |
| Polish | Orphaned CSS, third-party conflicts | Run coverage tools, audit library overrides |

---

## Pre-Migration Checklist

Before starting any CSS migration work:

- [ ] Establish CSS load order in `base.html`
- [ ] Implement `@layer` for cascade control
- [ ] Document token naming convention
- [ ] Set up visual regression testing
- [ ] Audit critical templates for inline style count
- [ ] Test current dark mode toggle behavior
- [ ] Document print-critical templates
- [ ] List all third-party CSS dependencies

---

## Sources

- [CSS Variables Pitfalls](https://blog.pixelfreestudio.com/css-variables-gone-wrong-pitfalls-to-watch-out-for/)
- [Bootstrap 5 CSS Variables](https://getbootstrap.com/docs/5.3/customize/css-variables/)
- [Specificity Wars](https://blog.pixelfreestudio.com/the-hidden-dangers-of-css-specificity-wars/)
- [CSS Refactoring Legacy Code](https://tryhoverify.com/blog/theres-nothing-more-painful-than-refactoring-legacy-css/)
- [Design System Migration Lessons](https://dev.to/victorandcode/lessons-from-migrating-a-web-application-to-a-design-system-2701)
- [Dark Mode Best Practices 2025](https://medium.com/design-bootcamp/the-ultimate-guide-to-implementing-dark-mode-in-2025-bbf2938d2526)
- [Bootstrap Override Best Practices](https://themeselection.com/override-bootstrap-css-styles/)
- Project analysis: `/home/rafaelnascimento/projetos/frete_sistema/app/static/css/_design-tokens.css`
- Project analysis: `/home/rafaelnascimento/projetos/frete_sistema/app/templates/base.html`
