<!-- doc:meta
tipo: explanation
camada: L2
sot_de: —
hub: .claude/atualizacoes/references/historico.md
superseded_by: —
atualizado: 2026-06-15
-->
# Atualizacao References — 2026-06-15-1

**Data**: 2026-06-15
**Grupos revisados**: P0 (root, 24 files), P1 (modelos/ + negocio/, 10 files), P2 (odoo/, 9 files) em profundidade; P3-P4 (design/, linx/, ssw/) scan rapido
**Arquivos modificados**: 6

## Resumo

Auditoria completa de P0-P2 com verificacao de versoes contra `requirements.txt`,
caminhos no filesystem e citacoes de linha contra o codigo real. Achados principais:
(1) **drift de versao do SDK** ainda nao propagado para `STUDY_PROMPT_ENGINEERING_2026.md`
(MCP_CAPABILITIES e BEST_PRACTICES ja tinham sido atualizados em 2026-06-13);
(2) **citacoes de linha desatualizadas** em MEMORY_PROTOCOL, MARGEM_CUSTEIO e PADROES_AVANCADOS
por refactors de codigo; (3) **caminhos de modulo errados** em REGRAS_MODELOS (CidadeAtendida/
CadastroSubRota); (4) **contagem de models** de recebimento (20 -> 23). Subagents (16),
skills invocaveis (54 = 53 dirs SKILL.md + `consultando-sql` DATA-only sem SKILL.md), IDs Odoo,
tolerancias 10%/0% (`validacao_nf_po_service.py:55-58`) TODOS conferem. Zero caminhos `app/*`
quebrados nas referencias P0-P2.

## Verificacoes de Versao (Fase 1)

| Componente | requirements.txt | Documentado (antes) | Acao |
|------------|------------------|---------------------|------|
| `anthropic` | 0.109.1 | MCP_CAPABILITIES / BEST_PRACTICES: 0.109.1 OK; STUDY:88 = **0.98.1** | Corrigido STUDY:88 |
| `claude-agent-sdk` | 0.2.101 (CLI 2.1.177) | MCP_CAPABILITIES / BEST_PRACTICES: 0.2.101 OK; STUDY:88 = **0.2.95 / CLI 2.1.170** | Corrigido STUDY:88 |
| `mcp` | >=1.26.0,<2.0.0 | Confere | — |
| `sentry-sdk` | 2.54.0 | Confere | — |

## Alteracoes por Grupo

### Root (P0) — 2 arquivos

- `STUDY_PROMPT_ENGINEERING_2026.md:88` — SDK desatualizado. `claude-agent-sdk==0.2.95`
  (CLI 2.1.170) -> **0.2.101** (CLI 2.1.177); `anthropic==0.98.1` -> **0.109.1**. O bump
  2026-06-13 (0.2.96-101 + anthropic 11 minors, zero breaking) ja constava em
  MCP_CAPABILITIES_2026.md:37-38 e BEST_PRACTICES_2026.md:43-44, mas nao no STUDY.
- `MEMORY_PROTOCOL.md:122` — citacao stale: `_calculate_category_decay()` em
  `memory_injection.py:271` -> **:348** (funcao moveu; confirmado unica definicao no arquivo).
  `memory_consolidator.py:62` (PROTECTED_PATHS) permanece correto.

### modelos/ (P1) — 1 arquivo

- `REGRAS_MODELOS.md` — caminho de modulo errado: `CidadeAtendida / CadastroSubRota
  (app/cotacao/models.py)` corrigido para `CidadeAtendida (app/vinculos/models.py) /
  CadastroSubRota (app/localidades/models.py)`. `app/cotacao/models.py` existe mas contem
  apenas `Cotacao`/`CotacaoItem`. Corrigido no titulo da secao (linha 301) e na entrada do
  indice/TOC (linha 56, incl. anchor regenerado).
  - Tambem: pointer de schema `pedidos.json` -> `mv_pedidos.json` (a view `pedidos` e
    materializada; nao ha `pedidos.json` gerado). Pointer `pre_separacao_items.json` (plural,
    inexistente) substituido por nota — tabela e `pre_separacao_item` (singular, deprecada),
    schema JSON nao gerado; campos via `app/carteira/models.py:457`.

### negocio/ (P1) — 2 arquivos

- `MARGEM_CUSTEIO.md:94` — citacao stale: bloco de recalculo de margem em
  `carteira_service.py:2625-2700` -> **2647-2715** (set `CAMPOS_QUE_DISPARAM_RECALCULO_MARGEM`
  em :2649). Demais citacoes do arquivo (`:949`, `:1376`, `:1379`, `custeio_service.py:827`,
  `:1140`, `:1160`) conferem.
