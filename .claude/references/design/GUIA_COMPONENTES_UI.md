# Guia de Componentes UI — Nacom Goya Design System

**Ultima Atualizacao**: 2026-05-06
**Status**: FONTE UNICA — substitui o antigo `MAPEAMENTO_CORES.md`

> **Consulte ANTES** de criar/alterar badges, botoes, tabelas ou qualquer elemento colorido.
> Para arquitetura CSS (pastas, @layer, build): ver `app/static/css/README.md`.
> Para auditar codigo existente: ver `scripts/audits/ui_audit.py` + `relatorios/ui_audit_FINDINGS_<data>.md`.

---

## 0. TL;DR — Antes de Codar

**Resumo**: o design system tem **vocabulario fechado** validado em WCAG.
PRs que violem sao **bloqueados pelo pre-commit hook** (`scripts/hooks/pre-commit-ui-lint.sh`).

### Regras blockantes (ver Secao 6 — codigos P1-P9)

1. **NUNCA** hex literal (`#abc`, `#aabbcc`) em template ou CSS modulo (use tokens)
2. **NUNCA** `rgb()/rgba()/hsl()/hsla()` literal em CSS modulo fora de `var(...)` (use tokens)
3. **NUNCA** inline `style="color/background: ..."` em template (use classe canonical)
4. **NUNCA** `<style>` block em template (mover para `css/modules/_X.css`)
5. **NUNCA** `var(--bs-purple|pink|cyan|orange|teal|indigo|red|green|blue|yellow|gray|black|white)` — Bootstrap-default, nao tematizado
6. **NUNCA** `var(--bs-X-text-emphasis|bg-subtle|border-subtle)` em CSS modulo (use `--semantic-X-*` ou tokens proprios)
7. **NUNCA** `bg-warning text-white`, `bg-light text-white`, `bg-info text-dark` (combinacoes ilegiveis)
8. **NUNCA** `!important` em CSS modulo (so em `tokens/`, `legacy/`, `utilities/_legacy.css`)

### Boas praticas

9. Use API canonical: `--_badge-bg/color`, `--_btn-bg/color`, `--_row-bg`
10. Para badges: prefira classes de `_badges.css` (Secao 2.3)
11. Para tabelas com row colorida: `.table-success/warning/primary/danger/info/secondary` (Secao 4.1)
12. `text-white | text-dark | text-light` em badges Bootstrap eh REDUNDANTE — `_bootstrap-overrides.css:675-687` ja forca contraste. Codemod V6 ja removeu existentes.
13. **Sempre** teste em DARK e LIGHT mode antes de commitar
14. Rode `python scripts/audits/ui_policy_lint.py --enforce-new` antes de PR (ou instale o pre-commit hook)

---

## 1. Arquitetura (resumo executivo)

```
@layer bootstrap, reset, tokens, base, components, modules, utilities;

app/static/css/
├── main.css                       # entry point: declara @layer + @import
├── tokens/_design-tokens.css      # FONTE UNICA de tokens HSL (light/dark)
├── base/_bootstrap-overrides.css  # ajustes Bootstrap (badges/tables/modals)
├── base/_navbar.css
├── components/                    # componentes globais theme-aware
│   ├── _badges.css                # API --_badge-bg/color/border
│   ├── _buttons.css               # API --_btn-bg/color
│   ├── _tables.css                # API --_table-bg/color/border-color
│   ├── _cards.css, _forms.css, _modals.css, _layout.css, _tags.css
├── modules/                       # estilos por modulo (_hora.css, _carvia.css, ...)
└── utilities/                     # _utilities.css, _legacy.css (compat BS4→5)
```

**Principio**: tokens decidem cor, componentes expoem API CSS custom-property, modulos
componem variantes via override de `--_X`.

---

## 2. Badges — Catalogo Canonical (`components/_badges.css`)

### 2.1 Variantes Bootstrap (filled)

Use estas classes diretamente. **Nao** acrescente `text-white|text-dark`.

