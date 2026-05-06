# UI Audit — FINDINGS Consolidados
**Data**: 2026-05-06

**Arquivos escaneados**: 569 templates, 57 CSS
**Total de violacoes (V1-V10) + catalogo (V12, V14)**: 2784

> Este documento e um espelho legivel do estado atual. Para violacoes automatizaveis ver `ui_audit_<data>.md` (top hotspots).
> Para regras de uso correto ver `.claude/references/design/GUIA_COMPONENTES_UI.md`.

## 1. Sumario por categoria
| Codigo | Descricao | Total |
|---|---|---:|
| `V4_rgb_in_css` | rgb/rgba/hsl literal em CSS (preferir token) | 1431 |
| `V6_badge_bg_text_combo` | Badge com bg-* + text-* (derruba design system) | 440 |
| `V5_important_in_css` | !important em CSS fora de tokens/_legacy | 308 |
| `V1_inline_style_color` | Inline style com cor (color/background/border) | 245 |
| `V12_table_row_class` | Uso de table-secondary/light/dark/info em row | 214 |
| `V3_hex_in_css_module` | Hex literal em CSS fora de tokens/vendor | 71 |
| `V2_hex_in_template` | Hex literal dentro de style= em template | 70 |
| `V7_text_bg_combo` | Combinacao bg + text antagonistica (baixo contraste) | 3 |
| `V14_untokenized_bs_var` | Var Bootstrap-native nao tematizada pelo design system | 2 |

## 2. Catalogo de classes badge

Lista todas as classes `*badge*` definidas em `components/` (canonical) e `modules/` (modulo-especifico). Identifica duplicacao real (mesmo nome em multiplos arquivos) e duplicacao semantica (sufixo equivalente a um status canonical).

### 2.1 Duplicacao REAL (mesmo nome em 2+ arquivos distintos): 3
| Classe | Arquivos | Recomendacao |
|---|---|---|
| `.score-badge` | `app/static/css/modules/_bi.css:186` (modulo), `app/static/css/modules/_pallet.css:1921` (modulo) | Consolidar em canonical ou prefixar com modulo |
| `.status-badge` | `app/static/css/modules/_financeiro.css:369` (modulo), `app/static/css/modules/_fretes.css:490` (modulo), `app/static/css/modules/_recebimento.css:244` (modulo), `app/static/css/modules/_pallet.css:1816` (modulo) | Consolidar em canonical ou prefixar com modulo |
| `.tipo-badge` | `app/static/css/modules/_pallet.css:1850` (modulo), `app/static/css/modules/custeio/custeio.css:10` (modulo) | Consolidar em canonical ou prefixar com modulo |

### 2.2 Duplicacao SEMANTICA (sufixo equivale a status canonical mas vive em modulo)
Estes deveriam reusar a classe canonical de `_badges.css` em vez de redefinir.

| Classe modulo | Sufixo | Definida em | Canonical equivalente |
|---|---|---|---|
| `.carvia-badge-aprovado` | `aprovado` | `app/static/css/modules/_carvia.css:124` | `.badge-status-aprovado` ou `.badge-aprovado` |
| `.carvia-badge-cancelado` | `cancelado` | `app/static/css/modules/_carvia.css:56` | `.badge-status-cancelado` ou `.badge-cancelado` |
| `.carvia-badge-conferido` | `conferido` | `app/static/css/modules/_carvia.css:74` | `.badge-status-conferido` ou `.badge-conferido` |
| `.carvia-badge-pago` | `pago` | `app/static/css/modules/_carvia.css:99` | `.badge-status-pago` ou `.badge-pago` |
| `.carvia-badge-pendente` | `pendente` | `app/static/css/modules/_carvia.css:61` | `.badge-status-pendente` ou `.badge-pendente` |
| `.carvia-badge-rascunho` | `rascunho` | `app/static/css/modules/_carvia.css:31` | `.badge-status-rascunho` ou `.badge-rascunho` |
| `.extrato-badge--pendente` | `pendente` | `app/static/css/modules/_financeiro.css:842` | `.badge-status-pendente` ou `.badge-pendente` |
| `.match-badge--pendente` | `pendente` | `app/static/css/modules/_financeiro.css:800` | `.badge-status-pendente` ou `.badge-pendente` |
| `.status-badge--aprovado` | `aprovado` | `app/static/css/modules/_financeiro.css:391` | `.badge-status-aprovado` ou `.badge-aprovado` |