- `RECEBIMENTO_MATERIAIS.md` — contagem de models 20 -> **23** (titulo linha 355 + TOC linha 33);
  adicionados 3 models de transferencia (snapshot) ausentes: `NfTransferenciaSnapshot` (:1700),
  `NfTransferenciaProdutoSnapshot` (:1828), `NfTransferenciaDesconsiderada` (:1866).

### odoo/ (P2) — 1 arquivo

- `PADROES_AVANCADOS.md` — citacoes e contagens stale (refactor de services):
  - Padrao 1 (Auditoria): `lancamento_odoo_service.py:498-672` -> **873-1048**
    (`_registrar_auditoria:873` + `_executar_com_auditoria:961`).
  - Padrao 7 (Timeout Override): `:1088-1141` (metodo `_gerar_po_com_timeout_estendido`
    inexistente) -> **509-689** (`_gerar_po_dfe_fire_and_poll`).
  - Tabela "Services de Referencia": linhas atualizadas via `wc -l` real — lancamento
    1.824->**2.240**, cte 976->**1.168**, carteira 2.790->**3.117**, pedido_compras
    925->**1.352**, recebimento_fisico 500+->**773**, baixa_titulos 1.128->**2.167**.

## Itens NAO corrigidos (advisory / carry-forward)

- `odoo/IDS_FIXOS.md` — `product_tmpl_id (FRETE) = 34` permanece flagado como `VERIFICAR`
  (requer MCP Odoo ao vivo; pendencia historica desde 2026-04-20). `product_id=29993` confere.
- `odoo/IDS_FIXOS.md` — `payment_provider_id=30` rotulado "padrao": valor (30) confere com
  `lancamento_odoo_service.py`; rotulo "padrao" e impreciso (30 e o provider de transferencia CD;
  FB usa 92). Nao corrigido — nao e erro factual de ID. Sugestao: rotular "FB->CD".
- `REGRAS_MODELOS.md` — 5 tabelas reais sem schema JSON auto-gerado citado:
  `relatorio_faturamento_importado`, `liberacao_antecipacao`, `custo_mensal`, `regra_comissao`,
  `contas_a_receber_abatimento`/`_tipos`. Gap SISTEMICO do gerador (`generate_schemas.py` cobre
  333 tabelas, nao estas). Os 2 casos de maior trafego (pedidos, pre_separacao_item) foram
  corrigidos. Backlog: estender cobertura do gerador OU suavizar os 5 pointers restantes.
- `odoo/PIPELINE_RECEBIMENTO.md` / `AGENT_BOILERPLATE.md` — `especialista-odoo` aparece em
  tabelas de "skills por fase"; e um SUBAGENT (`.claude/agents/especialista-odoo.md`), nao skill.
  Nao corrigido — contexto torna a intencao clara (orquestrador).
- `odoo/PIPELINE_RECEBIMENTO_LF.md` — `PLAYWRIGHT_MAX_TENTATIVAS=15`/`PLAYWRIGHT_INTERVALO_RETRY=120`
  apresentados como constantes de modulo; sao defaults de parametro em
  `playwright_nfe_transmissao.py:46-47`. Valores corretos; nomenclatura documental.

## Verificacoes que CONFEREM (sem alteracao)

- Event listeners da Separacao: `app/separacao/models.py` def @221/257/306/339 com ranges
  221-254 / 257-304 / 306-336 / 339-455 — TODOS corretos (ja ajustados em 2026-06-08).
- Tolerancias recebimento: `validacao_nf_po_service.py:55` (QTD 10%), `:58` (PRECO 0%),
  `:57` (data -5/+15) — conferem.
- IDs Odoo: FB=1, SC=3, CD=4, LF=5; picking_types FB=1/SC=8/CD=13/LF=19; constants LF em
  `recebimento_lf_odoo_service.py:128-160` — conferem.
- 16 subagents (`.claude/agents/*.md`); 54 skills invocaveis (53 dirs SKILL.md +
  `consultando-sql` DATA-only). Header ROUTING_SKILLS (54) e INDEX conferem.
- Infra Render (sistema-fretes Pro Plus / worker Standard / Postgres Basic 4GB / Redis Starter)
  em INFRAESTRUTURA.md — confere com CLAUDE.md TECH STACK.
- Zero caminhos `app/*` ou `.claude/*` quebrados em P0-P2. P3-P4 (design/linx/ssw) scan limpo.

## Itens para Revisao Manual

- Cobertura do gerador de schemas (`generate_schemas.py`) para as 5 tabelas sem JSON citadas
  em REGRAS_MODELOS — decidir entre gerar schemas ou suavizar pointers.
- `IDS_FIXOS.md` product_tmpl_id=34 — resolver via MCP Odoo (pendencia desde 2026-04-20).
- STUDY_PROMPT_ENGINEERING_2026 — revisao trimestral agendada 2026-07.
