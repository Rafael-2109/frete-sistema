# UI Dimension Analysis — Design System Coverage
**Data**: 2026-05-06

Analise das **dimensoes que o ui_audit.py NAO cobria** — bugs visuais
invisiveis a regex tatico (contraste WCAG, vars BS nao tematizadas,
inconsistencia semantica de headers, etc).

Este documento eh insumo para a Etapa 2-7 do plano de unificacao.

## 1. Tokens auto-validados (WCAG)

Calcula contraste WCAG entre cada par bg/text que o design system EXIGE.
**FAIL** = abaixo de AA 4.5:1 (texto normal). Tokens com FAIL precisam
ser recalibrados.

**0 pares com FAIL contraste (de 30 totais)**

| Tema | Background | Text | Ratio | Status | Descricao |
|---|---|---|---:|---|---|
| light | `bg-dark` | `text` | 15.53 | ✅ AAA | body sobre dark bg |
| light | `bg` | `text` | 17.43 | ✅ AAA | surface sobre bg |
| light | `bg-light` | `text` | 19.47 | ✅ AAA | card/input sobre bg-light |
| light | `bg-button` | `text` | 17.04 | ✅ AAA | button neutro |
| light | `bg-light` | `text-muted` | 8.52 | ✅ AAA | texto secundario em card |
| light | `semantic-success` | `white` | 5.09 | ✓ AA | badge bg-success + texto branco |
| light | `semantic-danger` | `white` | 7.13 | ✅ AAA | badge bg-danger + texto branco |
| light | `semantic-info` | `white` | 8.04 | ✅ AAA | badge bg-info + texto branco |
| light | `amber-50` | `dark10` | 10.44 | ✅ AAA | badge bg-warning + texto escuro |
| light | `amber-55` | `dark10` | 12.27 | ✅ AAA | btn-primary + texto escuro |
| light | `bs-success` | `white` | 5.09 | ✓ AA | bg-success + texto branco |
| light | `bs-danger` | `white` | 7.13 | ✅ AAA | bg-danger + texto branco |
| light | `bs-warning` | `dark10` | 10.44 | ✅ AAA | bg-warning + texto escuro |
| light | `bs-info` | `white` | 8.04 | ✅ AAA | bg-info + texto branco |
| light | `bs-primary` | `dark10` | 10.44 | ✅ AAA | bg-primary (amber) + texto escuro |
| dark | `bg-dark` | `text` | 18.80 | ✅ AAA | body sobre dark bg |
| dark | `bg` | `text` | 17.43 | ✅ AAA | surface sobre bg |
| dark | `bg-light` | `text` | 15.66 | ✅ AAA | card/input sobre bg-light |
| dark | `bg-button` | `text` | 13.50 | ✅ AAA | button neutro |
| dark | `bg-light` | `text-muted` | 8.30 | ✅ AAA | texto secundario em card |
| dark | `semantic-success` | `white` | 5.09 | ✓ AA | badge bg-success + texto branco |
| dark | `semantic-danger` | `white` | 7.13 | ✅ AAA | badge bg-danger + texto branco |
| dark | `semantic-info` | `white` | 8.04 | ✅ AAA | badge bg-info + texto branco |
| dark | `amber-50` | `dark10` | 10.44 | ✅ AAA | badge bg-warning + texto escuro |
| dark | `amber-55` | `dark10` | 12.27 | ✅ AAA | btn-primary + texto escuro |
| dark | `bs-success` | `white` | 5.09 | ✓ AA | bg-success + texto branco |
| dark | `bs-danger` | `white` | 7.13 | ✅ AAA | bg-danger + texto branco |
| dark | `bs-warning` | `dark10` | 10.44 | ✅ AAA | bg-warning + texto escuro |
| dark | `bs-info` | `white` | 8.04 | ✅ AAA | bg-info + texto branco |
| dark | `bs-primary` | `dark10` | 12.27 | ✅ AAA | bg-primary (amber) + texto escuro |

## 2. Vars Bootstrap raras / nao tematizadas

Vars como `--bs-purple`, `--bs-cyan`, `--bs-X-bg-subtle`, `--bs-X-text-emphasis`
usadas em templates ou modulos. **Nao sao tematizadas** pelo design system —
herdam Bootstrap default (cores arbitrarias, podem violar contraste em dark).