### 2.3 Inventario completo por arquivo

**`app/static/css/modules/_bi.css`** (3 classes):

- L186: `.score-badge`
- L301: `.uf-badge`
- L366: `.setor-badge`

**`app/static/css/modules/_carteira.css`** (4 classes):

- L72: `.cart-filter-badge`
- L83: `.cart-filter-badge`
- L90: `.cart-filter-badge--active`
- L95: `.cart-filter-badge--active`

**`app/static/css/modules/_carvia.css`** (35 classes):

- L31: `.carvia-badge-rascunho`
- L36: `.carvia-badge-cotado`
- L41: `.carvia-badge-confirmado`
- L46: `.carvia-badge-faturado`
- L51: `.carvia-badge-ativa`
- L56: `.carvia-badge-cancelado`
- L61: `.carvia-badge-pendente`
- L70: `.carvia-badge-vinculado_ft`
- L74: `.carvia-badge-conferido`
- L79: `.carvia-badge-divergente`
- L84: `.carvia-badge-emitida`
- L89: `.carvia-badge-emitido`
- L94: `.carvia-badge-paga`
- L99: `.carvia-badge-pago`
- L104: `.carvia-badge-recebido`
- L109: `.carvia-badge-cancelada`
- L114: `.carvia-badge-em-conferencia`
- L119: `.carvia-badge-enviado`
- L124: `.carvia-badge-aprovado`
- L129: `.carvia-badge-contra-proposta`
- L134: `.carvia-badge-separado`
- L139: `.carvia-badge-embarcado`
- L151: `.carvia-badge-transf-eh`
- L152: `.carvia-badge-transferencia`
- L173: `.carvia-badge-transf-veio`
- L195: `.carvia-badge-transferencia-lg`
- L464: `.carvia-fluxo-badge-receber`
- L470: `.carvia-fluxo-badge-pagar`
- L477: `.carvia-fluxo-badge-saldo`
- L736: `.carvia-badge-conciliado`
- L740: `.carvia-badge-parcial`
- L753: `.carvia-badge-score-alto`
- L758: `.carvia-badge-score-medio`
- L766: `.carvia-badge-xs`
- L771: `.carvia-badge-sm`

**`app/static/css/modules/_chat.css`** (3 classes):

- L25: `.chat-badge`
- L40: `.chat-badge--system`
- L46: `.chat-badge--user`

**`app/static/css/modules/_comercial.css`** (4 classes):

- L372: `.equipe-badge`
- L379: `.equipe-badge`
- L396: `.vendedor-badge`
- L403: `.vendedor-badge`

**`app/static/css/modules/_devolucao.css`** (2 classes):

- L99: `.devolucao-badge-data`
- L105: `.devolucao-badge-date`

**`app/static/css/modules/_embarques.css`** (4 classes):

- L229: `.agendamento-badge`
- L240: `.agendamento-badge`
- L381: `.agendamento-badge`
- L388: `.agendamento-badge`

**`app/static/css/modules/_financeiro.css`** (40 classes):

