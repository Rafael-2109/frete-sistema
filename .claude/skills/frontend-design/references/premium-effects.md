# Premium Effects - Sistema de Efeitos Visuais

Sistema centralizado de efeitos visuais premium para todas as telas do sistema.

## Arquitetura

Os efeitos premium estão **centralizados no `base.html`**:

```html
<!-- base.html -->
<head>
    ...
    <link rel="stylesheet" href="{{ url_for('static', filename='css/financeiro/premium-effects.css') }}">
</head>
<body>
    ...
    <script src="{{ url_for('static', filename='js/financeiro/premium-effects.js') }}"></script>
</body>
```

## Ativação Automática

Para ativar os efeitos premium em qualquer tela, basta adicionar a classe `premium-page` ao container principal:

```jinja2
{% block content %}
<div class="container-fluid premium-page">
    <header class="reveal">...</header>
    ...
</div>
{% endblock %}
```

O JavaScript detecta automaticamente `.premium-page` e injeta o aurora background.

## Efeitos Disponíveis

### 1. Aurora Background (automático)

Injetado automaticamente quando `.premium-page` está presente.

```css
.aurora-bg {
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse at 20% 30%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 70%, rgba(14, 165, 233, 0.1) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%, rgba(168, 85, 247, 0.08) 0%, transparent 70%);
    z-index: -1;
    pointer-events: none;
}
```

### 2. Scroll Reveal (classe `reveal`)

Elementos aparecem suavemente ao entrar na viewport:

```html
<div class="reveal">Aparece ao scrollar</div>
```

### 3. Staggered Children (classe `stagger-children`)

Animação escalonada para listas de cards:

```html
<div class="stagger-children">
    <div class="card">Card 1</div>
    <div class="card">Card 2</div>
    <div class="card">Card 3</div>
</div>
```

### 4. Button Shine (classe `btn-shine`)

Efeito de brilho em botões:

```html
<button class="btn btn-primary btn-shine">Botão Premium</button>
```

### 5. Shadow Glow (classe `shadow-glow`)

Sombra com glow colorido:

```html
<div class="card shadow-glow">Card com glow</div>
```

### 6. Glass Effect (classe `glass`)

Efeito glassmorphism:

```html
<div class="glass">Conteúdo com blur</div>
```

### 7. Pulse Glow (classe `pulse-glow`)

Animação de pulso para chamar atenção:

```html
<span class="badge pulse-glow">Novo!</span>
```

## Efeitos Removidos (decisão de design)

Os seguintes efeitos foram **removidos** por não serem adequados para sistema empresarial:

- `grain-overlay` - Textura de ruído (visual muito "artístico")
- `text-gradient-animated` - Gradiente animado em texto (distração)
- `spotlight` - Efeito de spotlight seguindo mouse (performance)

## Respeitando Preferências do Usuário

O sistema respeita `prefers-reduced-motion`:

```javascript
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    console.log('PremiumEffects: Reduced motion - disabled');
    return;
}
```

## Template Completo

```jinja2
{% extends "base.html" %}

{% block title %}Minha Página{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/meu-modulo/estilos.css') }}">
{% endblock %}

{% block content %}
<div class="container-fluid premium-page">
    <!-- Header com reveal -->
    <header class="page-header reveal">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1 class="h3 mb-0">
                    <i class="fas fa-star text-primary me-2"></i>
                    Título da Página
                </h1>
                <small class="text-muted">Subtítulo</small>
            </div>
            <div>
                <button class="btn btn-primary btn-shine">
                    <i class="fas fa-plus"></i> Ação
                </button>
            </div>
        </div>
    </header>

    <!-- Cards com stagger -->
    <div class="row stagger-children">
        <div class="col-md-4">
            <div class="card shadow-glow">...</div>
        </div>
        <div class="col-md-4">
            <div class="card shadow-glow">...</div>
        </div>
        <div class="col-md-4">
            <div class="card shadow-glow">...</div>
        </div>
    </div>
</div>
{% endblock %}
```

## Telas Já Implementadas

### Carteira
- `agrupados_balanceado.html`
- `dashboard.html`
- `standby.html`
- `programacao_em_lote.html`

### Financeiro
- `extrato_unificado.html`
- `contas_receber_hub.html`
- `contas_pagar_hub.html`
- `baixas_hub.html`
- `listar_contas_pagar.html`
- `pagamentos_baixas_hub.html`

### Manufatura
- `index.html`
- `necessidade_producao/index.html`
- `programacao_linhas.html`
- `projecao_estoque/consolidado.html`
- `projecao_estoque/index.html`
- `historico_pedidos.html`
- `recursos_producao.html`
- `requisicoes_compras/listar.html`
- `analise_producao/index.html`
- `lista_materiais/index.html`
- `lista_materiais/importar.html`
- `previsao_demanda_nova.html`
- `pedidos_compras/index.html`
- `pedidos_compras/sincronizar_manual.html`
- `requisicoes_compras/sincronizar_manual.html`

### Outros Módulos
- `estoque/listar_movimentacoes.html`
- `monitoramento/listar_entregas.html`
- `pedidos/lista_pedidos.html`
- `portaria/historico.html`
- `portal/sendas/exportacao.html`
- `portal/sendas/verificacao.html`
