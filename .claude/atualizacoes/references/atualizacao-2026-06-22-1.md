<!-- doc:meta
tipo: explanation
camada: L2
sot_de: —
hub: .claude/atualizacoes/references/historico.md
superseded_by: —
atualizado: 2026-06-22
-->
# Atualizacao References — 2026-06-22-1

**Data**: 2026-06-22
**Grupos revisados**: P0 (root, 26 files), P1 (modelos/ + negocio/, 11 files), P2 (odoo/, 9 files) em profundidade; P3-P4 (design/, linx/, ssw/) scan rapido
**Arquivos modificados**: 8

## Resumo

Auditoria completa de P0-P2 com verificacao de versoes contra `requirements.txt`,
caminhos no filesystem e citacoes de linha contra o codigo real (repo `frete_sistema_manutencao`).
Sem drift de versao do SDK nesta rodada (SDK `0.2.101` / CLI `2.1.177` / `anthropic 0.109.1`
conferem com requirements.txt — bump 2026-06-13 ja propagado na semana passada). Achados
principais: (1) **+3 skills no inventario** desde 2026-06-15 (header ROUTING_SKILLS ja em 57;
STUDY/INDEX em 54 — reconciliados); (2) **citacao de SDK stale** em AGENT_DESIGN_GUIDE (`0.2.95`
-> `0.2.101`); (3) **drift de linhas dos event listeners da Separacao** (refactor +5 linhas);
(4) **caminhos quebrados** corrigidos: `embarque_items.json` -> `embarque_itens.json` (PT-BR),
`app/agente/routes.py` -> pacote `app/agente/routes/`, 2 scripts movidos para `_deprecated/`;
(5) **contagens stale** (modelos recebimento TOC 23->24, 2 line-counts de services Odoo).
C8 (alcancabilidade) limpo ANTES e DEPOIS das edicoes (0 orfaos). 16 subagents, tolerancias
10%/0%, IDs Odoo (FB1/SC3/CD4/LF5) TODOS conferem.

## PASSO 0 — Verificacao C8 (alcancabilidade)

`python3 scripts/audits/doc_audit.py --report-only --skip-dup | grep ^C8` -> **0 findings**
(varredura GLOBAL: docs/, .claude/references/, app/**/CLAUDE.md, CLAUDE.md). Re-rodado apos
todas as edicoes -> continua **0 orfaos / 0 bidirecionalidade quebrada / 0 hub inexistente**.
Nenhum wiring de hub foi necessario. `c8_orfaos=0`, `c8_corrigidos=0`.

## Verificacoes de Versao (Fase 1)

| Componente | requirements.txt | Documentado | Acao |
|------------|------------------|-------------|------|
| `anthropic` | 0.109.1 | MCP_CAPABILITIES / BEST_PRACTICES / STUDY: 0.109.1 OK | — |
| `claude-agent-sdk` | 0.2.101 (CLI 2.1.177) | MCP_CAPABILITIES / BEST_PRACTICES / STUDY: 0.2.101 OK; **AGENT_DESIGN_GUIDE:73 = 0.2.95** | Corrigido AGENT_DESIGN_GUIDE:73 |
| `mcp` | >=1.26.0,<2.0.0 | Confere | — |
| `sentry-sdk` | 2.54.0 | Confere | — |

## Alteracoes por Grupo

### Root (P0) — 3 arquivos

- `AGENT_DESIGN_GUIDE.md:73` — citacao de SDK stale na descricao de `effort`/`xhigh`:
  "continua valido no SDK **0.2.95**" -> **0.2.101** (alinhado ao default vigente).
- `STUDY_PROMPT_ENGINEERING_2026.md:89` — contagem de skills `54 skills invocaveis` -> **57**
  (filesystem: 56 dirs SKILL.md + `consultando-sql` DATA-only sem SKILL.md = 57; header de
  ROUTING_SKILLS.md ja estava em 57 desde 2026-06-20).