- L174: `.fin-section-link__badge`
- L181: `.fin-section-link__badge--new`
- L186: `.fin-section-link__badge--hot`
- L369: `.status-badge`
- L380: `.status-badge--importado`
- L385: `.status-badge--aguardando`
- L387: `.status-badge--aguardando_revisao`
- L391: `.status-badge--aprovado`
- L396: `.status-badge--processando`
- L401: `.status-badge--concluido`
- L406: `.status-badge--parcial`
- L411: `.status-badge--erro`
- L679: `.lote-tab__badge`
- L765: `.match-badge`
- L775: `.match-badge--encontrado`
- L780: `.match-badge--sem_match`
- L785: `.match-badge--ja_pago`
- L790: `.match-badge--nao_aplicavel`
- L795: `.match-badge--formato_invalido`
- L800: `.match-badge--pendente`
- L805: `.match-badge--processado`
- L810: `.match-badge--erro`
- L815: `.match-badge--conciliado`
- L822: `.extrato-badge`
- L832: `.extrato-badge--match`
- L837: `.extrato-badge--sem_match`
- L842: `.extrato-badge--pendente`
- L847: `.extrato-badge--conciliado`
- L852: `.extrato-badge--nao_aplicavel`
- L859: `.ocorrencia-badge`
- L867: `.ocorrencia-badge--06`
- L872: `.ocorrencia-badge--09`
- L874: `.ocorrencia-badge--10`
- L878: `.ocorrencia-badge--17`
- L1410: `.pipeline-badges`
- L1817: `.sem-match-section__badge`
- L1863: `.status-badge--sem_match`
- L1864: `.status-badge--formato_invalido`
- L2091: `.export-card__badge`
- L2101: `.export-card__badge--excel`

**`app/static/css/modules/_fretes.css`** (3 classes):

- L490: `.status-badge`
- L531: `.vinculado-badge`
- L536: `.nao-vinculado-badge`

**`app/static/css/modules/_hora.css`** (1 classes):

- L111: `.hora-badge-divergencia`

**`app/static/css/modules/_insights.css`** (3 classes):

- L731: `.session-modal-badges`
- L738: `.session-modal-badge`
- L985: `.session-tool-badge`

**`app/static/css/modules/_manufatura.css`** (3 classes):

- L83: `.tipo-badge-INTERMEDIARIO`
- L90: `.tipo-badge-COMPONENTE`
- L97: `.tipo-badge-ACABADO`

**`app/static/css/modules/_pallet-unified.css`** (12 classes):

- L290: `.pu-badge-empresa`
- L296: `.pu-badge-empresa--cd`
- L298: `.pu-badge-empresa--fb`
- L299: `.pu-badge-empresa--sc`
- L300: `.pu-badge-tipo`
- L306: `.pu-badge-tipo--transportadora`
- L308: `.pu-badge-tipo--cliente`
- L309: `.pu-badge-status`
- L315: `.pu-badge-status--ativa`
- L317: `.pu-badge-status--resolvida`
- L318: `.pu-badge-status--cancelada`
- L380: `.pu-docs-badge`

**`app/static/css/modules/_pallet.css`** (10 classes):

- L1816: `.status-badge`
- L1850: `.tipo-badge`
- L1884: `.vinculacao-badge`
- L1903: `.empresa-badge`
- L1921: `.score-badge`
- L2171: `.venda-totais-badge`
- L2377: `.pallet-status-badge`
- L2379: `.pallet-status-badge--ativa`
- L2380: `.pallet-status-badge--resolvida`
- L2381: `.pallet-status-badge--cancelada`

**`app/static/css/modules/_portal.css`** (2 classes):

- L57: `.portal-status-badge`
- L172: `.protocol-badge`

**`app/static/css/modules/_rastreamento-standalone.css`** (2 classes):

- L412: `.standalone-nf-badge`
- L632: `.standalone-status-badge`

**`app/static/css/modules/_recebimento.css`** (2 classes):

- L244: `.status-badge`
- L404: `.fase-badge`

**`app/static/css/modules/_seguranca.css`** (10 classes):

- L63: `.seg-badge-critica`
- L67: `.seg-badge-alta`
- L72: `.seg-badge-media`
- L77: `.seg-badge-baixa`
- L82: `.seg-badge-info`
- L90: `.seg-badge-status-aberta`
- L94: `.seg-badge-status-em_andamento`
- L99: `.seg-badge-status-resolvida`
- L104: `.seg-badge-status-aceita`
- L109: `.seg-badge-status-falso_positivo`

**`app/static/css/modules/custeio/custeio.css`** (2 classes):

- L10: `.tipo-badge`
- L415: `.linha-producao-badge`

**`app/static/css/modules/margem/margem.css`** (1 classes):

- L236: `.margem-badge`