| Classe | Cor de fundo | Cor de texto | Uso |
|---|---|---|---|
| `.badge.bg-primary` | amber-55 | escuro fixo | Acao principal, destaque |
| `.badge.bg-secondary` | cinza 40% | branco | Neutro |
| `.badge.bg-success` | semantic-success (light: hsl 145 65 35) | branco | Confirmado, OK |
| `.badge.bg-danger` | semantic-danger | branco | Erro, perigo |
| `.badge.bg-warning` | amber-50 | escuro fixo | Atencao, pendente |
| `.badge.bg-info` | cinza 45% (light: cinza 40%) | branco | Informativo neutro |
| `.badge.bg-light` | bg-light token | text token | Adapta tema |
| `.badge.bg-dark` | hsl 0 0 20 (light: 25) | claro fixo | Escuro fixo |

### 2.2 Variantes outline

`.badge-outline-primary | -secondary | -success | -danger | -warning | -info | -light | -dark`

### 2.3 Status canonical (use estes em vez de criar novos)

| Classe | Equivalente curto | Aliases | Cor |
|---|---|---|---|
| `.badge-status-pendente` | `.badge-pendente` | — | amber-50 + escuro |
| `.badge-status-aprovado` | `.badge-aprovado` | `.badge-status-conferido`, `.badge-conferido` | success + branco |
| `.badge-status-rejeitado` | `.badge-rejeitado` | `.badge-status-reprovado`, `.badge-reprovado` | danger + branco |
| `.badge-status-pago` | `.badge-pago` | `.badge-status-lancado`, `.badge-lancado` | amber-55 + escuro |
| `.badge-status-cancelado` | `.badge-cancelado` | — | cinza 40% + branco |
| `.badge-status-rascunho` | `.badge-rascunho` | — | bg-light + texto + borda |
| `.badge-status` | base neutro | — | bg-light + texto + borda |
| `.badge-status-accent` | destaque amarelo | — | amarelo brilhante + escuro |

> **Regra de ouro**: se o status que voce precisa for sinonimo de algum acima
> (ex: "concluido" ≈ aprovado, "validado" ≈ conferido), reuse o canonical.

### 2.4 Quando criar uma classe nova

Apenas quando o status for genuinamente diferente. Use a API canonical:

```css
@layer modules {
  .badge-status-em_transito {
    --_badge-bg: hsl(220 70% 35%);
    --_badge-color: hsl(0 0% 100%);
  }

  /* Ajuste light mode (WCAG 4.5:1) */
  [data-bs-theme="light"] .badge-status-em_transito,
  [data-theme="light"] .badge-status-em_transito {
    --_badge-bg: hsl(220 70% 30%);
  }
}
```

**NAO** faca:
```css
/* RUIM — usa var Bootstrap-native nao tematizada (V14) */
.badge-meu-status { color: var(--bs-warning-text-emphasis); }

/* RUIM — overrida propriedades direto, ignorando API */
.badge-meu-status { background-color: ...; color: ...; }

/* RUIM — duplica canonical (V11.2) */
.modulo-badge-pago { ... }  /* use .badge-pago */
```

### 2.5 Erros comuns

| Erro | Por que | Correcao |
|---|---|---|
| `<span class="badge bg-warning text-dark">` | `_bootstrap-overrides.css` ja forca texto escuro em `bg-warning` (em ambos os temas) | `<span class="badge bg-warning">` |
| `<span class="badge bg-success text-white">` | `--_badge-color` ja eh branco | `<span class="badge bg-success">` |
| `<span class="badge bg-warning text-white">` | Anti-padrao de baixo contraste (V7) | `<span class="badge bg-warning">` |
| `<span class="badge" style="background-color: #ffc107;">` | Inline style cor (V1/V2) | `<span class="badge bg-warning">` |
| Badge customizado em modulo com sufixo igual a canonical | Duplica regra (V11) | Reusar canonical |

---

## 3. Botoes — `components/_buttons.css`

### 3.1 Mapeamento semantico

| Intencao | Classe | Texto | Exemplo |
|---|---|---|---|
| Acao principal | `btn-primary` | escuro fixo | "Salvar", "Criar" |
| Acao secundaria | `btn-secondary` | tema | "Cancelar", "Voltar" |
| Confirmar/aprovar | `btn-success` | branco | "Aprovar", "Confirmar" |
| Excluir/perigo | `btn-danger` | branco | "Excluir", "Rejeitar" |
| Atencao/aguardar | `btn-warning` | escuro fixo | "Pendente", "Revisar" |
| Informativo | `btn-info` | branco | (raro) |
| Header amber | `btn-outline-light` | claro | botao sobre `bg-primary` |

