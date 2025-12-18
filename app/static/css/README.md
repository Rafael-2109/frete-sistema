# Estrutura CSS - Frete Sistema

**Atualizado**: 2025-12-17
**Versao**: 2.1.0

---

## Estrutura de Pastas

```
app/static/css/
├── _variables.css              # FONTE UNICA de variaveis de cor
├── bootstrap-overrides.css     # Sobrescritas do Bootstrap
├── navbar.css                  # Estilos da navbar (global)
├── style.css                   # Legacy (manter por compatibilidade)
│
├── modules/
│   ├── carteira/               # Modulo Carteira de Pedidos
│   │   ├── agrupados.css       # Carteira agrupada por cliente
│   │   ├── workspace-montagem.css  # Workspace de montagem de cargas
│   │   ├── separacao-animations.css # Animacoes de separacao
│   │   └── carteira-simples.css    # Visao simplificada da carteira
│   │
│   ├── analises/               # Modulo Analises
│   │   └── drilldown.css       # Analises drill-down
│   │
│   └── financeiro/             # Modulo Financeiro
│       ├── extrato.css
│       └── premium-effects.css
│
└── contas_receber.css          # Modulo Contas a Receber
```

---

## Como Funciona

### 1. Variaveis Centralizadas

TODAS as variaveis de cor estao em `_variables.css`. Este arquivo e importado por `bootstrap-overrides.css`.

```css
/* _variables.css */
:root, [data-bs-theme="light"], [data-theme="light"] {
    --bs-primary: #009d80;
    --bs-success: #0d7d5f;
    /* ... */
}

[data-bs-theme="dark"], [data-theme="dark"] {
    --bs-primary: #00d4aa;
    --bs-success: #10b981;
    /* ... */
}
```

### 2. Ordem de Carregamento (base.html)

```html
<!-- 1. CDN Bootstrap -->
<link href="bootstrap.min.css">

<!-- 2. Icones e libs -->
<link href="font-awesome">
<link href="toastr">

<!-- 3. Overrides e variaveis -->
<link href="bootstrap-overrides.css">  <!-- Importa _variables.css -->
<link href="navbar.css">
<link href="premium-effects.css">
<link href="style.css">

<!-- 4. CSS especifico do modulo -->
{% block extra_css %}{% endblock %}
```

---

## Como Adicionar Novos Estilos

### Para um modulo existente:

1. Edite o arquivo CSS do modulo em `modules/<modulo>/`
2. Use variaveis de `_variables.css` para cores

### Para um novo modulo:

1. Crie pasta em `modules/<novo_modulo>/`
2. Crie arquivo CSS (ex: `principal.css`)
3. No template, adicione no bloco `extra_css`:

```jinja2
{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/modules/novo_modulo/principal.css') }}">
{% endblock %}
```

---

## Classes Utilitarias (Substituir Inline Styles)

Disponiveis em `_variables.css` para substituir `style="background-color: #xxx"`:

### Backgrounds de Status

```html
<!-- DE: style="background-color: #28a745; color: white;" -->
<!-- PARA: -->
<span class="bg-status-success">Ativo</span>
<span class="bg-status-warning">Pendente</span>
<span class="bg-status-danger">Erro</span>
<span class="bg-status-info">Processando</span>
<span class="bg-status-primary">Principal</span>
<span class="bg-status-secondary">Secundario</span>
<span class="bg-status-neutral">Neutro</span>
```

### Bordas Coloridas

```html
<div class="border-primary-custom">Borda teal</div>
<div class="border-success-custom">Borda verde</div>
<div class="border-warning-custom">Borda amber</div>
<div class="border-danger-custom">Borda vermelha</div>
<div class="border-info-custom">Borda azul</div>
```

### Texto Colorido

```html
<span class="text-status-success">Verde</span>
<span class="text-status-warning">Amber</span>
<span class="text-status-danger">Vermelho</span>
<span class="text-status-info">Azul</span>
<span class="text-status-primary">Teal</span>
```

### Badges de Status

```html
<span class="badge badge-ativo">Ativo</span>
<span class="badge badge-inativo">Inativo</span>
<span class="badge badge-pendente">Pendente</span>
<span class="badge badge-erro">Erro</span>
<span class="badge badge-processando">Processando</span>
```

### Stat Cards (Cards de Estatisticas)

Cards unificados para dashboards. Substitui `card bg-primary text-white`, `card bg-info`, etc.

```html
<!-- Card padrao (borda teal) -->
<div class="card stat-card">
    <div class="card-body">
        <h4 class="mb-0">123</h4>
        <span class="small">Total de Itens</span>
    </div>
</div>

<!-- Card com indicador de sucesso (borda verde) -->
<div class="card stat-card stat-card-success">...</div>

<!-- Card com indicador de perigo (borda vermelha) -->
<div class="card stat-card stat-card-danger">...</div>

<!-- Card clicavel (dentro de link) -->
<a href="...">
    <div class="card stat-card">...</div>
</a>
```

### Action Buttons (Botoes de Acao)

Botoes unificados para acoes rapidas em dashboards. Substitui `btn btn-success btn-lg`, `btn btn-primary btn-lg`, etc.

```html
<!-- Botao padrao (outline teal) -->
<a href="..." class="btn btn-action btn-lg btn-block">
    <i class="fas fa-list"></i><br>
    Listar Itens
</a>

<!-- Botao de acao destrutiva (outline vermelho) -->
<a href="..." class="btn btn-action btn-action-danger btn-lg btn-block">
    <i class="fas fa-trash"></i><br>
    Excluir
</a>
```

---

## Temas (Light/Dark)

O sistema suporta light e dark mode atraves dos atributos:
- `data-bs-theme="light|dark"` (Bootstrap 5.3)
- `data-theme="light|dark"` (fallback)

### Forcar tema em elemento especifico:

```html
<div data-bs-theme="dark">
    <!-- Conteudo sempre em dark mode -->
</div>
```

### Detectar tema no JavaScript:

```javascript
const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
```

---

## Mapeamento de Cores Bootstrap

| Bootstrap Antigo | Nosso Sistema |
|------------------|---------------|
| `#0d6efd` (blue) | `#009d80` (teal) |
| `#198754` (green) | `#0d7d5f` (emerald) |
| `#28a745` (green-old) | `#0d7d5f` (emerald) |
| `#ffc107` (yellow) | `#b45309` (amber) |
| `#dc3545` (red) | `#dc2626` (red) |
| `#17a2b8` (cyan) | `#0284c7` (sky) |
| `#6c757d` (gray) | `#64748b` (slate) |

---

## Regras de Ouro

1. **NUNCA** adicione cores hardcoded. Use variaveis de `_variables.css`
2. **SEMPRE** use classes utilitarias em vez de inline styles
3. **Modularize** - CSS de modulo vai em `modules/<modulo>/`
4. **Teste** light e dark mode apos alteracoes
5. **Documente** alteracoes significativas aqui

---

## Arquivos Obsoletos (NAO USAR)

- ~~`app/templates/carteira/css/`~~ (movido para `modules/carteira/`)

---

## Historico de Mudancas

| Data | Versao | Descricao |
|------|--------|-----------|
| 2025-12-17 | 2.1.0 | Adicionados `.stat-card` e `.btn-action` para padronizar dashboards |
| 2025-12-17 | 2.0.0 | Reorganizacao completa, centralizacao de variaveis, modularizacao |
| 2025-XX-XX | 1.0.0 | Estrutura inicial |