## 3. Catalogo de uso de `table-secondary/light/dark/info`

`table-success/primary/warning/danger/info` estao tematizadas em `components/_tables.css`. **`table-secondary` e `table-light/dark` NAO estao** — usam default Bootstrap nativo, que quebra a hierarquia de elevacao no dark mode.

### `table-dark` — 34 usos — **FALTANDO em _tables.css canonical**

- `app/templates/portaria/dashboard.html:145` — `table-dark`
- `app/templates/portaria/dashboard.html:199` — `table-dark`
- `app/templates/embarques/acessar_separacao.html:135` — `table-dark`
- `app/templates/embarques/listar_embarques.html:240` — `table-dark`
- `app/templates/fretes/lancamento_freteiros.html:210` — `table-dark`
- `app/templates/fretes/lancamento_freteiros.html:310` — `table-dark`
- `app/templates/fretes/simulador.html:93` — `table-dark`
- `app/templates/fretes/auditoria_lancamentos.html:133` — `table-dark`
- `app/templates/estoque/listar_movimentacoes.html:172` — `table-dark`
- `app/templates/estoque/listar_movimentacoes.html:410` — `table-dark`
- `app/templates/estoque/listar_unificacao_codigos.html:66` — `table-dark`
- `app/templates/estoque/saldo_estoque.html:91` — `table-dark`
- `app/templates/estoque/saldo_estoque.html:494` — `table-dark`
- `app/templates/estoque/saldo_estoque.html:886` — `table-dark sticky-top`
- `app/templates/estoque/importar_unificacao_codigos.html:159` — `table-dark`
- `app/templates/veiculos/admin_veiculos.html:53` — `table-dark`
- `app/templates/tabelas/tabelas_frete.html:139` — `table-dark`
- `app/templates/pessoal/pluggy_dry_run.html:99` — `table-dark sticky-top`
- `app/templates/financeiro/listar_contas_receber.html:791` — `table-dark`
- `app/templates/rastreamento/detalhes.html:205` — `table-dark`
- ... e mais 14 ocorrencias

### `table-info` — 6 usos — OK (em _tables.css)

- `app/templates/hora/estoque_lista.html:344` — `{% if not m.moto_disponivel %}table-secondary text-muted{% elif m.ultimo_evento == 'AVARIADA' %}table-warning{% elif m.ultimo_evento == 'FALTANDO_PECA' %}table-`
- `app/templates/embarques/visualizar_embarque.html:339` — `table-info`
- `app/templates/fretes/lancamento_freteiros.html:281` — `table-info`
- `app/templates/carteira/mapa_pedidos.html:278` — `table-info sticky-top`
- `app/templates/recebimento/primeira_compra.html:611` — `table-info`
- `app/templates/pedidos/_partials/_modais.html:253` — `table-info sticky-top`

### `table-light` — 150 usos — **FALTANDO em _tables.css canonical**

- `app/templates/separacao/listar.html:130` — `table-light`
- `app/templates/hora/recebimento_detalhe.html:104` — `table-light`
- `app/templates/hora/recebimento_detalhe.html:236` — `table-light`
- `app/templates/hora/avarias_lista.html:59` — `table-light`
- `app/templates/hora/permissoes_lista.html:22` — `table-light`
- `app/templates/hora/permissoes_lista.html:130` — `table-light`
- `app/templates/hora/recebimento_wizard.html:249` — `table-light`
- `app/templates/hora/transferencia_detalhe.html:70` — `table-light`
- `app/templates/hora/transferencia_detalhe.html:99` — `table-light`
- `app/templates/hora/transferencias_lista.html:50` — `table-light`
- `app/templates/hora/transferencia_confirmar_wizard.html:36` — `table-light`
- `app/templates/portaria/dashboard.html:215` — `
              {% if registro.status == 'DENTRO' %}table-success
              {% elif registro.status == 'AGUARDANDO' %}table-warning
              {% elif reg`
- `app/templates/portaria/historico.html:156` — `
              {% if registro.status == 'SAIU' %}table-light
              {% elif registro.status == 'DENTRO' %}table-success
              {% elif registro.st`