- `INDEX.md` — (a) header `Ultima atualizacao` 2026-06-08 (inventario 51->54) -> **2026-06-22**
  (inventario **54->57**); (b) mapeamento Skill->References ganhou `corrigindo-dados-assai`
  (WRITE backfill Assai, 2026-06-19, delegada a `gestor-motos-assai`). `auditando-reclassificacao-odoo`
  e `baixando-credores-lote-odoo` ja constavam no mapa.
- `ROADMAP_SDK_CLIENT.md` (P0 living roadmap) — caminho quebrado `app/agente/routes.py`
  (agora pacote `app/agente/routes/`, split em 2026-06-20) corrigido em 2 ocorrencias
  (tabela de impacto :635 + tabela de recursos :824), LOC 3074 -> ~9032 (total do pacote).
  Tambem: `scripts/poc_sdk_client.py` -> `scripts/_deprecated/oneoff-2026-06/poc_sdk_client.py`
  (2 ocorrencias :69 e :820 — script movido para _deprecated).

### modelos/ (P1) — 2 arquivos

- `REGRAS_CARTEIRA_SEPARACAO.md` — drift de ~5 linhas nos 4 event listeners da Separacao
  (refactor de `app/separacao/models.py`; decoradores hoje em 226/261/311/343):
  - Listener 1 `setar_falta_pagamento_inicial`: `221-254` -> **226-259**
  - Listener 2 `atualizar_status_automatico`: `257-304` -> **261-309**
  - Listener 3 `log_reversao_status`: `306-336` -> **311-341**
  - Listener 4 `recalcular_totais_embarque`: `339-455` -> **343-455** (heading :98 + ref :162)
- `REGRAS_MODELOS.md` — 2 correcoes:
  - `PreSeparacaoItem` em `app/carteira/models.py:457` -> **:441** (class def real).
  - Pointer de schema `embarque_items.json` (ingles) -> **`embarque_itens.json`** (PT-BR — nome
    real do arquivo em `schemas/tables/`). Erro factual de caminho.

### negocio/ (P1) — 1 arquivo

- `RECEBIMENTO_MATERIAIS.md:34` — TOC dizia "**23** models" (texto + anchor) enquanto o heading
  da secao (:385) ja dizia "**24** models". Real: 24 classes em `app/recebimento/models.py`.
  TOC + anchor reconciliados para 24 (`#models-24-models-em-apprecebimentomodelspy`).

### odoo/ (P2) — 2 arquivos

- `PADROES_AVANCADOS.md` — tabela "Services de Referencia", 2 line-counts stale (via `wc -l`):
  `pedido_compras_service.py` 1.352 -> **1.363**; `recebimento_fisico_odoo_service.py` 773 -> **814**.
  Os outros 4 (lancamento 2.240, cte 1.168, carteira 3.117, baixa_titulos 2.167) conferem.
  Padrao 1 (`_registrar_auditoria:873` + `_executar_com_auditoria:961`) e Padrao 7
  (`_gerar_po_dfe_fire_and_poll:509-689`) tambem conferem.
- `IDS_FIXOS.md` — script de audit movido para `_deprecated/`: `00b_investigar_gotchas.py`
  atualizado em 2 ocorrencias (:94 provenance + :227 comentario) para
  `scripts/inventario_2026_05/_deprecated/00b_investigar_gotchas.py`.

## Itens NAO corrigidos (advisory / carry-forward)

- `REGRAS_MODELOS.md` — 4 schema JSON ainda inexistentes (gap SISTEMICO do `generate_schemas.py`):
  `relatorio_faturamento_importado.json`, `liberacao_antecipacao.json`,
  `contas_a_receber_abatimento.json`, `contas_a_receber_tipos.json`. As tabelas existem; o gerador
  cobre 333 tabelas mas nao estas. Backlog desde 2026-06-15: estender gerador OU suavizar pointers.
- `odoo/IDS_FIXOS.md` — `product_tmpl_id (FRETE) = 34` permanece flagado `VERIFICAR` (requer MCP
  Odoo ao vivo; pendencia historica desde 2026-04-20). `product_id=29993` confere.
