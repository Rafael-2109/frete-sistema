---
name: frontend-design
description: >-
  Esta skill deve ser usada quando o usuario precisa "criar tela de...",
  "montar dashboard", "componente web", "interface com Flask/Jinja2", ou
  construir artefatos visuais com design profissional. Gera paginas com
  suporte obrigatorio light/dark mode e estetica nao-generica.
  Nao usar para modificar CSS existente sem criar tela (editar diretamente),
  criar skill (usar skill-creator), ou gerar PRD (usar prd-generator).
  Triggers em portugues: "crie uma tela de...", "monte um dashboard",
  "painel de controle", "tela de cadastro", "tela de listagem",
  "layout com sidebar", "pagina de configuracoes", "quero um layout Jinja2",
  ou qualquer pedido para construir novo HTML/CSS do zero.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Create distinctive frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details.

## Quick Reference

**CSS Variables Reference**: See [references/css-variables.md](references/css-variables.md) for complete list of all CSS variables (`--bs-*`, `--fin-*`, `--agent-*`).

**Premium Effects Reference**: See [references/premium-effects.md](references/premium-effects.md) for aurora background, scroll reveal, and other premium visual effects.

## Decision Tree

```
Does the screen belong to an EXISTING module?
│
├─ YES → Use existing CSS/JS files
│        Use existing class prefix (fin-*, cart-*, exp-*, etc.)
│        EXTEND, don't recreate
│        CHECK css-variables.md for EXACT variable names to reuse
│
└─ NO  → Create NEW design system
         Choose unique class prefix
         Follow creation guidelines below
```

## Known Design Systems