- `app/templates/portaria/listar_motoristas.html:58` — `table-light`
- `app/templates/fretes/vincular_cte_manual_despesa.html:188` — `table-light`
- `app/templates/fretes/cte_cancelamento_pendencias.html:151` — `table-light`
- `app/templates/carteira/dashboard.html:130` — `table-light`
- `app/templates/carteira/dashboard.html:365` — `table-light`
- `app/templates/carteira/mapa_pedidos.html:211` — `table-light sticky-top`
- `app/templates/carteira/simples.html:122` — `table-light sticky-top`
- ... e mais 130 ocorrencias

### `table-secondary` — 24 usos — **FALTANDO em _tables.css canonical**

- `app/templates/hora/estoque_lista.html:344` — `{% if not m.moto_disponivel %}table-secondary text-muted{% elif m.ultimo_evento == 'AVARIADA' %}table-warning{% elif m.ultimo_evento == 'FALTANDO_PECA' %}table-`
- `app/templates/portaria/dashboard.html:215` — `
              {% if registro.status == 'DENTRO' %}table-success
              {% elif registro.status == 'AGUARDANDO' %}table-warning
              {% elif reg`
- `app/templates/portaria/historico.html:156` — `
              {% if registro.status == 'SAIU' %}table-light
              {% elif registro.status == 'DENTRO' %}table-success
              {% elif registro.st`
- `app/templates/comercial/lista_clientes.html:705` — `table-secondary`
- `app/templates/comercial/lista_clientes.html:714` — `table-secondary`
- `app/templates/comercial/lista_clientes.html:729` — `table-secondary`
- `app/templates/comercial/lista_clientes.html:738` — `table-secondary`
- `app/templates/carteira/mapa_pedidos.html:1891` — `table-secondary`
- `app/templates/cotacao/otimizador.html:157` — `table-secondary`
- `app/templates/cotacao/cotacao.html:87` — `table-secondary fw-bold`
- `app/templates/cotacao/resumo_frete.html:89` — `table-secondary`
- `app/templates/cotacao/resumo_frete.html:165` — `table-secondary`
- `app/templates/pessoal/configuracao.html:80` — `table-secondary grupo-header`
- `app/templates/financeiro/listar_contas_receber.html:985` — `table-secondary sticky-top`
- `app/templates/financeiro/listar_contas_receber.html:1036` — `table-secondary sticky-top`
- `app/templates/financeiro/listar_contas_receber.html:1055` — `table-secondary sticky-top`
- `app/templates/pedidos/cotacao_manual.html:50` — `table-secondary fw-bold`
- `app/templates/faturamento/listar_relatorios.html:322` — `{% if not r.ativo %}table-secondary text-muted{% endif %}`
- `app/templates/devolucao/ocorrencias/detalhe.html:1640` — `table-secondary`
- `app/templates/fretes/ctes/detalhe.html:216` — `table-secondary`
- ... e mais 4 ocorrencias

## 4. Vars Bootstrap-native nao tematizadas (V14)

Estas vars (`--bs-*-text-emphasis`, `--bs-*-bg-subtle`, `--bs-*-border-subtle`) vem do Bootstrap default e NAO sao tematizadas pelo design system. No dark mode podem retornar valores incompativeis (ex: `--bs-warning-text-emphasis` retorna `#ffda6a` no dark do Bootstrap, criando 'amarelo claro sobre amarelo solido' em badges com `bg: var(--bs-warning)`).

| Var | Ocorrencias | Arquivos |
|---|---:|---|
| `--bs-warning-text-emphasis` | 2 | `app/static/css/modules/_hora.css` |

## 5. Casos high-impact (curados)

Casos identificados manualmente que merecem prioridade pelo impacto visual.

### 5.1 Badge 'Parcialmente Faturado' ilegivel no dark mode

**Sintoma**: Em `/hora/pedidos`, dark mode, badge `Parcialmente Faturado` aparece como amarelo claro sobre amarelo solido (texto invisivel).