### 3.2 Outline em headers `bg-primary`

Quando o card-header usa `bg-primary` (fundo amber), use `btn-outline-light`:

```html
<div class="card-header bg-primary">
  <button class="btn btn-outline-light btn-sm">Filtros</button>
</div>
```

### 3.3 Erros comuns

| Erro | Correcao |
|---|---|
| `btn-primary text-white` | `btn-primary` (texto ja escuro fixo) |
| `btn-success text-white` | `btn-success` (`--_btn-color` ja eh branco) |
| `btn-warning` para "Excluir" | `btn-danger` (warning = atencao, nao perigo) |
| `btn-primary` para badge de status | usar `badge-*` em vez de `btn-*` |

---

## 4. Tabelas — `components/_tables.css`

### 4.1 Row classes canonicais

Definidas com `--_row-bg` + `--_row-hover-bg` (HSLA, semi-transparente sobre tema):

| Classe | Cor | Uso |
|---|---|---|
| `.table-success` | verde 15% / 28% hover | Status concluido/aprovado |
| `.table-warning` | amarelo 15% / 28% hover | Status pendente/atencao |
| `.table-primary` | amber 15% / 28% hover | Status destacado |
| `.table-danger` | vermelho 15% / 28% hover | Status erro/cancelado |
| `.table-info` | ciano 15% / 28% hover | Status informativo |

### 4.2 NAO use ainda

`.table-secondary`, `.table-light`, `.table-dark` — **nao estao no canonical**. Usam Bootstrap-default que quebra hierarquia de elevacao no dark mode.

> Se precisar dessas variantes, abra issue para serem canonicalizadas em `_tables.css`
> antes de usar. Audit `V12` reporta uso atual (~214 ocorrencias).

### 4.3 Coluna utilities

```html
<th class="col-pedido">Pedido</th>
<th class="col-cnpj">CNPJ</th>
<th class="col-data">Data</th>
<th class="col-valor">Valor</th>
<th class="col-acoes">Acoes</th>
```

Lista completa em `components/_tables.css`: `col-id, col-pedido, col-cnpj, col-data, col-data-input, col-valor, col-qtd, col-peso, col-uf, col-status, col-acoes, col-check, col-nome, col-nome-lg, col-cidade, col-obs, col-nowrap`.

### 4.4 Sticky header

`<table class="table">` ja vem com sticky header em `<thead th>`. Para sticky col tambem:

```html
<table class="table table-sticky-both">...</table>
```

---

## 5. Cores Reais Neste Sistema (recap)

**Atencao**: nomes Bootstrap NAO correspondem a cores Bootstrap default!

| Classe Bootstrap | Cor REAL | Token | Hue |
|---|---|---|---|
| `*-primary` | amber (NAO azul) | `var(--amber-55)` | 60 |
| `*-secondary` | cinza neutro | `hsl(0 0% 40%)` | 0 |
| `*-success` | verde | `var(--semantic-success)` | 145 |
| `*-danger` | vermelho coral | `var(--semantic-danger)` | 350 |
| `*-warning` | amarelo-chartreuse | `var(--amber-50)` | 60 |
| `*-info` | cinza medio (NAO azul) | `hsl(0 0% 45%)` | 0 |
| `*-light` | adapta tema | `var(--bg-light)` | — |
| `*-dark` | escuro fixo | `hsl(0 0% 20%)` | 0 |

---

## 6. Antipatterns Catalogados

Codigos do `ui_audit.py` (ver `scripts/audits/ui_audit.py`):

### Audit numerico (`ui_audit.py`) — codigos catalogo

| Codigo | Antipattern | Como evitar |
|---|---|---|
| `V1` | Inline style com cor | usar classe canonical |
| `V2` | Hex literal em template | usar token via classe |
| `V3` | Hex em CSS modulo | usar token de `_design-tokens.css` |
| `V4` | rgb/rgba/hsla literal em CSS modulo | usar `var(--token)` ou `hsla()` baseado em token |
| `V5` | `!important` fora de tokens/legacy | corrigir especificidade ou layer |
| `V6` | `badge bg-X text-Y` redundante | so `badge bg-X` (canonical resolve) |
| `V7` | Combinacao baixo contraste | trocar para par valido |
| `V11` | Duplicacao de classe badge cross-modulo | consolidar em canonical |
| `V12` | `table-secondary/light/dark` em template | usar canonical (agora todos disponiveis) |
| `V14` | `--bs-*-text-emphasis/bg-subtle/border-subtle` em modulo | usar token semantico |

