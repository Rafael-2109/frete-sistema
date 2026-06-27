<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-27
-->
# Seção Gerencial HORA — Design (dashboards + relatórios)

> **Papel:** spec da nova seção **Gerencial** do módulo HORA — dashboards executivos
> (diretoria) e operacionais (gerência) + área de geração/construção de relatórios.
> Lido por quem for implementar (plano em `docs/superpowers/plans/`).

## Indice

- [Contexto](#contexto)
- [Decisões aprovadas](#decisões-aprovadas)
- [Modelo de negócio (resumo analítico)](#modelo-de-negócio-resumo-analítico)
- [Arquitetura](#arquitetura)
- [Permissões e escopo por loja](#permissões-e-escopo-por-loja)
- [Catálogo de KPIs por dashboard](#catálogo-de-kpis-por-dashboard)
- [Área de relatórios (galeria + builder)](#área-de-relatórios-galeria--builder)
- [Riscos e mitigações](#riscos-e-mitigações)
- [Fases de implementação](#fases-de-implementação)
- [Testes](#testes)
- [Não-objetivos (v2)](#não-objetivos-v2)

## Contexto

O módulo HORA (varejo B2C de motos elétricas, multi-loja) tem hoje um `dashboard.html`
mínimo: 6 contadores globais + tabela de 20 eventos recentes (`app/hora/routes/dashboard.py`).
Não há nenhum KPI de **vendas, receita, margem, giro ou desconto** — exatamente o que
gerência e diretoria precisam.

**Objetivo:** criar a seção **Gerencial** com (1) dashboards inteligentes para diretoria
e gerência e (2) uma área de geração/construção de relatórios com export. Toda a fonte de
dados é local ao módulo (`hora_*`), sem cross-join com outros módulos.

## Decisões aprovadas

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | Skill de estilo | **frontend-design** (Jinja2/Bootstrap, light/dark obrigatório) |
| 2 | Escopo de relatórios v1 | **Híbrido**: galeria pré-definida **+** builder simples de tabela dinâmica (dimensões/métricas curadas, views seguras) |
| 3 | Margem na Visão Diretoria | **Incluir no v1 com transparência de cobertura** (% de vendas com custo real disponível; nunca usar `preco_compra_esperado` como proxy silencioso) |
| 4 | Controle de acesso | **Escopo por loja** (`lojas_permitidas_ids`) **+ permissão específica** para a área de relatórios (slug `gerencial_relatorios`, separado de `gerencial`) |

## Modelo de negócio (resumo analítico)

- **Receita realizada** existe somente em `hora_venda.status='FATURADO'`.
- **Custo real** da moto = `hora_nf_entrada_item.preco_real` (por chassi; ignorar
  `desconsiderado=TRUE`). **Margem unitária** = `hora_venda_item.preco_final − preco_real`,
  cruzados por `numero_chassi` (chave universal do módulo), menos `hora_venda_brinde.custo_total`.
- **Estado da moto** = último evento (`MAX(id)` em `hora_moto_evento`), nunca UPDATE.
  `EVENTOS_EM_ESTOQUE` = RECEBIDA, CONFERIDA, TRANSFERIDA, CANCELADA, AVARIADA,
  FALTANDO_PECA, EMPRESTIMO_ENTRADA, RESSARCIMENTO_SAIDA.
- **Comissão** é calculada on-the-fly (`comissao_service.relatorio_comissao`, base por moto
  − redução por faixa de desconto); reusar o service existente, não reimplementar.
- **Dimensões analíticas canônicas:** LOJA (`loja_id`), VENDEDOR (`vendedor` / `criado_por_id`),
  MODELO/COR (via chassi → `hora_moto.modelo_id`/`cor`), FORMA DE PAGAMENTO
  (`hora_venda_pagamento.forma_pagamento_hora`), TEMPO (negócio=`data_venda`,
  operacional=`faturado_em`, aging/giro=`hora_moto_evento.timestamp`), CUSTO/MARGEM.

## Arquitetura

Segue o padrão de blueprint isolado do módulo (`app/hora/CLAUDE.md`).

```
app/hora/routes/gerencial.py        # rotas: 4 dashboards + galeria + builder + export
app/hora/services/gerencial/
    __init__.py
    kpi_service.py                  # KPIs executivos/comerciais (vendas, margem, ticket, conversão)
    estoque_kpi_service.py          # estoque, aging, giro (window function por chassi)
    suprimento_kpi_service.py       # lead time, divergência, custo de entrada
    relatorio_service.py            # galeria (relatórios pré-definidos) + builder curado
    relatorio_catalogo.py           # camada semântica: dimensões/métricas permitidas (whitelist)
app/templates/hora/gerencial/
    base_gerencial.html             # layout comum (filtros período/loja, cards, área de gráfico)
    executivo.html  comercial.html  estoque.html  suprimento.html
    relatorios.html                 # galeria + builder
    _kpi_card.html  _grafico.html    # parciais reusáveis
```

**Padrão de dados dos gráficos:** server-side. A rota chama o service (que devolve dicts
agregados já prontos), o template injeta via `{{ dados | tojson }}` e o Chart.js (CDN,
v4.4.0 — mesmo padrão de `bi/`, `main/`, `seguranca/`) renderiza no cliente. Filtros
(período, loja, granularidade dia/semana/mês) são query params que re-renderizam a página.
**Sem endpoints JSON novos no v1** para os dashboards; o builder de relatórios usa um
endpoint que devolve a tabela renderizada + botão de export.

**Regra anti-N+1 (CRÍTICO):** toda métrica é uma agregação SQL única (GROUP BY / JOIN /
window function). Proibido loop Python por venda/chassi. Estado/aging/giro usam
`ROW_NUMBER() OVER (PARTITION BY numero_chassi ORDER BY id DESC)` (índice
`ix_hora_moto_evento_chassi_timestamp` já existe) em vez de N subqueries `MAX(id)`.
Padronizar em **`MAX(id)`** (consistente com `estoque_service`), não `MAX(timestamp)`.

**Numérico/timezone:** seguir `REGRAS_TIMEZONE.md` (Brasil naive) e formatação BR
(`exportando-arquivos` já cobre Excel/CSV com formatação numérica).

## Permissões e escopo por loja

Dois slugs novos em `MODULOS_HORA` (`app/hora/models/permissao.py`), ambos em
`MODULOS_SO_VER` (só a ação `ver` tem semântica). `hora_user_permissao.modulo` é
VARCHAR(40) → **sem DDL/migration**.

| Slug | Gateia |
|------|--------|
| `gerencial` | os 4 dashboards (Executivo / Comercial / Estoque / Suprimento) |
| `gerencial_relatorios` | a área de geração/construção de relatórios (galeria + builder + export) |

- Decorator `require_hora_perm('gerencial', 'ver')` / `require_hora_perm('gerencial_relatorios', 'ver')`.
- **Escopo por loja aplicado no WHERE** de cada query (não basta esconder o menu):
  `lojas_permitidas_ids()` → `None` = irrestrito (diretoria/admin vê a rede);
  `[ids]` = gerente vê só a(s) sua(s) loja(s). Para KPIs por chassi (estoque, margem,
  giro) usar `chassis_acessiveis_subquery(lojas_permitidas)`.
- **Bucket `loja_id IS NULL`** (vendas com `CNPJ_DESCONHECIDO`): exibido à parte e somente
  para acesso irrestrito; nunca diluído silenciosamente nos totais por loja.
- Novo bloco dropdown **"Gerencial"** na topbar `app/templates/hora/base.html`, com o mesmo
  OR de permissões usado nos decorators (regra: link e decorator com a MESMA condição).

## Catálogo de KPIs por dashboard

> Fórmulas ancoradas em campos reais (schemas em `.claude/skills/consultando-sql/schemas/tables/`).
> Prioridade: **P0** = essencial v1, **P1** = v1 se couber, **P2** = v2.

### 1. Visão Executiva (diretoria)
| KPI | P | Fórmula |
|-----|---|---------|
| Receita realizada | P0 | `SUM(hora_venda.valor_total)` WHERE `status='FATURADO'` |
| Margem bruta R$ | P0 | `SUM(hvi.preco_final − nfi.preco_real)` JOIN por chassi, FATURADO, `nfi.desconsiderado=FALSE`, − `SUM(brinde.custo_total)` |
| Margem bruta % | P0 | `SUM(preco_final − preco_real) / SUM(preco_real) × 100` |
| Ticket médio | P0 | `AVG(hora_venda.valor_total)` FATURADO |
| Motos vendidas | P0 | `COUNT(hvi.numero_chassi)` via JOIN venda FATURADO |
| Receita por período (tendência) | P0 | `SUM(valor_total)` GROUP BY `DATE_TRUNC(dia/semana/mês, data_venda)` |
| Ranking de lojas (receita+unidades) | P0 | GROUP BY `loja_id` FATURADO |
| Heatmap margem % loja×modelo | P1 | margem% GROUP BY `loja_id, modelo_id` |
| Desconto total concedido | P1 | `SUM(hvi.desconto_aplicado)` FATURADO |
| Canal de marketing | P2 | GROUP BY `origem_lead` (cobertura parcial — rotular) |

**Transparência de margem:** todo card/gráfico de margem exibe **cobertura** =
`vendas FATURADAS com custo real disponível / total FATURADAS` (ex.: "margem sobre 82% das
vendas — 41 de 50"). Vendas sem `preco_real` por chassi ficam fora do numerador, nunca
preenchidas por estimativa.

### 2. Comercial & Vendedores (gerência)
Conversão COTAÇÃO→FATURADO (funil, `origem_criacao='MANUAL'`) · Vendas por vendedor ·
Comissão por vendedor (reusa `relatorio_comissao`, por `faturado_em`) · Desconto médio %/R$
por loja/vendedor/modelo (filtrar `tabela_preco_id NOT NULL`) · Mix de forma de pagamento
(`hora_venda_pagamento`) · Mix de parcelamento · **Gauge de aprovações pendentes**
(`hora_aprovacao_desconto` PENDENTE por tipo DESCONTO/FRETE/BRINDE) · Receita de peças ·
Custo de brindes.

### 3. Estoque & Giro (gerência)
Estoque disponível loja>modelo>cor (último evento ∈ `EVENTOS_EM_ESTOQUE`) · **Aging do
estoque parado** (faixas 0-30/31-60/61-90/90+, `NOW() − timestamp` do evento atual) · Giro
= dias do RECEBIDA até a venda (`AVG(data_venda − MIN(evento RECEBIDA))`) por modelo/loja ·
Reservadas e em trânsito (`listar_em_transito`).

### 4. Suprimento & Recebimento (gerência)
Lead time NF→recebimento (`AVG(data_recebimento − data_emissao)`) · Taxa de divergência por
tipo (MODELO/COR/FALTANDO/EXTRA/AVARIA, `substituida=FALSE`) · Custo médio de entrada por
modelo (`AVG(preco_real)`, `desconsiderado=FALSE`) · Desvio real vs esperado
(`preco_real − preco_compra_esperado`, requer `pedido_id`).

## Área de relatórios (galeria + builder)

**Galeria (pré-definidos, corretude garantida):** cada relatório é rota + query
parametrizada + tabela + export. Filtros comuns: período, loja, vendedor, modelo. v1:
Vendas por loja · Margem por modelo · Comissão por vendedor · Aging de estoque ·
Divergências de recebimento. Export Excel/CSV via **skill `exportando-arquivos`**
(formatação BR nativa). PDF executivo fica para v2.

**Builder simples (curado, NÃO SQL livre):** opera sobre uma **camada semântica**
(`relatorio_catalogo.py`) que whitelista:
- **Dimensões:** loja, vendedor, modelo, cor, forma de pagamento, período (dia/semana/mês), canal.
- **Métricas:** receita, margem R$, margem %, unidades, ticket médio, desconto R$, desconto %.
- **Filtros:** período, loja (respeitando escopo), status (default FATURADO).

O usuário escolhe 1-2 dimensões + 1-N métricas + filtros; o service monta a agregação a
partir de fragmentos pré-validados (cada métrica/dimensão tem seu SQL seguro mapeado),
renderiza tabela + gráfico e permite export. **Nunca** concatena SQL do usuário; o escopo
de loja é sempre reaplicado no WHERE no servidor (não confiar em parâmetro do cliente).

## Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Performance sobre `hora_moto_evento` (estado/aging/giro) | window function `ROW_NUMBER OVER PARTITION BY chassi ORDER BY id DESC`; índice já existe |
| N+1 ao enriquecer por chassi | tudo em JOIN/agregação SQL única; zero loop Python |
| `MAX(id)` vs `MAX(timestamp)` divergem em inserção retroativa | padronizar **`MAX(id)`** e documentar |
| Filtros silenciosos distorcem totais | sempre `status='FATURADO'`, `substituida=FALSE`, `origem_criacao='MANUAL'` na conversão; bucket `loja_id NULL` à parte |
| Cobertura parcial (margem, `hora_venda_pagamento`, `origem_lead`, `vendedor`) | exibir fração coberta em cada KPI afetado |
| Comissão não persistida (config vigente ≠ da venda) | rotular "reflete a config atual de comissão" |
| Vazamento entre lojas | escopo no WHERE do servidor + permissão; nunca via parâmetro do cliente |
| Dados de teste local vs produção | validar números (receita/unidades/estoque) via MCP Render `query_render_postgres` antes de publicar à diretoria |

## Fases de implementação

1. **F1 — Fundação:** slugs de permissão (`gerencial`, `gerencial_relatorios`) + dropdown
   "Gerencial" no menu + rota índice + `base_gerencial.html` (filtros período/loja) +
   helper de escopo. TDD do gate e do escopo de loja.
2. **F2 — Visão Executiva:** `kpi_service` (receita, margem c/ cobertura, ticket, unidades,
   tendência, ranking de lojas, desconto). Tela `executivo.html` (cards + linha + ranking + heatmap).
3. **F3 — Comercial & Vendedores:** conversão, vendedores, comissão (reuso), descontos, mix
   pagamento, gauge de aprovações, peças, brindes. Tela `comercial.html`.
4. **F4 — Estoque & Giro + Suprimento:** `estoque_kpi_service` (window function) e
   `suprimento_kpi_service`. Telas `estoque.html` e `suprimento.html`.
5. **F5 — Relatórios:** galeria pré-definida + export (`exportando-arquivos`) + builder
   curado (`relatorio_catalogo` + `relatorio_service`). Tela `relatorios.html`.
6. **F6 — Polish:** light/dark check, onboarding tour, validação dos números vs produção
   (MCP Render), atualização de `app/hora/CLAUDE.md`.

Cada fase entrega tela acessível pelo menu (regra: nunca tela sem acesso UI) e testes verdes.

## Testes

- `tests/hora/test_gerencial_permissao.py` — gate dos 2 slugs; escopo por loja (gerente só
  vê sua loja; admin vê tudo; bucket NULL só admin); link↔decorator coerentes.
- `tests/hora/test_gerencial_kpis.py` — fórmulas com fixtures: receita só FATURADO; margem
  só com `preco_real` disponível + cobertura correta; `desconsiderado` ignorado; aging por
  `MAX(id)`; conversão só `MANUAL`; `substituida=FALSE` na divergência.
- `tests/hora/test_gerencial_relatorios.py` — builder rejeita dimensão/métrica fora da
  whitelist; escopo de loja reaplicado no servidor; export gera arquivo.

## Não-objetivos (v2)

PDF executivo · agendamento/envio automático de relatórios · builder com SQL livre ·
financeiro/contas a receber/inadimplência (Fase 2 do módulo, tabelas inexistentes) ·
custo de frete de entrada e custo de peça na margem · comissão persistida (snapshot
histórico) · materialized view de estado-da-moto (só se a performance exigir).