| Module | Prefix | CSS File | Reference |
|--------|--------|----------|-----------|
| **Sistema (Bootstrap)** | `--bs-*` | `css/bootstrap-overrides.css` | [css-variables.md#1](references/css-variables.md#1-bootstrap-overrides---bs-) |
| **Financeiro** | `--fin-*` | `css/financeiro/extrato.css` | [css-variables.md#2](references/css-variables.md#2-financeiro---fin-) |
| **Agente** | `--agent-*` | `agente/css/agent-theme.css` | [css-variables.md#3](references/css-variables.md#3-agente---agent-) |

## MANDATORY Deliverables

**EVERY request MUST produce BOTH files:**
1. **Template** (`.html`) — Jinja2 extending `base.html`
2. **CSS** (`.css`) — Module stylesheet with scoped prefix

Never deliver only one. If creating a new design system, deliver BOTH the CSS tokens AND a template example using them.

## Using Existing Systems

### Template Structure (with Premium Effects)

```jinja2
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/[module]/[module].css') }}">
{% endblock %}

{% block content %}
<div class="container-fluid premium-page">
    <header class="page-header reveal">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1 class="h3 mb-0">
                    <i class="fas fa-icon text-primary me-2"></i>
                    Título
                </h1>
                <small class="text-muted">Subtítulo</small>
            </div>
        </div>
    </header>

    <!-- Use stagger-children for animated card grids -->
    <div class="row g-3 stagger-children">
        <!-- Cards here get staggered entry animation automatically -->
    </div>
</div>
{% endblock %}
```

**Key classes (from base.html — MUST use these, never recreate):**
- `premium-page` → Auto-injects aurora background (centralized in base.html)
- `reveal` → Scroll reveal animation for headers/sections
- `stagger-children` → Staggered entry animation for child elements (cards, rows)

**NEVER recreate stagger/reveal effects with custom CSS**. The base.html already provides these via centralized JS. Using `stagger-children` on a container automatically staggers all direct children.

For complete premium effects guide: [references/premium-effects.md](references/premium-effects.md)

### Essential Patterns

**Card:**
```css
.my-card {
    background: var(--bs-secondary-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 12px;
}
```

**Table:**
```css
.table-container thead th {
    background: var(--bs-tertiary-bg);
    color: var(--bs-secondary-color);
}
```

**For complete patterns**: See [css-variables.md#6](references/css-variables.md#6-padrões-de-componentes)

### Reusing Existing Module Variables

When building for an existing module (e.g., Financeiro), **reuse its documented variables by exact name**:

```css
/* ✅ CORRECT — Reuse documented financial variables */
.my-status { background: var(--fin-bg-success); }
.my-badge  { color: var(--fin-conciliado-color); }

/* ❌ WRONG — Inventing new variables for the same purpose */
.my-status { background: var(--conc-success-bg); }
```

**Before writing CSS for an existing module**, open [references/css-variables.md](references/css-variables.md) and search for the module's prefix to find all available variables. Do NOT invent new variable names when existing ones cover the same purpose.

## Creating New Systems

### Step 1: Define Identity

| Decision | Options |
|----------|---------|
| **Module Name** | `inventory`, `reports`, `customers` |
| **Class Prefix** | `inv-*`, `rpt-*`, `cust-*` |
| **Aesthetic** | Industrial, Clean, Warm, Data-dense, Bold |

### Step 2: CSS Variables Template

```css
/* === [MODULE] DESIGN SYSTEM === */

/* Dark mode (default) */
:root {
    /* Backgrounds */
    --[prefix]-bg-primary: #0a1628;
    --[prefix]-bg-secondary: #111d2e;
    --[prefix]-bg-tertiary: #1a2942;

    /* Texto */
    --[prefix]-text-primary: #f0f6fc;
    --[prefix]-text-secondary: #8b949e;

    /* Acentos */
    --[prefix]-accent-primary: #00d4aa;
    --[prefix]-accent-success: #10b981;
    --[prefix]-accent-warning: #f59e0b;
    --[prefix]-accent-danger: #ef4444;
}

/* Light mode — NOT just inversion, different tones */
[data-bs-theme="light"],
[data-theme="light"] {
    --[prefix]-bg-primary: #f5f7fa;
    --[prefix]-bg-secondary: #ffffff;
    /* ... all overrides with intentionally different values */
}
```

**IMPORTANT**: Hex values are allowed ONLY inside `:root` and `[data-bs-theme]` variable definitions. All element styles MUST use `var()` references.

### Step 3: Signature Visual Moments (pick 2+)

**A. Atmospheric Background:**
```css
.[prefix]-container::before {
    content: '';
    position: fixed;
    background: radial-gradient(
        ellipse at 70% 30%,
        rgba(var(--bs-primary-rgb), 0.08) 0%,
        transparent 60%
    );
    pointer-events: none;
}
```

**B. Entry Animation:**
```css
@keyframes [prefix]-fadeIn {
    from { opacity: 0; transform: translateY(20px); filter: blur(4px); }
    to { opacity: 1; transform: translateY(0); filter: blur(0); }
}
```

**C. Progressive Glow Line:**
```css
.[prefix]-card::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0;
    width: 0; height: 3px;
    background: linear-gradient(90deg, var(--[prefix]-accent-primary), var(--[prefix]-accent-info));
    transition: width 0.4s ease;
}
.[prefix]-card:hover::after { width: 100%; }
```

**Note**: Even in gradient stops, use `var()` references to your custom variables — not raw hex.

## Quality Checklist

- [ ] **Template** extends `base.html` with `{% block extra_css %}` (NOT `{% block head %}`)
- [ ] **CSS file** created with scoped prefix (NOT inline `<style>` in template)
- [ ] Uses CSS variables in elements (NOT hex colors — including gradient stops)
- [ ] Dark mode complete
- [ ] Light mode complete (NOT just inverted — different tones)
- [ ] `premium-page` class on main container
- [ ] `reveal` class on header/sections
- [ ] `stagger-children` on card grids/rows (NOT custom nth-child stagger)
- [ ] At least 2 signature visual moments
- [ ] `@media (prefers-reduced-motion: reduce)` disabling all animations
- [ ] Brazilian formatting: `valor_br`, `numero_br` filters (NOT raw JS formatting)
- [ ] WCAG AA contrast (4.5:1)

## FORBIDDEN

```css
/* ❌ NEVER USE IN ELEMENTS */
background: #343541;           /* Fixed hex in element */
background: #ffffff;           /* Fixed hex for backgrounds */
color: #1a1d23;               /* Fixed hex for text */
background: #0d1117;           /* GitHub Dark in element */
--accent: #58a6ff;             /* GitHub Blue */
font-family: Arial;            /* Generic font */
background: linear-gradient(90deg, var(--bs-primary), #f97316);  /* Hex in gradient stop */
```

```jinja2
{# ❌ NEVER DO #}
{% block head %}              {# Wrong block name — use extra_css #}
<style> .my-card { ... } </style>  {# Inline styles — use CSS file #}
```

```css
/* ❌ NEVER RECREATE base.html effects */
.my-card:nth-child(1) { animation-delay: 0.08s; }  /* Use stagger-children instead */
.my-card:nth-child(2) { animation-delay: 0.16s; }
```

**Always use**: `var(--bs-*)`, `var(--fin-*)`, or `var(--agent-*)` depending on module.

**If you need to check the available variables**: See [references/css-variables.md](references/css-variables.md)

## Anti-Hallucination Rules

1. **Variable names**: ALWAYS check css-variables.md before using a variable name. Do NOT guess.
2. **Existing modules**: When the module already has a design system (e.g., `--fin-*`), reuse its exact variable names. Do NOT create parallel naming (e.g., `--conc-*` for financial conciliation — use `--fin-*`).
3. **Premium classes**: The ONLY premium classes available are: `premium-page`, `reveal`, `stagger-children`, `shadow-glow`, `glass`, `btn-shine`, `pulse-glow`. Do NOT invent others.
4. **Template block names**: Use `extra_css` for CSS, `extra_js` for JS. Do NOT use `head` or `scripts`.
5. **Both files required**: ALWAYS deliver template.html + CSS file. Never just one.