### Policy lint (`ui_policy_lint.py`) — codigos blockantes

| Codigo | Regra | Em |
|---|---|---|
| `P1` | hex literal em template | template |
| `P2` | hex literal em CSS modulo | css/modules/, css/utilities/ |
| `P3` | inline `style="color/background: ..."` em template | template |
| `P4` | `<style>` block em template | template |
| `P5` | `var(--bs-purple/pink/cyan/orange/teal/indigo/etc)` — Bootstrap nao tematizado | template + css modulo |
| `P6` | `var(--bs-X-text-emphasis/bg-subtle/border-subtle)` em CSS modulo | css/modules/, css/utilities/ |
| `P7` | combinacao bg+text antagonista (bg-warning text-white, etc.) | template |
| `P8` | `!important` em CSS modulo | css/modules/, css/components/ |
| `P9` | `rgb()/rgba()/hsl()/hsla()` literal em CSS modulo (sem var) | css/modules/, css/utilities/ |

Rodar audit: `python scripts/audits/ui_audit.py` (gera 3 reports em `relatorios/`).
Rodar policy lint: `python scripts/audits/ui_policy_lint.py --report-only` (lista todas violacoes blockantes do codebase).
Rodar dimension analysis: `python scripts/audits/ui_dimension_analysis.py` (WCAG ratio dos tokens + catalogo headers/dimensoes).

### Regression check (pre-commit / CI)

Dois niveis complementares:

**1. Audit numerico** (`scripts/audits/ui_audit_regression.py`):

```bash
python scripts/audits/ui_audit_regression.py            # antes de commit
python scripts/audits/ui_audit_regression.py --update-baseline  # apos cleanup
```

Detecta se a contagem de violacoes aumentou. Rapido, mas NAO detecta mudanca visual.

**2. Visual regression** (`tests/visual/`):

```bash
# uma vez (estabelecer baseline)
python tests/visual/capture.py --target baseline

# antes de cada PR de cleanup
python tests/visual/capture.py --target current
python tests/visual/compare.py
# exit 0 = OK, exit 1 = pixel diff > threshold

# apos cleanup que mudou visual de proposito
python tests/visual/compare.py --update-baseline
```

Pre-requisitos: app rodando local + `UI_VISUAL_EMAIL` / `UI_VISUAL_PASSWORD` env vars +
`python -m playwright install chromium`. Detalhes em `tests/visual/README.md`.

**Quando usar cada um**:
- Audit numerico: SEMPRE antes de commit (rapido, sem dependencias)
- Visual: antes de PRs que alteram CSS/templates em volume (Fase E codemod)

---

## 7. Checklist Pre-Implementacao

Antes de escrever badge/botao/tabela colorida:

- [ ] Identifiquei a INTENCAO semantica (acao? status? severidade?)
- [ ] Verifiquei se ja existe classe canonical (Secao 2 / 3 / 4)
- [ ] Se classe nova: usei API `--_badge-bg/color`, `--_btn-bg/color`, ou `--_row-bg`
- [ ] Nao usei `--bs-*-text-emphasis | bg-subtle | border-subtle`
- [ ] Nao adicionei `text-white | text-dark` redundante
- [ ] Nao usei inline style com cor
- [ ] Testei em DARK mode E em LIGHT mode
- [ ] Rodei `python scripts/audits/ui_audit_regression.py` (deve retornar 0)

---

## 8. Quando Atualizar Este Documento

- Adicionou status canonical novo em `components/_badges.css` → atualizar Secao 2.3
- Adicionou row class em `components/_tables.css` → atualizar Secao 4.1
- Adicionou nova categoria de antipattern → atualizar Secao 6 + estender `ui_audit.py`
- Mudou semantica de classe Bootstrap → atualizar Secao 5

Mantenedor: dev que estiver alterando design system. Nao adie atualizacao para depois.