- `odoo/IDS_FIXOS.md` / `PIPELINE_RECEBIMENTO_LF.md` — `payment_provider_id=30` rotulado "padrao"
  e impreciso (30 = provider de transferencia do CD / contexto CTe-frete `lancamento_odoo_service.py:47`;
  FB usa `92` em `recebimento_lf_odoo_service.py:135`, ausente das tabelas). Nao e erro de ID — e
  nomenclatura. Sugestao mantida: rotular "FB->CD" e adicionar a linha do 92.
- `ROADMAP_PROMPT_ENGINEERING_2026.md` — paths `app/agente/sdk/structured_output.py`,
  `app/templates/agente/insights.html`, `.claude/references/TOOL_ERROR_HANDLING.md`,
  `.claude/skills/analise-carteira/SKILL.md` aparecem como BROKEN no sweep mas sao deliverables
  de roadmap marcados `(criar)` — corretamente inexistentes.
- `S3_STORAGE.md:484` — `scripts/migrations/migrar_local_para_s3.py` marcado "criar se necessario"
  (script-exemplo, nao referencia factual). OK.
- `REGRAS_DEV_LOCAL.md:195-198` — `app/{recebimento,pallet,portal,pedidos}/CLAUDE.md` listados
  como BACKLOG (modulos P0-P2 que DEVEM ganhar CLAUDE.md). Intencionalmente inexistentes.
- `ROADMAP_SDK_CLIENT.md` — demais LOC da tabela "Arquivos Afetados" tambem driftaram
  (client.py 2672->3028, permissions.py 607->1129, etc.); por ser roadmap de migracao com
  baseline-snapshot, so o caminho HARD-BROKEN (`routes.py`->pacote) foi corrigido. LOC advisory.
- `especialista-odoo` aparece em tabelas "skills por fase" de PIPELINE_RECEBIMENTO/AGENT_BOILERPLATE;
  e SUBAGENT (`.claude/agents/especialista-odoo.md`), nao skill. Contexto deixa a intencao clara.

## Verificacoes que CONFEREM (sem alteracao)

- Versoes SDK/anthropic/mcp/sentry — TODAS alinhadas a requirements.txt (sem bump esta semana).
- Event listeners Separacao: defs reais @226/261/311/343 em `app/separacao/models.py` — citacoes
  agora corretas.
- Tolerancias recebimento: `validacao_nf_po_service.py:55` (QTD 10%), `:56` (data antecip -5),
  `:57` (data atras +15), `:58` (PRECO 0%) — conferem.
- IDs Odoo: company FB=1/SC=3/CD=4/LF=5; picking_types FB=1/SC=8/CD=13/LF=19; product_id=29993 —
  conferem.
- MEMORY_PROTOCOL: `_calculate_category_decay` em `memory_injection.py:348`; `PROTECTED_PATHS`
  em `memory_consolidator.py:62` — conferem.
- MARGEM_CUSTEIO: `custeio_service.py` em `app/custeio/services/`; recalc-margem em
  `carteira_service.py:2649` (set `CAMPOS_QUE_DISPARAM_RECALCULO_MARGEM`) — confere (range :2715
  off-by-3 vs :2718, nao corrigido por ser cosmetico).
- 16 subagents (`.claude/agents/*.md`); 57 skills invocaveis. Infra Render (sistema-fretes Pro Plus /
  worker Standard / Postgres Basic 4GB / Redis Starter) em INFRAESTRUTURA.md — confere com CLAUDE.md.
- S3_STORAGE.md e OBSERVABILIDADE_AGENTE.md (recem-alterados): todos os `app/*` citados existem.
- P3-P4 (design/, linx/, ssw/ — 319 arquivos ssw): scan limpo, zero `app/*` quebrado.

## Itens para Revisao Manual

- Cobertura do `generate_schemas.py` para as 4 tabelas sem JSON em REGRAS_MODELOS.
- `IDS_FIXOS.md` product_tmpl_id=34 — resolver via MCP Odoo (pendencia desde 2026-04-20).
- `IDS_FIXOS.md` / `PIPELINE_RECEBIMENTO_LF.md` — rotular `payment_provider_id` por contexto
  (30=CD/CTe, 92=FB) e listar o 92.
- STUDY_PROMPT_ENGINEERING_2026 — revisao trimestral agendada 2026-07.