**6 usos** em 4 arquivos.

| Var | Ocorrencias | Tipo | Onde |
|---|---:|---|---|
| `var(--bs-warning-bg-subtle)` | 3 | NAO-TEMATIZADA | templates=3, css=0 |
| `var(--bs-success-bg-subtle)` | 2 | NAO-TEMATIZADA | templates=2, css=0 |
| `var(--bs-danger-bg-subtle)` | 1 | NAO-TEMATIZADA | templates=1, css=0 |

**Acao**: tematizar essas vars no `_design-tokens.css` em ambos os blocos
`[data-bs-theme=light]` e `[data-bs-theme=dark]`, OU bani-las do vocabulario.

## 3. Classes Bootstrap pastel (`bg-X-subtle`, `bg-opacity-N`)

Classes Bootstrap que aplicam cores pastel **nao tematizadas pelo design system**.
No dark mode podem virar tons claros que conflitam com texto branco/escuro herdado.

**84 ocorrencias** em 25 arquivos.

| Classe | Ocorrencias |
|---|---:|
| `bg-opacity-10` | 35 |
| `bg-success-subtle` | 16 |
| `bg-info-subtle` | 15 |
| `bg-warning-subtle` | 10 |
| `bg-danger-subtle` | 4 |
| `bg-primary-subtle` | 2 |
| `bg-opacity-75` | 1 |
| `bg-opacity-25` | 1 |

## 4. Headers (modal-header / card-header) — catalogo de variantes

Quantas variantes visuais coexistem para o mesmo elemento semantico?
Cada signature distinta = 1 variante. **Quanto mais variantes, mais inconsistencia.**

### `card-header` — 19 variantes em 969 ocorrencias

| Signature | Ocorrencias | Sample |
|---|---:|---|
| `NEUTRO` | 868 | `app/templates/monitoramento/visualizar_entrega.html:705` |
| `bg-light` | 51 | `app/templates/hora/nf_detalhe.html:95` |
| `bg-transparent` | 19 | `app/templates/main/dashboard.html:136` |
| `bg-opacity-10+bg-opacity-10` | 9 | `app/templates/comercial/analise_margem.html:355` |
| `bg-white` | 6 | `app/templates/bi/despesas.html:84` |
| `bg-warning+text-dark` | 2 | `app/templates/monitoramento/visualizar_entrega.html:385` |
| `bg-info-subtle` | 2 | `app/templates/carvia/detalhe_operacao.html:103` |
| `bg-light+bg-secondary+bg-success+bg-warning+text-dark+text-dark+text-white+text-white` | 1 | `app/templates/portaria/detalhes_veiculo.html:156` |
| `bg-gradient` | 1 | `app/templates/fretes/visualizar_email.html:29` |
| `bg-info-subtle+text-info-emphasis` | 1 | `app/templates/estoque/listar_movimentacoes.html:703` |
| `bg-gradient-danger` | 1 | `app/templates/faturamento/dashboard_faturamento.html:167` |
| `bg-gradient-warning` | 1 | `app/templates/faturamento/dashboard_faturamento.html:220` |
| `bg-opacity-25+bg-warning+bg-opacity-25` | 1 | `app/templates/hora/tagplus/parser_append.html:60` |
| `bg-opacity-10+bg-success+bg-opacity-10` | 1 | `app/templates/pedidos/_partials/_modais.html:170` |
| `bg-opacity-10+bg-warning+bg-opacity-10` | 1 | `app/templates/pedidos/_partials/_modais.html:206` |
| `bg-info+bg-opacity-10+bg-opacity-10` | 1 | `app/templates/pedidos/_partials/_modais.html:243` |
| `bg-primary-subtle` | 1 | `app/templates/carvia/nfs/detalhe.html:327` |
| `bg-primary+text-white` | 1 | `app/templates/carvia/aprovacoes/processar.html:164` |
| `bg-opacity-10+bg-primary+bg-opacity-10` | 1 | `app/templates/carvia/subcontratos/detalhe.html:619` |

### `modal-header` — 5 variantes em 351 ocorrencias

