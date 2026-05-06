# app/static/css/ — Arquitetura CSS

**Atualizado**: 2026-05-06
**Versao**: 3.0.0 (substitui v2.x do antigo `_variables.css`)

> Documentacao tecnica da arquitetura. Para uso correto de badges/botoes/tabelas:
> ler `.claude/references/design/GUIA_COMPONENTES_UI.md`.

---

## Estrutura

```
app/static/css/
├── main.css                       # ENTRY POINT — declara @layer e @import (todos)
│
├── tokens/
│   └── _design-tokens.css         # FONTE UNICA de tokens (HSL, light/dark, --bs-*)
│
├── base/
│   ├── _bootstrap-overrides.css   # ajustes Bootstrap (badges, tables, modals, btns)
│   └── _navbar.css                # navbar global
│
├── components/                    # componentes globais theme-aware
│   ├── _badges.css                # API --_badge-bg/color/border (ver Secao 2 do GUIA)
│   ├── _buttons.css               # API --_btn-bg/color
│   ├── _tables.css                # API --_table-bg/color/border-color (+ row variants)
│   ├── _cards.css
│   ├── _forms.css
│   ├── _modals.css
│   ├── _layout.css
│   └── _tags.css
│
├── modules/                       # estilos por modulo (componem variantes)
│   ├── _hora.css, _carvia.css, _carteira.css, _financeiro.css, ...
│   └── carteira/, custeio/, manufatura/, margem/, analises/  (subpastas)
│
├── utilities/
│   ├── _utilities.css             # classes utilitarias
│   └── _legacy.css                # compat Bootstrap 4 -> 5 (!important tolerado aqui)
│
├── vendor/
│   └── bootstrap.min.css          # self-hosted Bootstrap 5.3.3
│
├── financeiro/                    # CSS especifico (extrato, premium-effects)
└── contas_receber.css             # legado (modulo proprio)
```

---

## @layer Order (cascade)

```css
@layer bootstrap, reset, tokens, base, components, modules, utilities;
```

Layers superiores vencem inferiores **sem precisar `!important`**. Layer `bootstrap`
fica em primeiro = menor prioridade. `utilities` em ultimo = maior prioridade.

> **Gotcha**: `!important` declarado em `@layer bootstrap` (primeiro) tem MAIOR
> prioridade `!important` que `!important` em layers superiores (CSS Cascade L5
> inverte prioridade `!important` por layer). Ou seja: para vencer Bootstrap utility
> classes, NAO use `!important` em layer superior — sobrescreva a CUSTOM PROPERTY de
> input que Bootstrap consome (ex: `--bs-light-rgb`). Veja exemplos em
> `base/_bootstrap-overrides.css` linhas ~245-300.

---

## Como Funciona

### 1. Tokens (cor, espaco, sombra)

Toda cor sai de `tokens/_design-tokens.css`. Light e dark mode definem TODOS os
tokens com mesma chave, valor diferente:

```css
[data-bs-theme="dark"] {
    --bg-light: hsl(0 0% 10%);   /* dark mode */
    --text: hsl(0 0% 95%);
    --semantic-success: hsl(145 80% 52%);
}

[data-bs-theme="light"] {
    --bg-light: hsl(0 0% 100%);  /* light mode (branco) */
    --text: hsl(0 0% 5%);
    --bs-success: hsl(135 70% 35%);  /* override no mapping --bs-* */
}
```

### 2. Componentes — API Custom Property

Componentes expoem `--_X` privadas. Variantes overridam essas vars sem mexer em
`background-color/color` direto:

```css
/* components/_badges.css */
.badge {
    --_badge-bg: var(--bg-light);
    --_badge-color: var(--text);
    background: var(--_badge-bg);
    color: var(--_badge-color);
}

.badge.bg-success {
    --_badge-bg: var(--semantic-success);
    --_badge-color: hsl(0 0% 100%);
}
```

### 3. Modulos — Componem variantes

Modulos NAO duplicam logica de tema. Apenas overridam `--_X` da API:

```css
/* modules/_meu-modulo.css */
@layer modules {
  .meu-badge-customizado {
    --_badge-bg: hsl(220 70% 35%);
    --_badge-color: hsl(0 0% 100%);
  }
}
```

---

## Adicionar Novo CSS

### Em modulo existente

1. Editar `modules/_<modulo>.css` (ja importado em `main.css`).
2. Usar tokens: `var(--bg-light)`, `var(--text)`, `var(--semantic-X)`, `var(--amber-XX)`.
3. NAO usar hex literal, NAO usar `--bs-*-text-emphasis | bg-subtle | border-subtle`.

### Para novo modulo

1. Criar `modules/_novo-modulo.css`.
2. Wrap em `@layer modules { ... }`.
3. Adicionar `@import` em `main.css` (na secao "Modules").
4. Componer via API custom-property (nao redefinir cores absolutas).

### Para novo COMPONENTE global

1. Criar `components/_novo.css`.
2. Wrap em `@layer components { ... }`.
3. Expor API `--_X` privada (com prefixo `_` para indicar "interna").
4. Adicionar `@import` em `main.css`.

---

## Bootstrap 5.3 — Notas

- Self-hosted em `vendor/bootstrap.min.css`.
- Carregado dentro de `@layer bootstrap` (primeira posicao no order).
- Mapping `--bs-*` definido em `tokens/_design-tokens.css` para AMBOS os temas.
- Overrides especificos em `base/_bootstrap-overrides.css` (badges/tables/btns/modais).

---

## Auditoria

Script: `scripts/audits/ui_audit.py`

```bash
# Roda audit completo (3 outputs em relatorios/)
python scripts/audits/ui_audit.py

# Apenas FINDINGS (catalogo + recomendacoes)
python scripts/audits/ui_audit.py --findings-only

# Escopo restrito
python scripts/audits/ui_audit.py --templates-dir app/templates/hora
```

Outputs:

| Arquivo | Conteudo |
|---|---|
| `relatorios/ui_audit_<data>.json` | machine-readable (todas violacoes) |
| `relatorios/ui_audit_<data>.md` | top hotspots (humano) |
| `relatorios/ui_audit_FINDINGS_<data>.md` | catalogo + dups + recomendacoes |

Codigos detectados (V1-V14): ver Secao 6 do `GUIA_COMPONENTES_UI.md`.

---

## Regras de Ouro

1. **Nunca** hex hardcoded em template ou CSS modulo. Use tokens.
2. **Nunca** `--bs-*-text-emphasis | bg-subtle | border-subtle` em modulo (Bootstrap-native, nao tematizado).
3. **Sempre** API custom-property em variants (`--_badge-bg`, `--_btn-bg`, `--_row-bg`).
4. **Sempre** testar em light + dark mode apos alteracao.
5. **Sempre** rodar `ui_audit.py` antes de commit (e nao adicionar novas violacoes).
6. **Componentes globais** vao em `components/`, **estilos por modulo** em `modules/`.

---

## Cache Busting

`base.html` adiciona `?v=N` em links CSS. Incrementar quando:

- Tokens mudam (`tokens/_design-tokens.css`).
- Layer order muda (`main.css`).
- Adicao/remocao de imports em `main.css`.

Mudancas dentro de `modules/_X.css` em geral nao precisam bump (o navegador respeita
`Cache-Control` do servidor + ETag).

---

## Historico

| Data | Versao | Descricao |
|---|---|---|
| 2026-05-06 | 3.0.0 | README reescrito. Antigo `_variables.css` removido ha tempo (substituido por `tokens/_design-tokens.css`). Documentacao agora reflete arquitetura @layer real. Antigo `MAPEAMENTO_CORES.md` descomissionado (stub redirect). FONTE UNICA: `GUIA_COMPONENTES_UI.md` |
| 2025-12-18 | 2.2.0 | Cache busting `?v=6`, badges de filtro |
| 2025-12-17 | 2.0.0 | Reorganizacao com `_variables.css` (depois substituido) |