**Fonte**: `app/static/css/modules/_hora.css:129-133`
```css
.badge-status-parcialmente_faturado,
.badge-status-em_conferencia {
    background-color: var(--bs-warning);
    color: var(--bs-warning-text-emphasis, #664d03);
}
```

**Causa raiz**: `--bs-warning-text-emphasis` e Bootstrap-native, nao tematizada pelo design system. Fallback `#664d03` (escuro) so aplica se a var nao existir; mas Bootstrap define a var em ambos os temas com cores opostas (light: escuro, dark: claro).

**Como deveria estar** (API canonical com cor fixa):
```css
.badge-status-parcialmente_faturado,
.badge-status-em_conferencia {
    --_badge-bg: var(--amber-50);
    --_badge-color: hsl(0 0% 10%);  /* fixo: contraste em ambos os temas */
}
```

### 5.2 Tabela `/hora/estoque` com linhas que nao respeitam tema

**Sintoma**: Linhas com `class="table-secondary text-muted"` (motos fora de estoque) aparecem com fundo cinza claro Bootstrap-default em vez do tom escuro do tema.

**Fonte**: `app/templates/hora/estoque_lista.html:344`
```html
<tr class="{% if not m.moto_disponivel %}table-secondary text-muted{% elif ... %}">
```

**Causa raiz**: `_tables.css` e `_bootstrap-overrides.css` definem `.table-success/primary/warning/danger/info`. **`.table-secondary` nao esta no canonical** — usa o Bootstrap-default cinza-medio que ignora tokens.

**Como deveria estar**: adicionar em `components/_tables.css`:
```css
.table-secondary {
    --_row-bg: hsla(0 0% 50% / 0.10);
    --_row-hover-bg: hsla(0 0% 50% / 0.20);
    background-color: var(--_row-bg);
}
.table-secondary:hover { background-color: var(--_row-hover-bg); }
```

## 6. Recomendacoes consolidadas (proximas fases)

Esta auditoria foi gerada pela Fase A do plano. As fases seguintes (B/C/E/F) deverao consumir este documento.

### Fase B — Componentes canonicos
- `_badges.css`: adicionar status faltantes detectados em 2.2 (sufixo nao-canonical frequente em modulos: `aberto, faturado, em_andamento, em_separacao, em_transito, em_conferencia, parcialmente_faturado, com_divergencia, recebido, vendido, devolvido, reservado, avariado, ativo, resolvido, tratativa`)
- `_tables.css`: adicionar `.table-secondary` (e revisar se vale incluir overrides explicitos `.table-light/dark` em vez de manter no `_bootstrap-overrides.css`)
- Consolidar TODOS os overrides de tabela em `_tables.css` (mover de `_bootstrap-overrides.css` para reduzir fontes de verdade)

### Fase C — Refatorar modulos
- **`_hora.css`**: trocar `background-color/color` direto por API `--_badge-bg/color`; remover uso de `--bs-warning-text-emphasis` (substituir por `hsl(0 0% 10%)` fixo); deletar classes que duplicam canonical (ver tabela 2.1)
- **`_pallet-unified.css`**: migrar `pu-badge-status--*` para API canonical (mantendo prefixo `pu-` se variante visual 'tinted' for intencional)
- **`_carvia.css`**: ~40 badges com prefixo `carvia-badge-*` — auditar se podem reutilizar canonical (rascunho, confirmado, cancelado, pendente, conferido, aprovado)
- **`_seguranca.css`**: ja usa API correta, apenas auditar coverage

### Fase E — Templates
- Substituir `class="badge bg-X text-Y"` redundantes por `badge badge-status-X` (440 ocorrencias)
- Limpar inline styles com cor (245 ocorrencias)
- Substituir `table-secondary` em `/hora/estoque` (e similares) por classe correta apos Fase B definir o canonical

### Fase F — Wiring/Enforcement
- Pre-commit hook rodando `ui_audit.py --json-only` em modo baseline (so falha em regressao)
- CI check comparando audit do PR com `relatorios/ui_audit_baseline.json` commitado
- Atualizar `CLAUDE.md` apontando para fonte unica `GUIA_COMPONENTES_UI.md`