| Signature | Ocorrencias | Sample |
|---|---:|---|
| `NEUTRO` | 347 | `app/templates/monitoramento/visualizar_entrega.html:197` |
| `bg-danger+text-white` | 1 | `app/templates/hora/nf_detalhe.html:571` |
| `bg-light` | 1 | `app/templates/recebimento/primeira_compra.html:291` |
| `bg-opacity-10+bg-opacity-10` | 1 | `app/templates/carvia/detalhe_operacao.html:639` |
| `bg-primary+text-white` | 1 | `app/templates/carvia/faturas_transportadora/conferir.html:379` |

## 5. `<style>` blocks em templates

Convencao DEV: nao usar `<style>` em template — CSS deve viver em `modules/_X.css`.

**22 blocks** em 22 templates.

| Arquivo | Linha | Tamanho | Preview |
|---|---:|---:|---|
| `app/templates/devolucao/termo_descarte.html` | 9 | 3509 | @page {             size: A4;             margin: 10mm 15mm;         }         * {             margin: 0;             pa |
| `app/templates/embarques/imprimir_separacao_carvia.html` | 7 | 1714 | @page { size: A4; margin: 1cm; }         body { font-family: Arial, sans-serif; font-size: 12px; line-height: 1.4; color |
| `app/templates/embarques/imprimir_embarque.html` | 7 | 3340 | @page {             size: A4;             margin: 1cm;         }                  body {             font-family: Arial, |
| `app/templates/embarques/imprimir_separacao.html` | 7 | 2596 | @page {             size: A4;             margin: 1cm;         }                  body {             font-family: Arial, |
| `app/templates/embarques/imprimir_completo.html` | 7 | 5891 | @page {             size: A4;             margin: 1cm;         }                  body {             font-family: Arial, |
| `app/templates/estoque/listar_movimentacoes.html` | 1002 | 793 | /* Dropdown de Sugestões de Produtos */ .dropdown-suggestions {     position: absolute;     top: 100%;     left: 0;      |
| `app/templates/estoque/saldo_estoque.html` | 702 | 1002 | .sortable {     cursor: pointer;     user-select: none; }  .sortable i {     font-size: 0.8em;     opacity: 0.6;     mar |
| `app/templates/recebimento/recebimento_fisico.html` | 250 | 2394 | .card-picking {         cursor: pointer;         transition: all 0.2s ease;         border-left: 4px solid var(--bs-succ |
| `app/templates/rastreamento/scanner_qrcode.html` | 12 | 3969 | * {             margin: 0;             padding: 0;             box-sizing: border-box;         }          body {         |
| `app/templates/rastreamento/confirmacao.html` | 12 | 2065 | body {             background: linear-gradient(135deg, var(--standalone-primary) 0%, var(--standalone-secondary) 100%);  |
| `app/templates/rastreamento/aceite_lgpd.html` | 16 | 4793 | body {             background: linear-gradient(135deg, var(--standalone-gradient-start) 0%, var(--standalone-gradient-en |
| `app/templates/rastreamento/erro.html` | 12 | 983 | body {             background: linear-gradient(135deg, var(--standalone-danger) 0%, hsl(354, 70%, 46%) 100%);            |
| `app/templates/rastreamento/questionario_entrega.html` | 14 | 7512 | body {             background: linear-gradient(135deg, var(--standalone-primary) 0%, var(--standalone-secondary) 100%);  |
| `app/templates/rastreamento/app_inicio.html` | 12 | 3812 | * {             margin: 0;             padding: 0;             box-sizing: border-box;         }          body {         |
| `app/templates/rastreamento/upload_canhoto.html` | 14 | 3132 | body {             background: linear-gradient(135deg, var(--standalone-gradient-start) 0%, var(--standalone-gradient-en |
| `app/templates/rastreamento/rastreamento_ativo.html` | 23 | 5636 | body {             background: linear-gradient(135deg, var(--standalone-primary) 0%, var(--standalone-secondary) 100%);  |
| `app/templates/pedidos/imprimir_separacao_antecipado.html` | 7 | 2685 | @page {             size: A4;             margin: 1cm;         }          body {             font-family: Arial, sans-se |
| `app/templates/motochefe/carga_inicial/historico.html` | 175 | 261 | .table-preview {     font-size: 0.85rem;     max-height: 400px;     overflow-y: auto; }  .table-preview th {     positio |
| `app/templates/motochefe/carga_inicial/index.html` | 245 | 718 | .card {         box-shadow: 0 2px 4px hsla(0, 0%, 0%, 0.1);     }     .card-header {         font-weight: 600;     }     |
| `app/templates/motochefe/cadastros/equipes/gerenciar_precos.html` | 219 | 360 | /* Destacar linhas com preço configurado */ .table-success {     background-color: hsla(var(--semantic-success-hsl), 0.1 |
| `app/templates/motochefe/vendas/pedidos/imprimir.html` | 7 | 7057 | /* Reset e configurações base */         * {             margin: 0;             padding: 0;             box-sizing: bord |
| `app/templates/motochefe/produtos/motos/imprimir_devolucao.html` | 7 | 3452 | /* Reset e configurações base */         * {             margin: 0;             padding: 0;             box-sizing: bord |

## 6. Cores via JavaScript

`.style.background = '...'` ou `.style.color = '...'` em JS — bypass total
do design system (visual snapshot pega so estado pos-render).

**3 ocorrencias.**

| Arquivo | Linha | Snippet |
|---|---:|---|
| `app/templates/financeiro/crud_abatimentos.html` | 420 | `.style.color = '#fff'` |
| `app/templates/carvia/nfs/_modal_inserir_nf_transferencia.html` | 163 | `.style.color = 'var(--semantic-success, #198754)'` |
| `app/static/js/shared/cnpj-lookup.js` | 85 | `.style.background = 'var(--bg-light, #f8f9fa)'` |

## 7. SVG inline com cor hardcoded

**9 ocorrencias.**

Cores mais usadas:

- `#1e40af`: 2 ocorrencias
- `#ffffff`: 2 ocorrencias
- `#ef4444`: 1 ocorrencias
- `#10b981`: 1 ocorrencias
- `#3b82f6`: 1 ocorrencias
- `#fbbf24`: 1 ocorrencias
- `#fde68a`: 1 ocorrencias

## 8. Cores condicionais Jinja

Patterns como `{{ '#XXX' if cond else '#YYY' }}` — cores hardcoded em logica template.

**4 ocorrencias.**

- `app/templates/embarques/imprimir_embarque.html:237` — `#1a73e8` ↔ `#d93025`
- `app/templates/embarques/_carvia_separacao_content.html:13` — `#1a73e8` ↔ `#d93025`
- `app/templates/embarques/imprimir_completo.html:336` — `#1a73e8` ↔ `#d93025`
- `app/templates/carvia/cotacoes/detalhe.html:373` — `#1a73e8` ↔ `#d93025`

## 9. Priorizacao Pareto (alcance da correcao)

Ordem por **valor / esforco** — comecar pelo topo:

| # | Valor | Esforco | Acao | Alcance |
|---:|---|---|---|---|
| 2 | ALTO | BAIXO | Tematizar 6 usos de --bs-X-bg-subtle/text-emphasis no _design-tokens.css | Todos templates que usam essas vars |
| 4 | ALTO | MEDIO | Substituir 84 bg-X-subtle/bg-opacity-N por classe canonical | N templates (criar 1-2 classes canonical, codemod massivo) |
| 5 | ALTO | ALTO | Unificar 24 variantes de header em 2-3 canonicas | 1320 ocorrencias em ~402 templates |
| 6 | MEDIO | ALTO | Migrar 22 <style> blocks de templates para CSS modulo | 22 templates |
| 7 | BAIXO | MEDIO | Substituir 3 `.style.background/color =` por toggle de classe | Pontos de manipulacao dinamica |

## 10. Pos-correcoes — pipeline preventivo

Para evitar regressao em PRs futuros:

1. **Lint bloqueador** (pre-commit + CI): rejeitar PR com
   - cor fora do vocabulario fechado (hex, rgb, var nao-canonical)
   - inline `style=color/background` em template
   - `bg-X-subtle | bg-opacity-N` (proibidos pos-unificacao)
   - combinacao bg+text com WCAG ratio < 4.5:1

2. **Visual analysis com axe-core** (Playwright integration):
   - rodar `axe.run()` em cada pagina capturada
   - reportar violacoes WCAG (cor + outras)

3. **Politica restritiva no GUIA_COMPONENTES_UI.md**:
   - vocabulario fechado de cores PERMITIDAS
   - lista explicita do que esta BANIDO
   - exemplos de violacoes + correcao
