---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality using Flask/Jinja2 template structure. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications. Generates creative, polished code and UI design that avoids generic AI aesthetics with mandatory light/dark mode support.
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

---

## DECISION TREE: Use Existing vs. Create New Design System

**BEFORE writing any CSS, answer these questions:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Does the screen belong to an EXISTING module with a design    │
│  system already in place?                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  YES ──► Use existing CSS/JS files                             │
│          Use existing class prefix (fin-*, cart-*, exp-*, etc) │
│          EXTEND, don't recreate                                │
│                                                                 │
│  NO  ──► Create NEW design system for the module               │
│          Choose unique class prefix                            │
│          Choose unique aesthetic direction                     │
│          Follow creation guidelines below                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Known Design Systems in This Project

| Module | Prefix | CSS Path | Aesthetic |
|--------|--------|----------|-----------|
| Financeiro | `fin-*` | `css/financeiro/extrato.css` | Industrial Financial + Monospace |
| [Add new modules here as created] | | | |

**If the module is in the table above**: USE EXISTING SYSTEM (see Module-Specific section below)

**If the module is NOT in the table**: CREATE NEW SYSTEM (see New Module Creation section)

---

## PART 1: Using Existing Design Systems

### 1A. Financial Module (`/financeiro/*`)

**Files:**
- CSS: `app/static/css/financeiro/extrato.css`
- JS: `app/static/js/financeiro/extrato.js`
- Prefix: `fin-*`

**Template:**
```jinja2
{% extends "base.html" %}

{% block title %}Page Title - Financeiro{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/financeiro/extrato.css') }}">
{% endblock %}

{% block content %}
<div class="fin-container">
    <header class="fin-header">
        <div>
            <h1 class="fin-header__title">
                <i class="fas fa-icon"></i>
                Título da Página
            </h1>
            <p class="fin-header__subtitle">Descrição breve</p>
        </div>
        <div class="fin-header__actions">
            <button class="theme-toggle" onclick="toggleTheme()" title="Alternar tema">
                <i class="fas fa-sun theme-toggle__icon theme-toggle__icon--light"></i>
                <i class="fas fa-moon theme-toggle__icon theme-toggle__icon--dark"></i>
            </button>
        </div>
    </header>
    <!-- Content using fin-* classes -->
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/financeiro/extrato.js') }}"></script>
{% endblock %}
```

**Available Components:**
| Component | Classes | Use Case |
|-----------|---------|----------|
| Container | `.fin-container` | Main wrapper |
| Header | `.fin-header`, `.fin-header__title` | Page header |
| Stats | `.fin-stats-grid`, `.fin-stat-card` | KPIs |
| Hub Cards | `.fin-hub-card`, `.fin-hub-grid` | Dashboard cards |
| Tables | `.fin-table`, `.fin-table-wrapper` | Data tables |
| Buttons | `.fin-btn--primary/success/ghost` | Actions |
| Forms | `.fin-input`, `.fin-form-group` | Form elements |

**Opções não implementadas**
<opcoes>
| Skeleton | `.fin-skeleton`, `.fin-skeleton--text/value/card/row` | Loading states |
| Timeline | `.fin-timeline`, `.fin-timeline__item` | History/events |
| Progress Ring | `.fin-progress-ring` | Circular KPIs |
| Toast | `.fin-toast`, `.fin-toast--success/warning/danger/info` | Notifications |
| Row Hover | `.fin-row-hover`, `.fin-row-selected` | Table row effects |
| Chips | `.fin-chip`, `.fin-chip--success/warning/danger/info` | Tags/labels |
| Empty State | `.fin-empty-state` | No data placeholder |
| Spinner | `.fin-spinner`, `.fin-spinner-dots` | Loading indicators |

