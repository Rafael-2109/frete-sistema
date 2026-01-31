# SISTEMA DE DESIGN TOKENS - FRETE SISTEMA

**Data**: 2025-12-18
**Status**: IMPLEMENTADO
**Versão**: 1.0

---

## RESUMO EXECUTIVO

O sistema agora possui uma arquitetura de Design Tokens centralizada e consistente.

| Arquivo | Função | Status |
|---------|--------|--------|
| `_design-tokens.css` | Fonte única de verdade para cores | IMPLEMENTADO |
| `_utilities.css` | Classes utilitárias baseadas em tokens | IMPLEMENTADO |
| `bootstrap-overrides.css` | Importa tokens e sobrescreve Bootstrap | ATUALIZADO |
| `_variables.css` | OBSOLETO - removido | REMOVIDO |

---

## PRINCÍPIOS DO DESIGN

### Paleta Minimalista
- **95% Escala de Cinza** - UI monocromática elegante
- **5% Accent Âmbar** - Apenas para ações primárias e destaques
- **Cores semânticas** - APENAS para status críticos (success/danger)

### Dark Mode (Padrão) - "Emerge from Darkness"
```
Body (5%) → Cards (8%) → Elevated (10%) → Modal (12%)
```
Elementos mais importantes "emergem" do fundo escuro.

### Light Mode - "Float Above Gray"
```
Body (82%) → Cards (90%) → Elevated (95%) → Modal (98%)
```
Fundo cinza médio, elementos elevados flutuam em direção ao branco.

---

## ARQUITETURA DE ARQUIVOS

```
app/static/css/
├── _design-tokens.css    # FONTE ÚNICA - Todos os tokens
├── _utilities.css        # Classes utilitárias
├── bootstrap-overrides.css # Importa tokens + override Bootstrap
└── modules/
    └── carteira/
        ├── agrupados.css # Usa var(--token)
        └── ...
```

### Ordem de Carregamento (base.html)
1. Bootstrap CSS
2. bootstrap-overrides.css (que importa _design-tokens.css e _utilities.css)
3. Módulos específicos

---

## ESCALA DE CINZA

### Primitivos (HSL 0°, 0%, X%)

| Token | Lightness | Uso Principal |
|-------|-----------|---------------|
| `--gray-0` | 0% | Preto puro |
| `--gray-5` | 5% | Body dark mode |
| `--gray-8` | 8% | Cards dark mode |
| `--gray-10` | 10% | Elevated dark mode |
| `--gray-12` | 12% | Modal dark mode |
| `--gray-15` | 15% | Borders dark mode |
| `--gray-20` | 20% | Borders secundárias |
| `--gray-25` | 25% | Hover states dark |
| `--gray-30` | 30% | Muted text dark |
| `--gray-40` | 40% | Secondary text dark |
| `--gray-50` | 50% | Neutral |
| `--gray-60` | 60% | Secondary text light |
| `--gray-70` | 70% | Borders light mode |
| `--gray-75` | 75% | Hover light mode |
| `--gray-80` | 80% | Borders light claras |
| `--gray-82` | 82% | Body light mode |
| `--gray-85` | 85% | Borders light sutis |
| `--gray-90` | 90% | Cards light mode |
| `--gray-95` | 95% | Elevated light mode |
| `--gray-98` | 98% | Modal light mode |
| `--gray-100` | 100% | Branco puro |

---

## ACCENT ÂMBAR

Cor de destaque única baseada em HSL(45°, X%, X%).

| Token | HSL | Uso |
|-------|-----|-----|
| `--amber-20` | hsl(45, 100%, 20%) | Não usado |
| `--amber-30` | hsl(45, 100%, 30%) | Text dark âmbar |
| `--amber-40` | hsl(45, 95%, 40%) | Borders âmbar |
| `--amber-50` | hsl(45, 100%, 50%) | Âmbar puro |
| `--amber-55` | hsl(45, 95%, 55%) | **PRIMARY** - Botões, links |
| `--amber-60` | hsl(45, 90%, 60%) | Hover |
| `--amber-70` | hsl(45, 85%, 70%) | Highlight |
| `--amber-80` | hsl(45, 80%, 80%) | Backgrounds sutis |
| `--amber-90` | hsl(45, 75%, 90%) | Backgrounds claros |

### Aliases
```css
--accent-primary: var(--amber-55);
--accent-hover: var(--amber-60);
--accent-active: var(--amber-50);
--accent-subtle: var(--amber-80);
```

---

## CORES SEMÂNTICAS

Usadas APENAS para comunicar status críticos. NÃO usar para UI geral.

| Token | HSL | Uso |
|-------|-----|-----|
| `--semantic-success` | hsl(145, 65%, 40%) | Sucesso, confirmação |
| `--semantic-danger` | hsl(0, 70%, 50%) | Erro, perigo |
| `--semantic-warning` | var(--amber-55) | Alerta (usa âmbar) |
| `--semantic-info` | var(--gray-50) | Info (CINZA, não azul!) |

### Variantes
```css
--semantic-success-subtle: hsla(145, 65%, 40%, 0.15);
--semantic-danger-subtle: hsla(0, 70%, 50%, 0.15);
--semantic-warning-subtle: hsla(45, 95%, 55%, 0.15);
```

---

## TOKENS DE TEMA

### Dark Mode (Padrão)
```css
:root, [data-bs-theme="dark"] {
    --bg-body: var(--gray-5);
    --bg-surface: var(--gray-8);
    --bg-elevated: var(--gray-10);
    --bg-modal: var(--gray-12);
    --bg-input: var(--gray-10);

    --border-default: var(--gray-15);
    --border-subtle: var(--gray-12);
    --border-strong: var(--gray-25);

    --text-primary: var(--gray-95);
    --text-secondary: var(--gray-60);
    --text-muted: var(--gray-40);
    --text-inverse: var(--gray-5);

    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
}
```

