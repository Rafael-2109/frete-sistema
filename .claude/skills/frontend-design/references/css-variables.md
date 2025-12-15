# Frontend Design Reference - Variáveis CSS do Sistema

**Última Atualização**: 15/12/2025

---

## Índice

- [1. Bootstrap Overrides (`--bs-*`)](#1-bootstrap-overrides---bs-)
  - [Cores Semânticas](#cores-semânticas-accent)
  - [Cores RGB](#cores-rgb-para-rgba)
  - [Backgrounds](#backgrounds)
  - [Texto](#texto)
  - [Bordas](#bordas)
  - [Links](#links)
  - [Tipografia](#tipografia)
- [2. Financeiro (`--fin-*`)](#2-financeiro---fin-)
  - [Backgrounds](#backgrounds-1)
  - [Bordas](#bordas-1)
  - [Texto](#texto-1)
  - [Acentos](#acentos-financial-teal-palette)
  - [Status de Conciliação](#status-de-conciliação)
  - [Gradientes e Sombras](#gradientes)
- [3. Agente (`--agent-*`)](#3-agente---agent-)
  - [Backgrounds](#backgrounds-2)
  - [Texto](#texto-2)
  - [Acentos](#acentos-deep-ocean-palette)
  - [Status](#status)
  - [Sombras e Transições](#sombras)
- [4. Seletores de Tema](#4-seletores-de-tema)
- [5. Classes Utilitárias](#5-classes-utilitárias)
- [6. Padrões de Componentes](#6-padrões-de-componentes)
- [7. NUNCA USAR](#7-nunca-usar)
- [8. Mapeamento entre Sistemas](#8-mapeamento-entre-sistemas)
- [9. Exemplo de Migração](#9-exemplo-de-migração)
- [10. Premium Effects (Financeiro)](#10-premium-effects-financeiro)

---

## Arquivos CSS com Variáveis

| Arquivo | Caminho | Prefix | Uso |
|---------|---------|--------|-----|
| **bootstrap-overrides.css** | `app/static/css/bootstrap-overrides.css` | `--bs-*` | **PRINCIPAL** - Sistema inteiro |
| **extrato.css** | `app/static/css/financeiro/extrato.css` | `--fin-*` | Módulo Financeiro |
| **agent-theme.css** | `app/static/agente/css/agent-theme.css` | `--agent-*` | Chat do Agente Logístico |
| **navbar.css** | `app/static/css/navbar.css` | `--bs-*` | Navbar (usa bootstrap-overrides) |
| **style.css** | `app/static/style.css` | - | Estilos globais legados |

---

## 1. Bootstrap Overrides (`--bs-*`)

**Arquivo**: `app/static/css/bootstrap-overrides.css`
**Uso**: Sistema inteiro - carregado APÓS bootstrap.min.css

### Cores Semânticas (Accent)

| Variável | Light Mode | Dark Mode | Uso |
|----------|------------|-----------|-----|
| `--bs-primary` | `#009d80` | `#00d4aa` | Financial Teal principal |
| `--bs-success` | `#0d7d5f` | `#10b981` | Sucesso (Emerald) |
| `--bs-warning` | `#b45309` | `#f59e0b` | Alerta (Amber) |
| `--bs-danger` | `#dc2626` | `#ef4444` | Erro (Red) |
| `--bs-info` | `#0284c7` | `#0ea5e9` | Info (Sky Blue) |
| `--bs-secondary` | `#64748b` | `#64748b` | Secundário (Slate) |

### Cores RGB (para rgba())

```css
--bs-primary-rgb: 0, 157, 128;    /* Light / Dark: 0, 212, 170 */
--bs-success-rgb: 13, 125, 95;    /* Light / Dark: 16, 185, 129 */
--bs-warning-rgb: 180, 83, 9;     /* Light / Dark: 245, 158, 11 */
--bs-danger-rgb: 220, 38, 38;     /* Light / Dark: 239, 68, 68 */
--bs-info-rgb: 2, 132, 199;       /* Light / Dark: 14, 165, 233 */
```

**Exemplo de uso:**
```css
background: rgba(var(--bs-primary-rgb), 0.15);
box-shadow: 0 0 20px rgba(var(--bs-primary-rgb), 0.3);
```

### Backgrounds

| Variável | Light Mode | Dark Mode | Hierarquia |
|----------|------------|-----------|------------|
| `--bs-body-bg` | `#ffffff` | `#0a1628` | Fundo principal |
| `--bs-secondary-bg` | `#f6f8fa` | `#111d2e` | Cards, containers |
| `--bs-tertiary-bg` | `#eaeef2` | `#1a2942` | Headers, inputs |
| `--bs-card-bg` | `#ffffff` | `#111d2e` | Cards específico |

### Texto

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--bs-body-color` | `#1f2328` | `#f0f6fc` |
| `--bs-secondary-color` | `#6b8aad` | `#8dafd5` |

### Bordas

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--bs-border-color` | `rgba(31, 35, 40, 0.15)` | `#2d4a6a` |
| `--bs-border-radius` | `0.5rem` | `0.5rem` |
| `--bs-border-radius-sm` | `0.25rem` | `0.25rem` |
| `--bs-border-radius-lg` | `0.75rem` | `0.75rem` |

### Links

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--bs-link-color` | `#009d80` | `#00d4aa` |
| `--bs-link-hover-color` | `#007a63` | `#00f5c4` |

### Tipografia

```css
--bs-font-sans-serif: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
--bs-font-monospace: 'JetBrains Mono', 'Fira Code', monospace;
```

[↑ Voltar ao índice](#índice)

---

## 2. Financeiro (`--fin-*`)

**Arquivo**: `app/static/css/financeiro/extrato.css`
**Uso**: Módulo Financeiro (extrato, hub de baixas, conciliação)

### Backgrounds

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--fin-bg-primary` | `#ffffff` | `#0a1628` |
| `--fin-bg-secondary` | `#f6f8fa` | `#111d2e` |
| `--fin-bg-tertiary` | `#eaeef2` | `#1a2942` |
| `--fin-bg-hover` | `rgba(0,0,0,0.04)` | `#243656` |
| `--fin-bg-elevated` | `#ffffff` | `#152238` |

### Bordas

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--fin-border` | `rgba(31, 35, 40, 0.15)` | `#2d4a6a` |
| `--fin-border-light` | `rgba(31, 35, 40, 0.10)` | `#3d5f82` |
| `--fin-border-focus` | `#009d80` | `#00d4aa` |

### Texto

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--fin-text-primary` | `#1f2328` | `#f0f6fc` |
| `--fin-text-secondary` | `#656d76` | `#8b949e` |
| `--fin-text-muted` | `#8b949e` | `#6e7681` |
| `--fin-text-inverse` | `#ffffff` | `#0a1628` |

### Acentos (Financial Teal Palette)

| Variável | Light Mode | Dark Mode | Uso |
|----------|------------|-----------|-----|
| `--fin-accent-primary` | `#009d80` | `#00d4aa` | Teal principal |
| `--fin-accent-success` | `#0d7d5f` | `#10b981` | Sucesso |
| `--fin-accent-warning` | `#b45309` | `#f59e0b` | Alerta |
| `--fin-accent-danger` | `#dc2626` | `#ef4444` | Erro |
| `--fin-accent-danger-light` | `#ef4444` | `#f87171` | Erro claro |
| `--fin-accent-info` | `#0284c7` | `#0ea5e9` | Info |
| `--fin-accent-pending` | `#64748b` | `#64748b` | Pendente |

### Backgrounds de Status

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--fin-bg-success` | `rgba(13, 125, 95, 0.10)` | `rgba(16, 185, 129, 0.15)` |
| `--fin-bg-warning` | `rgba(180, 83, 9, 0.10)` | `rgba(245, 158, 11, 0.15)` |
| `--fin-bg-danger` | `rgba(220, 38, 38, 0.10)` | `rgba(239, 68, 68, 0.15)` |
| `--fin-bg-info` | `rgba(2, 132, 199, 0.10)` | `rgba(14, 165, 233, 0.15)` |

### Status de Conciliação

| Variável | Uso |
|----------|-----|
| `--fin-match-bg` | Fundo item com match |
| `--fin-match-border` | Borda item com match |
| `--fin-multiplos-bg` | Fundo item múltiplos matches |
| `--fin-multiplos-border` | Borda item múltiplos matches |
| `--fin-sem-match-bg` | Fundo sem match |
| `--fin-sem-match-border` | Borda sem match |
| `--fin-aprovado-bg` | Fundo aprovado |
| `--fin-aprovado-border` | Borda aprovado |
| `--fin-conciliado-bg` | Fundo conciliado |
| `--fin-conciliado-border` | Borda conciliado |

### Gradientes

```css
--fin-gradient-header: linear-gradient(135deg, #152238 0%, #0a1628 100%);
--fin-gradient-card: linear-gradient(180deg, #111d2e 0%, #0a1628 100%);
--fin-gradient-accent: linear-gradient(135deg, #059669 0%, #10b981 100%);
```

### Sombras

```css
--fin-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--fin-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
--fin-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
--fin-shadow-glow: 0 0 20px rgba(0, 212, 170, 0.15);
```

### Tipografia e Spacing

```css
--fin-font-display: 'IBM Plex Sans', -apple-system, sans-serif;
--fin-font-mono: 'JetBrains Mono', 'Fira Code', monospace;

--fin-transition-fast: 150ms ease;
--fin-transition-normal: 250ms ease;
--fin-transition-slow: 400ms ease;

--fin-radius-sm: 4px;
--fin-radius-md: 8px;
--fin-radius-lg: 12px;
--fin-radius-xl: 16px;
```

[↑ Voltar ao índice](#índice)

---

## 3. Agente (`--agent-*`)

**Arquivo**: `app/static/agente/css/agent-theme.css`
**Uso**: Chat do Agente Logístico (Deep Ocean Design System)

### Backgrounds

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--agent-bg-primary` | `#f4f7fa` | `#0a1628` |
| `--agent-bg-secondary` | `#ffffff` | `#111d2e` |
| `--agent-bg-tertiary` | `#e8eef4` | `#1a2942` |
| `--agent-bg-hover` | `#dce4ed` | `#243554` |
| `--agent-bg-active` | `#d0dae6` | `#2d4266` |

### Texto

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--agent-text-primary` | `#1f2328` | `#f0f6fc` |
| `--agent-text-secondary` | `#57606a` | `#8b949e` |
| `--agent-text-muted` | `#8b949e` | `#6e7681` |
| `--agent-text-inverse` | `#ffffff` | `#0a1628` |

### Acentos (Deep Ocean Palette)

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--agent-accent-primary` | `#00a88a` | `#00d4aa` |
| `--agent-accent-primary-rgb` | `0, 168, 138` | `0, 212, 170` |
| `--agent-accent-primary-hover` | `#009679` | `#00eabb` |
| `--agent-accent-primary-muted` | `rgba(0, 168, 138, 0.12)` | `rgba(0, 212, 170, 0.15)` |
| `--agent-accent-secondary` | `#0284c7` | `#0ea5e9` |
| `--agent-accent-secondary-rgb` | `2, 132, 199` | `14, 165, 233` |

### Status

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--agent-success` | `#059669` | `#10b981` |
| `--agent-success-muted` | `rgba(5, 150, 105, 0.12)` | `rgba(16, 185, 129, 0.15)` |
| `--agent-warning` | `#d97706` | `#f59e0b` |
| `--agent-warning-muted` | `rgba(217, 119, 6, 0.12)` | `rgba(245, 158, 11, 0.15)` |
| `--agent-danger` | `#dc2626` | `#ef4444` |
| `--agent-danger-muted` | `rgba(220, 38, 38, 0.12)` | `rgba(239, 68, 68, 0.15)` |
| `--agent-info` | `#0284c7` | `#0ea5e9` |
| `--agent-info-muted` | `rgba(2, 132, 199, 0.12)` | `rgba(14, 165, 233, 0.15)` |

### Bordas

| Variável | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--agent-border-color` | `rgba(31, 35, 40, 0.12)` | `rgba(240, 246, 252, 0.1)` |
| `--agent-border-color-emphasis` | `rgba(31, 35, 40, 0.2)` | `rgba(240, 246, 252, 0.2)` |
| `--agent-border-color-active` | `rgba(0, 168, 138, 0.4)` | `rgba(0, 212, 170, 0.4)` |

### Sombras

```css
--agent-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--agent-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
--agent-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
--agent-shadow-xl: 0 20px 40px rgba(0, 0, 0, 0.6);
--agent-shadow-glow: 0 0 20px rgba(0, 212, 170, 0.2);
--agent-shadow-glow-strong: 0 0 40px rgba(0, 212, 170, 0.3);
```

### Tipografia e Spacing

```css
--agent-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--agent-font-mono: 'JetBrains Mono', 'Fira Code', monospace;

--agent-space-xs: 4px;
--agent-space-sm: 8px;
--agent-space-md: 12px;
--agent-space-lg: 16px;
--agent-space-xl: 24px;
--agent-space-2xl: 32px;

--agent-radius-sm: 6px;
--agent-radius-md: 10px;
--agent-radius-lg: 16px;
--agent-radius-xl: 24px;
--agent-radius-full: 9999px;
```

### Transições

```css
--agent-transition-fast: 150ms ease;
--agent-transition-base: 250ms ease;
--agent-transition-slow: 400ms ease;
--agent-transition-spring: 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Gradientes

```css
--agent-gradient-primary: linear-gradient(135deg, #00d4aa 0%, #0ea5e9 100%);
--agent-gradient-header: linear-gradient(135deg, #0a1628 0%, #111d2e 50%, #1a2942 100%);
--agent-gradient-glow: radial-gradient(ellipse at 50% 0%, rgba(0, 212, 170, 0.15) 0%, transparent 60%);
```

### Z-Index Scale

```css
--agent-z-base: 1;
--agent-z-dropdown: 100;
--agent-z-sticky: 200;
--agent-z-modal: 1000;
--agent-z-tooltip: 1100;
--agent-z-toast: 1200;
```

[↑ Voltar ao índice](#índice)

---

## 4. Seletores de Tema

### Bootstrap (data-bs-theme ou data-theme)

```css
/* Light mode */
[data-bs-theme="light"] .elemento,
[data-theme="light"] .elemento { }

/* Dark mode */
[data-bs-theme="dark"] .elemento,
[data-theme="dark"] .elemento,
:root:not([data-theme="light"]) .elemento { }
```

### Financeiro (data-theme)

```css
[data-theme="light"] { /* variáveis light */ }
:root { /* variáveis dark - default */ }
```

### Agente (data-theme)

```css
[data-theme="light"] { /* variáveis light */ }
:root, [data-theme="dark"] { /* variáveis dark - default */ }
```

[↑ Voltar ao índice](#índice)

---

## 5. Classes Utilitárias

### Bootstrap Overrides

```html
<!-- Texto -->
<span class="text-primary">Teal</span>
<span class="text-success">Verde</span>
<span class="text-warning">Laranja</span>
<span class="text-danger">Vermelho</span>
<span class="text-info">Azul</span>
<span class="text-muted">Muted</span>

<!-- Backgrounds -->
<div class="bg-primary">...</div>
<div class="bg-success">...</div>

<!-- Monospace -->
<span class="font-mono">R$ 1.234,56</span>

<!-- Animações -->
<div class="animate-fade-in">...</div>
<div class="animate-pulse">...</div>
<div class="stagger-children">...</div>
```

### Financeiro

```html
<div class="fin-container">...</div>
<div class="fin-section">...</div>
<div class="fin-stat-card">...</div>
<div class="fin-hub-card">...</div>
<div class="fin-header">...</div>
```

### Agente

```html
<div class="chat-fullscreen-wrapper">...</div>
<div class="message assistant">...</div>
<div class="message user">...</div>
```

[↑ Voltar ao índice](#índice)

---

## 6. Padrões de Componentes

### Card Padrão (Bootstrap)

```css
.my-card {
    background: var(--bs-secondary-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 12px;
    transition: all 0.3s ease;
}

.my-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}
```

### Page Header

```html
<header class="page-header">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h1 class="h3 mb-0">
                <i class="fas fa-icon text-primary me-2"></i>
                Título
            </h1>
            <small class="text-muted">Subtítulo</small>
        </div>
        <div class="btn-toolbar">
            <a href="..." class="btn btn-outline-secondary btn-sm">
                <i class="fas fa-arrow-left me-1"></i> Voltar
            </a>
        </div>
    </div>
</header>
```

### Tabela

```css
.table-container {
    background: var(--bs-secondary-bg);
    border: 1px solid var(--bs-border-color);
    border-radius: 12px;
    overflow: hidden;
}

.table-container thead th {
    background: var(--bs-tertiary-bg);
    color: var(--bs-secondary-color);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.875rem;
}
```

[↑ Voltar ao índice](#índice)

---

## 7. NUNCA USAR

- ❌ Cores hex fixas (`#ffffff`, `#000000`, `#343541`, `#202123`)
- ❌ `bg-dark`, `bg-light` sem adaptação de tema
- ❌ Fontes genéricas (Arial, Inter padrão, Roboto)
- ❌ Classes Bootstrap que não adaptam ao tema sem override
- ❌ CSS inline extenso com paleta própria

[↑ Voltar ao índice](#índice)

---

## 8. Mapeamento entre Sistemas

| Bootstrap (`--bs-*`) | Financeiro (`--fin-*`) | Agente (`--agent-*`) |
|---------------------|------------------------|---------------------|
| `--bs-body-bg` | `--fin-bg-primary` | `--agent-bg-primary` |
| `--bs-secondary-bg` | `--fin-bg-secondary` | `--agent-bg-secondary` |
| `--bs-tertiary-bg` | `--fin-bg-tertiary` | `--agent-bg-tertiary` |
| `--bs-body-color` | `--fin-text-primary` | `--agent-text-primary` |
| `--bs-secondary-color` | `--fin-text-secondary` | `--agent-text-secondary` |
| `--bs-border-color` | `--fin-border` | `--agent-border-color` |
| `--bs-primary` | `--fin-accent-primary` | `--agent-accent-primary` |
| `--bs-success` | `--fin-accent-success` | `--agent-success` |
| `--bs-warning` | `--fin-accent-warning` | `--agent-warning` |
| `--bs-danger` | `--fin-accent-danger` | `--agent-danger` |
| `--bs-info` | `--fin-accent-info` | `--agent-info` |

[↑ Voltar ao índice](#índice)

---

## 9. Exemplo de Migração

### ANTES (errado)

```css
.card {
    background: #343541;
    border: 1px solid #444654;
    color: #ececf1;
}
```

### DEPOIS (correto)

```css
.card {
    background: var(--bs-secondary-bg);
    border: 1px solid var(--bs-border-color);
    color: var(--bs-body-color);
}
```

[↑ Voltar ao índice](#índice)

---

## 10. Premium Effects (Financeiro)

**Arquivos**:
- CSS: `app/static/css/financeiro/premium-effects.css`
- JS: `app/static/js/financeiro/premium-effects.js`

### Como Usar

```html
<!-- Carregar no template -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/financeiro/premium-effects.css') }}">
<script src="{{ url_for('static', filename='js/financeiro/premium-effects.js') }}"></script>
```

### Classes CSS Disponíveis

| Classe | Descrição | Uso |
|--------|-----------|-----|
| `.grain-overlay` | Textura de grão sobre a página | Container principal |
| `.aurora-bg` | Background animado tipo aurora | Container fixo |
| `.glass` | Efeito glassmorphism | Cards, modais |
| `.shadow-glow` | Sombra com glow colorido | Cards destacados |
| `.shadow-glow--success` | Glow verde | Status sucesso |
| `.shadow-glow--danger` | Glow vermelho | Status erro |
| `.btn-shine` | Efeito shine no hover | Botões |
| `.btn-liquid` | Efeito liquid no hover | Botões |
| `.text-gradient` | Texto com gradiente | Títulos |
| `.text-gradient-animated` | Gradiente animado | Títulos hero |
| `.text-glow` | Texto com glow | Valores destacados |
| `.reveal` | Aparece ao scroll | Seções |
| `.stagger-children` | Filhos aparecem em sequência | Grids, listas |
| `.spotlight` | Luz segue o mouse | Cards interativos |
| `.pulse-glow` | Pulsa com glow | Alertas, badges |

### Exemplos de Uso

**Reveal ao Scroll:**
```html
<div class="reveal">
    Aparece quando entra na viewport
</div>
```

**Stagger Children:**
```html
<div class="stagger-children">
    <div>Item 1 (delay 0.1s)</div>
    <div>Item 2 (delay 0.15s)</div>
    <div>Item 3 (delay 0.2s)</div>
</div>
```

**Card com Spotlight:**
```html
<div class="card spotlight">
    Luz segue o cursor
</div>
```

**Glassmorphism:**
```html
<div class="glass">
    Card com blur e transparência
</div>
```

**Texto Gradiente:**
```html
<h1 class="text-gradient">Título com Gradiente</h1>
<h1 class="text-gradient-animated">Gradiente Animado</h1>
```

### JavaScript API

```javascript
// Inicialização automática no DOMContentLoaded
// Métodos disponíveis:
PremiumEffects.initScrollReveal();     // Ativa .reveal
PremiumEffects.initStaggeredChildren(); // Ativa .stagger-children
PremiumEffects.initSpotlight();         // Ativa .spotlight
```

### Reduced Motion

Todos os efeitos respeitam `prefers-reduced-motion: reduce` automaticamente.

[↑ Voltar ao índice](#índice)
