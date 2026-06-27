<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-27
-->
# Seção Gerencial HORA — Implementation Plan

> **Papel:** plano de implementação bite-sized (TDD, commits frequentes) da seção
> Gerencial do módulo HORA (dashboards + relatórios). Derivado do spec aprovado
> `docs/superpowers/specs/2026-06-27-hora-gerencial-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice

- [Contexto](#contexto)
- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [FASE F1 — Fundação](#fase-f1--fundação)
- [FASE F2 — Visão Executiva](#fase-f2--visão-executiva)
- [FASE F3 — Comercial & Vendedores](#fase-f3--comercial--vendedores)
- [FASE F4 — Estoque & Suprimento](#fase-f4--estoque--suprimento)
- [FASE F5 — Relatórios](#fase-f5--relatórios)
- [FASE F6 — Polish](#fase-f6--polish)

## Contexto

Nova seção Gerencial do módulo HORA: 4 dashboards (Executivo/Comercial/Estoque/Suprimento)
+ área de relatórios híbrida (galeria pré-definida + builder curado). Fonte exclusiva
`hora_*`. Stack Bootstrap 5.3 + design tokens (light/dark) + Chart.js CDN v4.4.0. Telas
construídas com a skill **frontend-design**. Permissão via 2 slugs novos + escopo por loja.
Spec é a fonte de verdade das fórmulas de KPI.

## Global Constraints

- **Isolamento de módulo:** só tabelas `hora_*`. Zero cross-join / import de outros módulos.
- **Estado da moto:** `MAX(id)` em `hora_moto_evento` (consistente com `estoque_service`), nunca `MAX(timestamp)`.
- **Receita:** somente `hora_venda.status='FATURADO'`.
- **Custo:** `hora_nf_entrada_item.preco_real` com `desconsiderado=FALSE`; join por `numero_chassi`.
- **Anti-N+1:** toda métrica = agregação SQL única (GROUP BY/JOIN/window). Zero loop Python por venda/chassi.
- **Escopo por loja:** `lojas_permitidas_ids()` (`None`=irrestrito; `[ids]`=restrito) aplicado no WHERE do servidor; bucket `loja_id IS NULL` à parte e só p/ irrestrito.
- **Timezone:** Brasil naive (`app.utils.timezone`); `REGRAS_TIMEZONE.md`.
- **Permissões:** `require_hora_perm('gerencial','ver')` / `('gerencial_relatorios','ver')`. Link no menu = MESMO OR do decorator.
- **Commits:** frequentes, sem `[skip render]`. Branch `worktree-hora-gerencial` (worktree).
- **Testes:** `tests/hora/`; baseline atual 231 verdes.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `app/hora/models/permissao.py` (mod) | + slugs `gerencial`, `gerencial_relatorios` |
| `app/hora/services/gerencial/__init__.py` (novo) | exporta API dos services |
| `app/hora/services/gerencial/filtros.py` (novo) | parse de período/loja/granularidade + resolução de escopo |
| `app/hora/services/gerencial/kpi_service.py` (novo) | KPIs executivo + comercial |
| `app/hora/services/gerencial/estoque_kpi_service.py` (novo) | estoque/aging/giro (window function) |
| `app/hora/services/gerencial/suprimento_kpi_service.py` (novo) | lead time/divergência/custo entrada |
| `app/hora/services/gerencial/relatorio_catalogo.py` (novo) | camada semântica (whitelist dims/métricas) |
| `app/hora/services/gerencial/relatorio_service.py` (novo) | galeria + builder + export |
| `app/hora/routes/gerencial.py` (novo) | rotas dos 4 dashboards + relatórios |
| `app/hora/routes/__init__.py` (mod) | import do módulo de rotas gerencial |
| `app/templates/hora/base.html` (mod) | dropdown "Gerencial" na topbar |
| `app/templates/hora/gerencial/*.html` (novo) | base_gerencial + 4 dashboards + relatorios + parciais |
| `tests/hora/test_gerencial_*.py` (novo) | permissão/escopo, KPIs, relatórios |

---

## FASE F1 — Fundação

### Task F1.1: Slugs de permissão

**Files:** Modify `app/hora/models/permissao.py`; Test `tests/hora/test_gerencial_permissao.py`

**Produces:** slugs `'gerencial'` e `'gerencial_relatorios'` em `MODULOS_HORA` + `MODULOS_SO_VER`.

- [ ] **Step 1 — teste falha:** `test_slugs_gerencial_registrados` — assert `'gerencial'` e `'gerencial_relatorios'` ∈ `[m[0] for m in MODULOS_HORA]` e ∈ `MODULOS_SO_VER`.
- [ ] **Step 2 — rodar:** `pytest tests/hora/test_gerencial_permissao.py::test_slugs_gerencial_registrados -v` → FAIL.
- [ ] **Step 3 — impl:** adicionar `('gerencial','Gerencial: Dashboards')` e `('gerencial_relatorios','Gerencial: Relatorios')` ao final de `MODULOS_HORA`; adicionar ambos a `MODULOS_SO_VER`.
- [ ] **Step 4 — rodar:** PASS.
- [ ] **Step 5 — commit:** `feat(hora-gerencial): slugs de permissao gerencial + gerencial_relatorios`.

### Task F1.2: Service de filtros e escopo

**Files:** Create `app/hora/services/gerencial/__init__.py`, `app/hora/services/gerencial/filtros.py`; Test `tests/hora/test_gerencial_filtros.py`

**Produces:**
- `parse_filtros(args: dict) -> Filtros` — dataclass `Filtros(data_ini: date, data_fim: date, granularidade: str, loja_id: int|None)`. Default período = mês corrente; granularidade ∈ {dia,semana,mes} default `dia`.
- `lojas_efetivas(loja_id: int|None) -> list[int]|None` — interseção do `loja_id` pedido com `lojas_permitidas_ids()`; `None` = irrestrito; lança/zera se loja pedida fora do escopo.
- `pode_ver_bucket_sem_loja() -> bool` — True só se `lojas_permitidas_ids() is None`.

- [ ] **Step 1 — testes falham:** `test_parse_filtros_default_mes_corrente`, `test_parse_filtros_periodo_explicito`, `test_lojas_efetivas_restrito_intersecta`, `test_lojas_efetivas_loja_fora_escopo_zera`, `test_bucket_sem_loja_so_irrestrito` (mock `lojas_permitidas_ids`).
- [ ] **Step 2 — rodar:** FAIL.
- [ ] **Step 3 — impl:** `filtros.py` com dataclass + funções; usar `app.utils.timezone` para "hoje" Brasil.
- [ ] **Step 4 — rodar:** PASS.
- [ ] **Step 5 — commit:** `feat(hora-gerencial): service de filtros + escopo de loja`.

### Task F1.3: Blueprint de rotas + menu + base_gerencial

**Files:** Create `app/hora/routes/gerencial.py`, `app/templates/hora/gerencial/base_gerencial.html`; Modify `app/hora/routes/__init__.py`, `app/templates/hora/base.html`; Test `tests/hora/test_gerencial_permissao.py`

**Consumes:** F1.1 (slugs), F1.2 (filtros).
**Produces:** rotas `hora.gerencial` (redirect→executivo), `hora.gerencial_executivo/comercial/estoque/suprimento/relatorios` (stubs render por ora). Dropdown "Gerencial" no menu com OR `tem_perm_hora('gerencial','ver') or tem_perm_hora('gerencial_relatorios','ver')`.

- [ ] **Step 1 — testes falham:** `test_gate_sem_permissao_redireciona` (usuário sem slug → 302/403), `test_gate_admin_acessa` (admin → 200), `test_menu_link_aparece_com_perm` (HTML contém "Gerencial" quando perm), `test_relatorios_exige_slug_proprio` (`gerencial_relatorios` separado de `gerencial`).
- [ ] **Step 2 — rodar:** FAIL.
- [ ] **Step 3 — impl:** rotas com decorators; importar `gerencial` em `routes/__init__.py`; `base_gerencial.html` (extends `hora/base.html`, bloco de filtros período/loja/granularidade reusável + área de conteúdo + Chart.js CDN no `extra_js`); dropdown no `base.html` entre Aprovações e Cadastros, com sub-itens Executivo/Comercial/Estoque/Suprimento/Relatórios (cada `<li>` gateado pelo slug correto).
- [ ] **Step 4 — rodar:** PASS.
- [ ] **Step 5 — commit:** `feat(hora-gerencial): blueprint de rotas + dropdown no menu + base_gerencial`.

---

## FASE F2 — Visão Executiva

### Task F2.1: kpi_service executivo

**Files:** Create `app/hora/services/gerencial/kpi_service.py`; Test `tests/hora/test_gerencial_kpis.py`

**Consumes:** F1.2 (`Filtros`, `lojas_efetivas`).
**Produces** (todas recebem `(filtros: Filtros)`, filtram FATURADO + escopo, retornam tipos abaixo):
- `receita_realizada -> {'valor': Decimal, 'qtd_vendas': int}`
- `margem_bruta -> {'margem_rs': Decimal, 'margem_pct': Decimal, 'cobertura_pct': Decimal, 'vendas_com_custo': int, 'total_vendas': int}` — `SUM(preco_final-preco_real)` join chassi, `desconsiderado=FALSE`, menos `SUM(brinde.custo_total)`; cobertura = vendas com TODOS os chassis com `preco_real` / total FATURADAS.
- `ticket_medio -> Decimal`
- `motos_vendidas -> int`
- `receita_por_periodo -> list[{'periodo': str, 'valor': Decimal}]` (DATE_TRUNC por granularidade sobre `data_venda`).
- `ranking_lojas -> list[{'loja_id': int|None, 'loja_nome': str, 'receita': Decimal, 'unidades': int}]` (bucket NULL só se `pode_ver_bucket_sem_loja`).
- `desconto_total -> Decimal`
- `kpis_executivo -> dict` (agrega tudo para a rota).

- [ ] **Step 1 — testes falham (fixtures com 2 lojas, vendas FATURADO+COTACAO, NF entrada com preco_real, brinde, 1 venda sem custo):**
  `test_receita_so_faturado` (COTACAO não soma), `test_margem_desconta_custo_e_brinde`, `test_margem_cobertura_exclui_venda_sem_custo`, `test_margem_ignora_desconsiderado`, `test_ticket_medio`, `test_ranking_lojas_ordena_por_receita`, `test_ranking_bucket_null_so_irrestrito`, `test_receita_por_periodo_agrupa_por_dia`.
- [ ] **Step 2 — rodar:** FAIL.
- [ ] **Step 3 — impl:** queries SQLAlchemy agregadas (sem N+1). Margem via subquery de custo por chassi.
- [ ] **Step 4 — rodar:** PASS.
- [ ] **Step 5 — commit:** `feat(hora-gerencial): kpi_service executivo (receita, margem c/ cobertura, ticket, ranking)`.

### Task F2.2: Rota + template Executivo

**Files:** Modify `app/hora/routes/gerencial.py`; Create `app/templates/hora/gerencial/executivo.html`, `_kpi_card.html`, `_grafico.html`; Test `tests/hora/test_gerencial_kpis.py`

**Consumes:** F2.1.
**Produces:** `gerencial_executivo` renderiza cards + Chart.js (linha temporal, barra ranking, heatmap margem). Usar skill **frontend-design** para o template (light/dark, estética não-genérica).

- [ ] **Step 1 — teste falha:** `test_executivo_200_e_contem_receita` (rota 200, HTML com valor de receita e canvas de gráfico).
- [ ] **Step 2 — rodar:** FAIL.
- [ ] **Step 3 — impl:** rota chama `kpis_executivo(filtros)`, passa `dados|tojson`; template com cards (`_kpi_card`), linha de receita, ranking, heatmap; cobertura de margem visível.
- [ ] **Step 4 — rodar:** PASS + smoke manual (`python run.py`, abrir /hora/gerencial/executivo).
- [ ] **Step 5 — commit:** `feat(hora-gerencial): dashboard Executivo (cards + tendência + ranking + heatmap margem)`.

---

## FASE F3 — Comercial & Vendedores

### Task F3.1: kpi_service comercial

**Files:** Modify `app/hora/services/gerencial/kpi_service.py`; Test `tests/hora/test_gerencial_kpis.py`

**Produces** (`(filtros)`):
- `conversao_funil -> {'cotacao': int, 'confirmado': int, 'faturado': int, 'taxa': Decimal}` (só `origem_criacao='MANUAL'`).
- `vendas_por_vendedor -> list[{'vendedor': str, 'unidades': int, 'receita': Decimal}]`.
- `comissao_por_vendedor -> list[dict]` — reusa `comissao_service.relatorio_comissao` (por `faturado_em`).
- `desconto_por_dimensao(filtros, dim) -> list[dict]` dim∈{loja,vendedor,modelo}; `tabela_preco_id NOT NULL`.
- `mix_pagamento -> list[{'forma': str, 'valor': Decimal}]` (de `hora_venda_pagamento`).
- `aprovacoes_pendentes -> {'DESCONTO': int, 'FRETE': int, 'BRINDE': int}`.
- `receita_pecas -> Decimal`; `custo_brindes -> Decimal`.
- `kpis_comercial -> dict`.

- [ ] **Step 1 — testes falham:** `test_conversao_so_manual`, `test_vendas_por_vendedor_agrupa`, `test_comissao_reusa_relatorio` (mock/integra `relatorio_comissao`), `test_desconto_por_loja_ignora_sem_tabela`, `test_mix_pagamento_soma`, `test_aprovacoes_pendentes_por_tipo`.
- [ ] **Step 2 — rodar:** FAIL.
- [ ] **Step 3 — impl.** [ ] **Step 4 — PASS.** [ ] **Step 5 — commit:** `feat(hora-gerencial): kpi_service comercial (conversão, vendedores, comissão, descontos, mix, aprovações)`.

### Task F3.2: Rota + template Comercial

**Files:** Modify `app/hora/routes/gerencial.py`; Create `app/templates/hora/gerencial/comercial.html`; Test `tests/hora/test_gerencial_kpis.py`

- [ ] **Step 1 — teste falha:** `test_comercial_200_contem_funil`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl** (funil, ranking vendedores, gauge aprovações, barra mix pagamento; skill frontend-design). [ ] **Step 4 — PASS + smoke.** [ ] **Step 5 — commit:** `feat(hora-gerencial): dashboard Comercial & Vendedores`.

---

## FASE F4 — Estoque & Suprimento

### Task F4.1: estoque_kpi_service (window function)

**Files:** Create `app/hora/services/gerencial/estoque_kpi_service.py`; Test `tests/hora/test_gerencial_estoque.py`

**Produces:**
- `_estado_atual_cte()` — `ROW_NUMBER() OVER (PARTITION BY numero_chassi ORDER BY id DESC)`; filtra `rn=1`.
- `estoque_por_loja_modelo(lojas) -> list[{'loja_id','loja_nome','modelo','cor','qtd','disponivel','avariada','faltando_peca'}]`.
- `aging_estoque(lojas) -> {'faixas': {'0-30':int,'31-60':int,'61-90':int,'90+':int}, 'detalhe': list}` (`NOW()-timestamp` do evento atual ∈ EVENTOS_EM_ESTOQUE).
- `giro_dias(filtros) -> list[{'modelo','dias_medios'}]` (`data_venda - MIN(evento RECEBIDA)`).
- `reservadas_em_transito(lojas) -> {'reservadas': int, 'em_transito': list}`.

- [ ] **Step 1 — testes falham (fixtures com eventos sequenciais por chassi):** `test_estado_atual_pega_max_id`, `test_estoque_conta_so_em_estoque`, `test_aging_classifica_faixas`, `test_giro_calcula_dias`, `test_reservadas_conta_ultimo_RESERVADA`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl** (window function; escopo via `lojas`). [ ] **Step 4 — PASS.** [ ] **Step 5 — commit:** `feat(hora-gerencial): estoque_kpi_service (estado MAX(id), aging, giro)`.

### Task F4.2: suprimento_kpi_service

**Files:** Create `app/hora/services/gerencial/suprimento_kpi_service.py`; Test `tests/hora/test_gerencial_estoque.py`

**Produces:**
- `lead_time_recebimento(filtros) -> {'dias_medios_nf_receb': Decimal, 'dias_medios_conferencia': Decimal}`.
- `taxa_divergencia(filtros) -> list[{'tipo','qtd','pct'}]` (`substituida=FALSE`).
- `custo_medio_entrada(filtros) -> list[{'modelo','custo_medio'}]` (`desconsiderado=FALSE`).
- `desvio_custo(filtros) -> list[{'modelo','desvio_medio'}]` (`preco_real-preco_compra_esperado`).

- [ ] **Step 1 — testes falham:** `test_lead_time_nf_recebimento`, `test_taxa_divergencia_ignora_substituida`, `test_custo_medio_ignora_desconsiderado`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl.** [ ] **Step 4 — PASS.** [ ] **Step 5 — commit:** `feat(hora-gerencial): suprimento_kpi_service (lead time, divergência, custo)`.

### Task F4.3: Rotas + templates Estoque e Suprimento

**Files:** Modify `app/hora/routes/gerencial.py`; Create `app/templates/hora/gerencial/estoque.html`, `suprimento.html`; Test `tests/hora/test_gerencial_estoque.py`

- [ ] **Step 1 — testes falham:** `test_estoque_200_contem_aging`, `test_suprimento_200_contem_lead_time`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl** (tabela hierárquica loja>modelo>cor, heatmap aging, barras; skill frontend-design). [ ] **Step 4 — PASS + smoke.** [ ] **Step 5 — commit:** `feat(hora-gerencial): dashboards Estoque & Giro + Suprimento`.

---

## FASE F5 — Relatórios

### Task F5.1: Catálogo semântico

**Files:** Create `app/hora/services/gerencial/relatorio_catalogo.py`; Test `tests/hora/test_gerencial_relatorios.py`

**Produces:**
- `DIMENSOES: dict[str, dict]` — slug→{label, sql_group, sql_select}. Slugs: loja, vendedor, modelo, cor, forma_pagamento, periodo, canal.
- `METRICAS: dict[str, dict]` — slug→{label, sql_agg}. Slugs: receita, margem_rs, margem_pct, unidades, ticket, desconto_rs, desconto_pct.
- `validar_selecao(dims: list[str], metricas: list[str]) -> tuple[bool, str|None]` — rejeita slug fora da whitelist; exige ≥1 dim e ≥1 métrica.

- [ ] **Step 1 — testes falham:** `test_validar_aceita_whitelist`, `test_validar_rejeita_dim_desconhecida`, `test_validar_exige_metrica`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl.** [ ] **Step 4 — PASS.** [ ] **Step 5 — commit:** `feat(hora-gerencial): catálogo semântico de relatórios (whitelist dims/métricas)`.

### Task F5.2: relatorio_service (galeria + builder + export)

**Files:** Create `app/hora/services/gerencial/relatorio_service.py`; Test `tests/hora/test_gerencial_relatorios.py`

**Consumes:** F5.1, F2/F4 services.
**Produces:**
- `RELATORIOS_PREDEFINIDOS: list[{'slug','label','descricao'}]` (vendas_por_loja, margem_por_modelo, comissao_por_vendedor, aging_estoque, divergencias_recebimento).
- `gerar_predefinido(slug, filtros) -> {'colunas': list, 'linhas': list}`.
- `gerar_builder(dims, metricas, filtros) -> {'colunas','linhas'}` — monta agregação só de fragmentos do catálogo; reaplica escopo de loja no servidor.
- `exportar(resultado, formato) -> bytes|path` — formato ∈ {xlsx, csv} via skill `exportando-arquivos`.

- [ ] **Step 1 — testes falham:** `test_predefinido_vendas_por_loja`, `test_builder_monta_dim_metrica`, `test_builder_rejeita_fora_catalogo`, `test_builder_reaplica_escopo_loja`, `test_exportar_xlsx_gera_arquivo`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl.** [ ] **Step 4 — PASS.** [ ] **Step 5 — commit:** `feat(hora-gerencial): relatorio_service (galeria + builder + export)`.

### Task F5.3: Rota + template Relatórios

**Files:** Modify `app/hora/routes/gerencial.py`; Create `app/templates/hora/gerencial/relatorios.html`; Test `tests/hora/test_gerencial_relatorios.py`

**Produces:** `gerencial_relatorios` (galeria + form do builder) + `gerencial_relatorio_resultado` (POST → tabela+gráfico) + `gerencial_relatorio_export` (download). Slug `gerencial_relatorios`.

- [ ] **Step 1 — testes falham:** `test_relatorios_200_lista_galeria`, `test_relatorio_export_download`, `test_relatorios_gate_slug_proprio`.
- [ ] **Step 2 — FAIL.** [ ] **Step 3 — impl** (galeria de cards + builder UI com selects de dim/métrica/filtro; skill frontend-design). [ ] **Step 4 — PASS + smoke.** [ ] **Step 5 — commit:** `feat(hora-gerencial): área de relatórios (galeria + builder + export)`.

---

## FASE F6 — Polish

### Task F6.1: Tour + light/dark + CLAUDE.md

**Files:** Create `app/static/onboarding/tours/hora/gerencial.js` (se padrão exigir); Modify `app/templates/hora/gerencial/*` (data-tour), `app/hora/CLAUDE.md`; Test (visual)

- [ ] **Step 1:** revisar light/dark de todas as telas (tokens `--bs-*`, sem cor hardcoded).
- [ ] **Step 2:** onboarding tour da seção (se houver `_macro.js` aplicável).
- [ ] **Step 3:** documentar a seção Gerencial em `app/hora/CLAUDE.md` (nova seção numerada) + atualizar `MODULOS_HORA` na doc.
- [ ] **Step 4 — commit:** `docs(hora-gerencial): tour + CLAUDE.md + light/dark polish`.

### Task F6.2: Validação vs produção + review final

**Files:** —

- [ ] **Step 1:** rodar `pytest tests/hora/ -q` → todos verdes (231 + novos).
- [ ] **Step 2:** validar números-chave (receita/unidades/estoque do mês) via MCP Render `query_render_postgres` contra os dashboards (dados locais = teste).
- [ ] **Step 3:** code review adversarial (requesting-code-review / Workflow de review) das queries (N+1, escopo de loja, filtros silenciosos).
- [ ] **Step 4:** verification-before-completion — rodar suíte + smoke das 5 telas; reportar evidências.
- [ ] **Step 5 — commit final + push** (após aval do usuário, sem `[skip render]`).