### Light Mode
```css
[data-bs-theme="light"] {
    --bg-body: var(--gray-82);
    --bg-surface: var(--gray-90);
    --bg-elevated: var(--gray-95);
    --bg-modal: var(--gray-98);
    --bg-input: var(--gray-95);

    --border-default: var(--gray-70);
    --border-subtle: var(--gray-75);
    --border-strong: var(--gray-60);

    --text-primary: var(--gray-10);
    --text-secondary: var(--gray-30);
    --text-muted: var(--gray-50);
    --text-inverse: var(--gray-95);

    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.15);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.2);
}
```

---

## CLASSES UTILITÁRIAS

### Backgrounds
```css
.bg-body        /* var(--bg-body) */
.bg-surface     /* var(--bg-surface) */
.bg-elevated    /* var(--bg-elevated) */
.bg-modal       /* var(--bg-modal) */
.bg-input       /* var(--bg-input) */
.bg-accent      /* var(--accent-primary) */
```

### Texto
```css
.text-primary   /* var(--text-primary) */
.text-secondary /* var(--text-secondary) */
.text-muted     /* var(--text-muted) */
.text-accent    /* var(--accent-primary) */
```

### Bordas
```css
.border-default /* var(--border-default) */
.border-subtle  /* var(--border-subtle) */
.border-strong  /* var(--border-strong) */
.border-accent  /* var(--accent-primary) */
```

### Borders Left (Status)
```css
.border-left-success  /* 3px solid var(--semantic-success) */
.border-left-danger   /* 3px solid var(--semantic-danger) */
.border-left-warning  /* 3px solid var(--semantic-warning) */
.border-left-info     /* 3px solid var(--semantic-info) */
```

### Badges de Status
```css
.badge-status-pendente   /* Warning sutil */
.badge-status-processando /* Info sutil */
.badge-status-concluido  /* Success sutil */
.badge-status-erro       /* Danger sutil */
```

### Badges de Filtro
```css
.badge-filtro           /* Base */
.badge-filtro.ativo     /* Com accent âmbar */
```

---

## COMPONENTES BASE

### Botões
```css
.btn-primary {
    background: var(--accent-primary);
    color: var(--gray-10);
    border: none;
}
.btn-primary:hover {
    background: var(--accent-hover);
}

.btn-secondary {
    background: var(--gray-25);
    color: var(--text-primary);
}

.btn-outline-primary {
    border-color: var(--accent-primary);
    color: var(--accent-primary);
}
```

### Cards
```css
.card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
}
.card-header {
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-default);
}
```

### Forms
```css
.form-control, .form-select {
    background: var(--bg-input);
    border-color: var(--border-default);
    color: var(--text-primary);
}
.form-control:focus {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 0.2rem var(--accent-subtle);
}
```

### Tables
```css
.table {
    --bs-table-bg: var(--bg-surface);
    --bs-table-color: var(--text-primary);
    --bs-table-border-color: var(--border-default);
}
.table-hover tbody tr:hover {
    background: var(--bg-elevated);
}
```

### Modals
```css
.modal-content {
    background: var(--bg-modal);
    border-color: var(--border-default);
}
.modal-header, .modal-footer {
    border-color: var(--border-subtle);
}
```

---

## MAPEAMENTO BOOTSTRAP

Todas as variáveis Bootstrap são mapeadas para Design Tokens:

```css
:root {
    --bs-body-bg: var(--bg-body);
    --bs-body-color: var(--text-primary);
    --bs-border-color: var(--border-default);
    --bs-primary: var(--accent-primary);
    --bs-secondary: var(--gray-40);
    --bs-success: var(--semantic-success);
    --bs-danger: var(--semantic-danger);
    --bs-warning: var(--semantic-warning);
    --bs-info: var(--semantic-info);
}
```

---

## MÓDULOS MIGRADOS

### Carteira (100% migrado)
- `agrupados.css` - Usa Design Tokens
- `carteira-simples.css` - Usa variáveis Bootstrap
- `workspace-montagem.css` - Migrado para tokens
- `separacao-animations.css` - Migrado para tokens

### Módulos com Sistema Próprio (Manter)
- **Agente** (`--agent-*`) - Sistema de chat independente
- **Financeiro** (`--fin-*`) - Visual específico para área financeira
- **Manufatura** (`--np-*`) - Necessidade de produção

### Arquivos de Impressão (Não Migrar)
- `embarques/imprimir_*.html` - Cores hardcoded para consistência de impressão

---

## GUIA DE USO

### SEMPRE usar:
```css
/* Bom - usa tokens */
background: var(--bg-surface);
color: var(--text-primary);
border-color: var(--border-default);
```

### NUNCA usar:
```css
/* Ruim - hardcoded */
background: #1a1a1a;
color: #ffffff;
border-color: #333;

/* Ruim - cores fora do sistema */
background: blue;
color: #0d6efd; /* Bootstrap blue - não usar! */
```

### Cores semânticas - APENAS para status:
```css
/* Bom - status real */
.status-sucesso { color: var(--semantic-success); }
.status-erro { color: var(--semantic-danger); }

/* Ruim - decorativo */
.titulo { color: var(--semantic-success); } /* NÃO! */
```

---

## CHECKLIST PARA NOVOS DESENVOLVIMENTOS

- [ ] Usar apenas tokens definidos em `_design-tokens.css`
- [ ] Não adicionar cores hardcoded
- [ ] Não usar azul (`#0d6efd`, `#007bff`) - sistema é monocromático + âmbar
- [ ] Testar em Dark e Light mode
- [ ] Usar classes utilitárias quando possível
- [ ] Cores semânticas APENAS para status críticos