**JavaScript Helpers (premium-effects.js):**
| Helper | Usage | Description |
|--------|-------|-------------|
| `FinToast.success(title, message)` | `FinToast.success('Sucesso!', 'Operação concluída')` | Show success toast |
| `FinToast.danger(title, message)` | `FinToast.error('Erro', 'Algo deu errado')` | Show error toast |
| `FinCounter.animate(el, value, opts)` | `FinCounter.animate(el, 1234, {prefix: 'R$ '})` | Animated number |
| `FinProgressRing.create(percent, opts)` | `FinProgressRing.create(75, {color: 'success'})` | Create SVG ring |
| `FinSkeleton.table(rows, cols)` | `FinSkeleton.table(5, 4)` | Table skeleton HTML |
| `FinTimeline.create(items)` | `FinTimeline.create([{time, title, status}])` | Timeline HTML |
| `FinChip.create(text, opts)` | `FinChip.create('Tag', {type: 'success'})` | Chip HTML |
</opcoes>
---

## PART 2: Creating New Design Systems

When creating a NEW module, follow these mandatory steps:

### Step 1: Choose Module Identity

**Define before coding:**

| Decision | Example Options |
|----------|----------------|
| **Module Name** | `inventory`, `reports`, `customers`, `settings` |
| **Class Prefix** | `inv-*`, `rpt-*`, `cust-*`, `set-*` |
| **Aesthetic Direction** | Minimal/Clean, Bold/Playful, Technical/Data, Warm/Friendly |
| **Primary Accent Color** | NOT GitHub blue (#58a6ff) |
| **Typography Personality** | Monospace-heavy, Sans-serif clean, Display fonts |

### Step 2: Create File Structure

```
app/static/
├── css/
│   └── [module]/
│       └── [module].css    # Main stylesheet
└── js/
    └── [module]/
        └── [module].js     # Module scripts
```

### Step 3: Define CSS Variables

```css
/* === [MODULE NAME] DESIGN SYSTEM === */
/* Aesthetic: [DESCRIBE YOUR AESTHETIC CHOICE] */

@import url('https://fonts.googleapis.com/css2?family=[YOUR+FONTS]&display=swap');

/* === DARK MODE (Default) === */
:root {
    /* Backgrounds - CHOOSE YOUR OWN, not GitHub's */
    --[prefix]-bg-primary: #[YOUR-DARK-BG];      /* NOT #0d1117 */
    --[prefix]-bg-secondary: #[YOUR-SECONDARY];
    --[prefix]-bg-tertiary: #[YOUR-TERTIARY];
    --[prefix]-bg-hover: #[YOUR-HOVER];

    /* Text */
    --[prefix]-text-primary: #[HIGH-CONTRAST];
    --[prefix]-text-secondary: #[MEDIUM];
    --[prefix]-text-muted: #[LOW];

    /* Accents - CHOOSE YOUR OWN PALETTE */
    --[prefix]-accent-primary: #[YOUR-PRIMARY];  /* NOT #58a6ff */
    --[prefix]-accent-success: #[YOUR-SUCCESS];
    --[prefix]-accent-warning: #[YOUR-WARNING];
    --[prefix]-accent-danger: #[YOUR-DANGER];

    /* Typography */
    --[prefix]-font-display: '[Your Display Font]', sans-serif;
    --[prefix]-font-mono: '[Your Mono Font]', monospace;

    /* Effects */
    --[prefix]-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
    --[prefix]-radius-lg: 12px;
    --[prefix]-transition: 250ms ease;
}

/* === LIGHT MODE === */
[data-theme="light"] {
    --[prefix]-bg-primary: #[LIGHT-BG];
    /* ... complete light mode palette */
}
```

### Step 4: Implement Signature Visual Moments

**MANDATORY: Include at least 2 of these:**

#### A. Atmospheric Background
```css
.[prefix]-container::before {
    content: '';
    position: fixed;
    top: -20%;
    right: -10%;
    width: 60%;
    height: 80%;
    background: radial-gradient(
        ellipse at 70% 30%,
        rgba([YOUR-ACCENT-RGB], 0.15) 0%,
        rgba([YOUR-SECONDARY-RGB], 0.08) 30%,
        transparent 60%
    );
    pointer-events: none;
    z-index: 0;
    animation: [prefix]-atmosphereFloat 20s ease-in-out infinite;
}
```

#### B. Entry Animations with Blur
```css
@keyframes [prefix]-heroEntry {
    0% {
        opacity: 0;
        transform: translateY(30px) scale(0.97);
        filter: blur(4px);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }
}
```

#### C. Progressive Glow Line on Hover
```css
.[prefix]-card::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--[prefix]-accent-primary), var(--[prefix]-accent-secondary));
    transition: width 0.4s ease;
}

.[prefix]-card:hover::after {
    width: 100%;
}
```

#### D. Multi-Layer Shadow Hover
```css
.[prefix]-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow:
        0 25px 50px rgba(0, 0, 0, 0.4),
        0 0 0 1px var(--[prefix]-accent-primary),
        0 0 40px rgba([YOUR-ACCENT-RGB], 0.12);
}
```

### Step 5: Base Template for New Module

```jinja2
{% extends "base.html" %}

{% block title %}Page Title - [Module]{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/[module]/[module].css') }}">
{% endblock %}

{% block content %}
<div class="[prefix]-container">
    <header class="[prefix]-header">
        <div>
            <h1 class="[prefix]-header__title">
                <i class="fas fa-icon"></i>
                Page Title
            </h1>
            <p class="[prefix]-header__subtitle">Description</p>
        </div>
        <div class="[prefix]-header__actions">
            <button class="theme-toggle" onclick="toggleTheme()">
                <i class="fas fa-sun theme-toggle__icon theme-toggle__icon--light"></i>
                <i class="fas fa-moon theme-toggle__icon theme-toggle__icon--dark"></i>
            </button>
        </div>
    </header>
    
    <!-- Module content -->
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/[module]/[module].js') }}"></script>
<script>
// Theme management
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

// Initialize theme
(function() {
    const saved = localStorage.getItem('theme');
    const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', saved || system);
})();
</script>
{% endblock %}
```

---

## PART 3: Universal Design Rules (ALL Modules)

### FORBIDDEN: GitHub Palette Clone

```css
/* ❌ NEVER USE THESE EXACT VALUES */
--bg: #0d1117;           /* GitHub Dark */
--accent: #58a6ff;       /* GitHub Blue */
--success: #3fb950;      /* GitHub Green */
--warning: #d29922;      /* GitHub Yellow */
--danger: #f85149;       /* GitHub Red */
```

**The Test**: If it looks like GitHub, you failed.

### REQUIRED: Typography Excellence

```css
/* Headers: Bold + Tight */
.[prefix]-title {
    font-weight: 700;
    letter-spacing: -0.02em;
}

/* Values: Large + Monospace */
.[prefix]-value {
    font-family: var(--[prefix]-font-mono);
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
}

/* Labels: Small Caps */
.[prefix]-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
```

### REQUIRED: Accessibility

```css
/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    .[prefix]-container::before,
    .[prefix]-container::after {
        animation: none;
    }
    
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

/* Focus visible */
.[prefix]-input:focus-visible {
    outline: 2px solid var(--[prefix]-accent-primary);
    outline-offset: 2px;
}
```

### REQUIRED: Light Mode Specific Design

```css
/* Light mode is NOT just inverted dark mode */
[data-theme="light"] {
    /* Accents need to be DARKER for contrast */
    --[prefix]-accent-primary: #[DARKENED-VERSION];
    
    /* Shadows need to be SOFTER */
    --[prefix]-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
    
    /* Backgrounds can have subtle warmth */
    --[prefix]-bg-primary: #fafbfc;
}
```

---

## PART 4: Aesthetic Direction Examples

Choose ONE direction and commit fully:

### A. Industrial/Technical (like Financial)
- Monospace for data
- Dark backgrounds
- Accent: Teal/Cyan (#00d4aa)
- Sharp corners (4-8px radius)
- Dense information display

### B. Clean/Minimal (for Settings, Admin)
- Sans-serif throughout
- Lots of white space
- Accent: Blue/Indigo (#6366f1)
- Rounded corners (12-16px radius)
- Single-purpose screens

### C. Warm/Friendly (for Customer-facing)
- Rounded, soft fonts
- Warm color temperature
- Accent: Orange/Amber (#f59e0b)
- Large radius (16-24px)
- Generous padding

### D. Data/Dashboard (for Reports, Analytics)
- Small, condensed typography
- High density grids
- Accent: Purple/Violet (#8b5cf6)
- Minimal radius (4px)
- Charts and visualizations

### E. Bold/Playful (for Marketing, Public)
- Display fonts for headers
- High contrast colors
- Accent: Pink/Magenta (#ec4899)
- Mixed radius (small buttons, large cards)
- Animations prominent

---

## PART 5: Quality Checklist

### Before Submitting ANY Frontend Code:

**Structure:**
- [ ] Uses correct decision (existing system vs. new)
- [ ] Files in correct location (`css/[module]/`, `js/[module]/`)
- [ ] Class prefix is unique to module

**Theming:**
- [ ] Dark mode complete
- [ ] Light mode complete (not just inverted)
- [ ] Theme toggle present and functional
- [ ] `prefers-color-scheme` respected on first visit
- [ ] Theme persists in localStorage

**Visual Quality:**
- [ ] NOT a GitHub clone (different colors)
- [ ] At least 2 signature visual moments
- [ ] Typography uses bold weights + tight spacing
- [ ] Atmospheric background effects (both modes)
- [ ] Staggered entry animations
- [ ] Dramatic hover states

**Accessibility:**
- [ ] `prefers-reduced-motion` respected
- [ ] WCAG AA contrast (4.5:1 text, 3:1 large text)
- [ ] Focus states visible
- [ ] Semantic HTML

**Responsive:**
- [ ] Works on mobile (768px)
- [ ] Works on small mobile (480px)
- [ ] Tables horizontally scrollable

---

## PART 6: Bootstrap Integration

### When to Use Bootstrap

| Situação | Recomendação |
|----------|--------------|
| Projeto já usa Bootstrap | ✅ Integrar com Bootstrap |
| Projeto novo, prazo curto | ⚠️ Bootstrap + Heavy customization |
| Projeto novo, design único | ❌ CSS custom puro (sem Bootstrap) |
| Componentes complexos (modals, dropdowns) | ✅ Bootstrap JS + Custom CSS |

### Integration Strategy: "Bootstrap as Foundation, Custom as Identity"

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Bootstrap Base                                        │
│  → Grid system (container, row, col-*)                         │
│  → Utility classes (d-flex, mt-3, text-center)                 │
│  → JS Components (Modal, Dropdown, Collapse)                   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: CSS Variable Override                                 │
│  → Bootstrap CSS variables overridden                          │
│  → Dark/Light mode via data-bs-theme + custom                  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: Custom Components                                     │
│  → [prefix]-* classes for unique components                    │
│  → Signature visual moments                                     │
│  → Module-specific styling                                      │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure with Bootstrap

```
app/static/
├── css/
│   ├── bootstrap-overrides.css    # Global Bootstrap customization
│   └── [module]/
│       └── [module].css           # Module-specific (loads AFTER bootstrap)
└── js/
    └── [module]/
        └── [module].js
```

### Bootstrap Variable Override (MANDATORY)

Create `bootstrap-overrides.css` loaded AFTER Bootstrap:

```css
/* ==========================================================================
   BOOTSTRAP OVERRIDES - Project Identity Layer
   Load this AFTER bootstrap.min.css
   ========================================================================== */

/* === PREVENT GITHUB-CLONE SYNDROME === */
/* Bootstrap 5.3+ uses CSS variables - override them ALL */

:root,
[data-bs-theme="light"] {
    /* Primary - NOT default Bootstrap blue (#0d6efd) */
    --bs-primary: #00d4aa;
    --bs-primary-rgb: 0, 212, 170;
    
    /* Secondary */
    --bs-secondary: #6366f1;
    --bs-secondary-rgb: 99, 102, 241;
    
    /* Success - NOT default Bootstrap green (#198754) */
    --bs-success: #10b981;
    --bs-success-rgb: 16, 185, 129;
    
    /* Warning */
    --bs-warning: #f59e0b;
    --bs-warning-rgb: 245, 158, 11;
    
    /* Danger */
    --bs-danger: #ef4444;
    --bs-danger-rgb: 239, 68, 68;
    
    /* Info */
    --bs-info: #0ea5e9;
    --bs-info-rgb: 14, 165, 233;
    
    /* Body */
    --bs-body-bg: #ffffff;
    --bs-body-color: #1f2328;
    
    /* Borders */
    --bs-border-color: rgba(31, 35, 40, 0.15);
    --bs-border-radius: 0.5rem;
    --bs-border-radius-lg: 0.75rem;
    
    /* Fonts - NEVER use default Bootstrap fonts */
    --bs-font-sans-serif: 'IBM Plex Sans', system-ui, sans-serif;
    --bs-font-monospace: 'JetBrains Mono', monospace;
}

[data-bs-theme="dark"] {
    /* Dark mode backgrounds - NOT GitHub colors */
    --bs-body-bg: #0a1628;
    --bs-body-color: #f0f6fc;
    --bs-secondary-bg: #111d2e;
    --bs-tertiary-bg: #1a2942;
    
    /* Borders in dark mode */
    --bs-border-color: rgba(240, 246, 252, 0.15);
    
    /* Adjust accent colors for dark mode contrast */
    --bs-primary: #00d4aa;
    --bs-link-color: #00d4aa;
}

/* === TYPOGRAPHY ENHANCEMENT === */
h1, h2, h3, .h1, .h2, .h3 {
    font-weight: 700;
    letter-spacing: -0.02em;
}

.display-1, .display-2, .display-3, .display-4 {
    font-weight: 700;
    letter-spacing: -0.03em;
}

/* === BUTTON ENHANCEMENT === */
.btn {
    font-weight: 500;
    letter-spacing: 0.01em;
    transition: all 0.25s ease, box-shadow 0.3s ease;
    position: relative;
    overflow: hidden;
}

/* Shine effect on buttons */
.btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.15),
        transparent
    );
    transition: left 0.5s ease;
}

.btn:hover::before {
    left: 100%;
}

.btn-primary:hover {
    box-shadow: 
        0 0 0 3px rgba(var(--bs-primary-rgb), 0.25),
        0 4px 15px rgba(var(--bs-primary-rgb), 0.3);
    transform: translateY(-1px);
}

/* === CARD ENHANCEMENT === */
.card {
    border: 1px solid var(--bs-border-color);
    transition: all 0.3s ease, box-shadow 0.4s ease;
    position: relative;
    overflow: hidden;
}

/* Progressive glow line */
.card::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--bs-primary), var(--bs-info));
    transition: width 0.4s ease;
}

.card:hover::after {
    width: 100%;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 
        0 20px 40px rgba(0, 0, 0, 0.15),
        0 0 0 1px var(--bs-primary);
}

[data-bs-theme="dark"] .card:hover {
    box-shadow: 
        0 20px 40px rgba(0, 0, 0, 0.4),
        0 0 0 1px var(--bs-primary),
        0 0 30px rgba(var(--bs-primary-rgb), 0.1);
}

/* === FORM ENHANCEMENT === */
.form-control:focus,
.form-select:focus {
    border-color: var(--bs-primary);
    box-shadow: 
        0 0 0 3px rgba(var(--bs-primary-rgb), 0.15),
        0 4px 12px rgba(var(--bs-primary-rgb), 0.1);
    transform: translateY(-1px);
}

/* === TABLE ENHANCEMENT === */
.table {
    --bs-table-hover-bg: rgba(var(--bs-primary-rgb), 0.05);
}

.table > tbody > tr {
    transition: all 0.2s ease;
    position: relative;
}

.table > tbody > tr:hover {
    box-shadow: inset 3px 0 0 var(--bs-primary);
}

/* === MODAL ENHANCEMENT === */
.modal-content {
    border: 1px solid var(--bs-border-color);
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
}

[data-bs-theme="dark"] .modal-content {
    background: var(--bs-secondary-bg);
}

/* === REDUCED MOTION === */
@media (prefers-reduced-motion: reduce) {
    .btn::before,
    .card::after {
        display: none;
    }
    
    .btn, .card, .form-control {
        transition: none !important;
        transform: none !important;
    }
}
```

### Template Structure with Bootstrap

```jinja2
{% extends "base.html" %}

{% block title %}Page Title - Module{% endblock %}

{% block extra_css %}
{# Bootstrap is loaded in base.html #}
{# Load overrides AFTER Bootstrap #}
<link rel="stylesheet" href="{{ url_for('static', filename='css/bootstrap-overrides.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/[module]/[module].css') }}">
{% endblock %}

{% block content %}
<div class="container-fluid [prefix]-container py-4">
    {# Use Bootstrap grid + custom component classes #}
    <div class="row">
        <div class="col-12">
            <header class="[prefix]-header d-flex justify-content-between align-items-start mb-4 pb-3 border-bottom">
                <div>
                    <h1 class="[prefix]-header__title h3 fw-bold mb-1">
                        <i class="fas fa-icon me-2 text-primary"></i>
                        Page Title
                    </h1>
                    <p class="[prefix]-header__subtitle text-secondary mb-0">Description</p>
                </div>
                <div class="[prefix]-header__actions d-flex gap-2">
                    <button class="btn btn-outline-secondary" onclick="toggleTheme()">
                        <i class="fas fa-sun theme-icon-light"></i>
                        <i class="fas fa-moon theme-icon-dark d-none"></i>
                    </button>
                </div>
            </header>
        </div>
    </div>
    
    {# Stats using Bootstrap grid + custom classes #}
    <div class="row g-3 mb-4">
        <div class="col-6 col-md-3">
            <div class="card [prefix]-stat-card h-100">
                <div class="card-body">
                    <div class="[prefix]-stat-card__value h2 fw-bold mb-1">1,234</div>
                    <div class="[prefix]-stat-card__label text-uppercase small text-secondary">Total Items</div>
                </div>
            </div>
        </div>
        {# More stat cards... #}
    </div>
    
    {# Data table with Bootstrap table + custom enhancements #}
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0 fw-semibold">Data Table</h5>
            <span class="badge bg-primary rounded-pill">100 items</span>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0 [prefix]-table">
                    <thead class="table-light">
                        <tr>
                            <th>Column 1</th>
                            <th>Column 2</th>
                        </tr>
                    </thead>
                    <tbody>
                        {# Table rows #}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/[module]/[module].js') }}"></script>
<script>
// Theme toggle - syncs with Bootstrap's data-bs-theme
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-bs-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    
    html.setAttribute('data-bs-theme', next);
    html.setAttribute('data-theme', next); // For custom CSS compatibility
    localStorage.setItem('theme', next);
    
    // Toggle icons
    document.querySelectorAll('.theme-icon-light').forEach(el => el.classList.toggle('d-none'));
    document.querySelectorAll('.theme-icon-dark').forEach(el => el.classList.toggle('d-none'));
}

// Initialize theme
(function() {
    const saved = localStorage.getItem('theme');
    const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const theme = saved || system;
    
    document.documentElement.setAttribute('data-bs-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    
    if (theme === 'dark') {
        document.querySelectorAll('.theme-icon-light').forEach(el => el.classList.add('d-none'));
        document.querySelectorAll('.theme-icon-dark').forEach(el => el.classList.remove('d-none'));
    }
})();
</script>
{% endblock %}
```

### Module-Specific CSS (WITH Bootstrap)

```css
/* ==========================================================================
   [MODULE] - Module-Specific Styles
   Works WITH Bootstrap, adds unique identity
   ========================================================================== */

/* === ATMOSPHERIC BACKGROUND === */
/* This is what makes it NOT look like generic Bootstrap */
.[prefix]-container {
    position: relative;
    min-height: calc(100vh - 56px);
}

.[prefix]-container::before {
    content: '';
    position: fixed;
    top: -20%;
    right: -10%;
    width: 60%;
    height: 80%;
    background: radial-gradient(
        ellipse at 70% 30%,
        rgba(var(--bs-primary-rgb), 0.08) 0%,
        rgba(var(--bs-info-rgb), 0.04) 30%,
        transparent 60%
    );
    pointer-events: none;
    z-index: 0;
    animation: [prefix]-atmosphereFloat 20s ease-in-out infinite;
}

@keyframes [prefix]-atmosphereFloat {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(20px, -20px) scale(1.05); }
}

/* === CUSTOM STAT CARDS === */
/* Extends Bootstrap .card with unique styling */
.[prefix]-stat-card {
    border-left: 4px solid var(--bs-primary);
    animation: [prefix]-fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

.[prefix]-stat-card:nth-child(1) { animation-delay: 0.1s; }
.[prefix]-stat-card:nth-child(2) { animation-delay: 0.15s; }
.[prefix]-stat-card:nth-child(3) { animation-delay: 0.2s; }
.[prefix]-stat-card:nth-child(4) { animation-delay: 0.25s; }

.[prefix]-stat-card__value {
    font-family: var(--bs-font-monospace);
    letter-spacing: -0.03em;
    color: var(--bs-primary);
}

.[prefix]-stat-card__label {
    letter-spacing: 0.5px;
}

/* === HEADER DECORATION === */
.[prefix]-header {
    position: relative;
    animation: [prefix]-slideIn 0.5s ease-out;
}

.[prefix]-header::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(
        90deg,
        var(--bs-primary) 0%,
        var(--bs-info) 40%,
        transparent 80%
    );
    opacity: 0.6;
}

/* === ENTRY ANIMATIONS === */
@keyframes [prefix]-fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px) scale(0.98);
        filter: blur(4px);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }
}

@keyframes [prefix]-slideIn {
    from {
        opacity: 0;
        transform: translateX(-30px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* === REDUCED MOTION === */
@media (prefers-reduced-motion: reduce) {
    .[prefix]-container::before {
        animation: none;
    }
    
    .[prefix]-stat-card,
    .[prefix]-header {
        animation: none;
    }
}
```

### Class Naming Convention with Bootstrap

| Use Case | Bootstrap Class | Custom Class | Combined |
|----------|----------------|--------------|----------|
| Container | `.container-fluid` | `.[prefix]-container` | `container-fluid [prefix]-container` |
| Cards | `.card` | `.[prefix]-stat-card` | `card [prefix]-stat-card` |
| Buttons | `.btn .btn-primary` | (use Bootstrap) | `btn btn-primary` |
| Tables | `.table .table-hover` | `.[prefix]-table` | `table table-hover [prefix]-table` |
| Forms | `.form-control` | (use Bootstrap) | `form-control` |
| Grid | `.row .col-*` | (use Bootstrap) | `row`, `col-md-6` |
| Spacing | `.mb-4 .py-3` | (use Bootstrap) | `mb-4 py-3` |
| Header | (custom) | `.[prefix]-header` | `[prefix]-header d-flex...` |

**Rule**: Use Bootstrap for STRUCTURE (grid, spacing, base components), use Custom for IDENTITY (colors, animations, unique components).

### Bootstrap Integration Checklist

- [ ] `bootstrap-overrides.css` created and loaded AFTER Bootstrap
- [ ] All `--bs-*` color variables overridden (NOT using Bootstrap defaults)
- [ ] `data-bs-theme` synced with `data-theme` for compatibility
- [ ] Custom atmospheric effects added (NOT default Bootstrap look)
- [ ] Cards have progressive glow line effect
- [ ] Buttons have shine effect
- [ ] Entry animations present (staggered)
- [ ] Reduced motion respected
- [ ] Typography enhanced (bold headers, monospace values)
- [ ] Module prefix used for custom components (`[prefix]-*`)

### The Bootstrap Test

**Before**: Generic Bootstrap site (looks like every Bootstrap template)

**After**: Bootstrap foundation with distinctive identity

**Question to ask**: "If I remove the Bootstrap classes, would this still have personality?"

If YES → You're using Bootstrap correctly
If NO → You're just using Bootstrap, not designing

---
```

---

## Resumo da Integração Bootstrap

### ✅ O Que Bootstrap PODE Fazer:
- Grid system (`container`, `row`, `col-*`)
- Utility classes (`d-flex`, `mb-4`, `text-center`)
- JavaScript components (Modal, Dropdown, Collapse)
- Base form styling (`form-control`, `form-select`)
- Base button structure (`.btn`)

### ✅ O Que a Skill ADICIONA:
- Override de TODAS as cores Bootstrap
- Atmospheric background effects
- Entry animations com blur
- Progressive glow lines
- Multi-layer shadow hovers
- Typography enhancement
- Module-specific identity

### ⚠️ Armadilhas a Evitar:

```css
/* ❌ NUNCA fazer isso */
.btn-primary {
    /* Usar cor padrão Bootstrap */
}

/* ✅ SEMPRE fazer isso */
:root {
    --bs-primary: #00d4aa; /* SUA cor, não Bootstrap */
}
```

---

## Compatibilidade

| Versão Bootstrap | Compatível | Notas |
|------------------|------------|-------|
| Bootstrap 5.3+ | ✅ Total | CSS Variables nativas |
| Bootstrap 5.0-5.2 | ⚠️ Parcial | Precisa mais overrides |
| Bootstrap 4.x | ⚠️ Limitada | Sem CSS Variables nativas |
| Bootstrap 3.x | ❌ Não | Arquitetura muito diferente |

**Recomendação**: Use Bootstrap 5.3+ para melhor integração com dark mode e CSS Variables.


## The Ultimate Test

**For EXISTING modules:**
> "Does this screen feel like it belongs to the same family?"

**For NEW modules:**
> "Would a senior designer be proud of this? Is it memorable?"

If either answer is "no" or "it's just functional" - you haven't finished.
```

---

## Principais Mudanças

### ✅ Generalização Aplicada:

| Antes | Depois |
|-------|--------|
| Financial como PRIORITY #1 | Decision tree genérico |
| Apenas `fin-*` exemplos | Template com `[prefix]` placeholder |
| Tabela de componentes só do financeiro | Estrutura para adicionar novos módulos |
| Palette examples hardcoded | Multiple aesthetic directions |
| Um único design system | Múltiplos design systems coexistindo |

### ✅ Novos Recursos:

1. **Decision Tree** - Clareza sobre quando usar existente vs. criar novo
2. **Aesthetic Directions** - 5 opções de "flavor" para diferentes módulos
3. **Module Registry** - Tabela para documentar design systems existentes
4. **File Structure Template** - Onde colocar arquivos de novos módulos
5. **Placeholder Syntax** - `[prefix]`, `[module]`, `[YOUR-*]` para customização

### ✅ Mantido:

- Todos os guidelines de qualidade
- Anti-patterns (GitHub clone)
- Signature visual moments
- Acessibilidade
- Checklist de qualidade

---

## Como Usar na Prática

**Cenário 1: Nova tela do financeiro**
```
Claude detecta: /financeiro/nova-tela
→ Usa PART 1: Financial Module
→ Aplica fin-* classes existentes
→ NÃO cria novo CSS
```

**Cenário 2: Novo módulo de inventário**
```
Claude detecta: /inventario/dashboard
→ Tabela não tem "inventário"
→ Usa PART 2: Creating New Design Systems
→ Escolhe prefix: inv-*
→ Escolhe aesthetic: Industrial/Technical
→ Cria css/inventario/inventario.css
→ Adiciona à tabela de módulos conhecidos
```

**Cenário 3: Nova tela de relatórios**
```
Claude detecta: /relatorios/vendas
→ Tabela não tem "relatórios"
→ Usa PART 2
→ Escolhe prefix: rpt-*
→ Escolhe aesthetic: Data/Dashboard
→ Palette diferente do financeiro (purple-based)
```

---

## 🎯 Resultado Esperado

Com essa skill refatorada:

1. ✅ **Financeiro preservado** - Continua usando `fin-*` sem alterações
2. ✅ **Outros módulos possíveis** - Estrutura clara para criar novos
3. ✅ **Consistência garantida** - Cada módulo segue mesmas regras de qualidade
4. ✅ **Diversidade permitida** - Módulos podem ter identidades visuais próprias
5. ✅ **Documentação automática** - Tabela de módulos cresce conforme projeto evolui

**A skill agora é um FRAMEWORK, não um template específico.**