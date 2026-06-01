# Atualizacao References — 2026-06-01-1

**Data**: 2026-06-01
**Grupos revisados**: P0 (root, 20 files), P1 (modelos/ + negocio/, 10 files), P2 (odoo/, 9 files) em profundidade; P3-P4 (design/, linx/, ssw/) scan rapido
**Arquivos modificados**: 5

## Resumo

Auditoria completa de P0-P2 com verificacao de versoes contra `requirements.txt`,
caminhos no filesystem e citacoes de linha contra o codigo real. Duas fontes de drift
desde 2026-05-25: (1) migracao do modelo default **Opus 4.7 -> 4.8** (2026-05-28, config
server-side sem mudanca de SDK), ainda nao propagada para STUDY/AGENT_DESIGN_GUIDE;
(2) **3 skills Odoo novas** (`escriturando-odoo` ABRANGENTE, `faturando-odoo` Skill 8,
`auditando-cadastro-fiscal-odoo` PRE-FLIGHT) ja contabilizadas no header de ROUTING_SKILLS
(51 skills, 30/05) mas ausentes do mapeamento Skill->References do INDEX e das contagens
do STUDY. Adicionalmente, 2 correcoes de citacao de linha/caminho em PADROES_BACKEND e
MARGEM_CUSTEIO. Versoes (SDK 0.2.87 / anthropic 0.98.1 / mcp >=1.26.0) TODAS conferem.
Zero caminhos quebrados.

## Verificacoes de Versao (Fase 1)

| Componente | requirements.txt | Documentado | Status |
|-----------|------------------|-------------|--------|
| `anthropic` | 0.98.1 | 0.98.1 (BEST_PRACTICES, MCP_CAPABILITIES) | OK |
| `claude-agent-sdk` | 0.2.87 (CLI 2.1.150) | 0.2.87 / 2.1.150 | OK |
| `mcp` | >=1.26.0 | >=1.26.0, 7 servers / 35 tools | OK |
| `sentry-sdk[flask]` | 2.54.0 | 2.54.0 (INFRAESTRUTURA) | OK |

> Nota: o venv local pode ter `anthropic` abaixo do pin (artefato de instalacao). O pin de
> `requirements.txt` (0.98.1) e a fonte de verdade e e o que esta documentado.

## Verificacoes de Fato (Fase 1)

- **Subagentes**: 16 arquivos `.claude/agents/*.md` = 15 Nacom Goya + 1 `orientador-loja`.
  Confere com AGENT_DESIGN_GUIDE/AGENT_TEMPLATES (16 totais) e SUBAGENT_RELIABILITY (15 NG).
- **xhigh**: 8 subagents com `effort: xhigh` (analista-carteira, auditor-financeiro,
  auditor-sped-ecd, desenvolvedor-integracao-odoo, especialista-odoo, gestor-motos-assai,
  gestor-recebimento, raio-x-pedido) — lista bate com AGENT_DESIGN_GUIDE:42.
- **Skills**: 51 diretorios em `.claude/skills/` (50 com SKILL.md + `consultando-sql` data
  folder). Inventario ROUTING_SKILLS bate: Odoo 19 + SSW 2 + Portal 1 + CarVia 1 + Agente 1
  + Sentry 1 + Util 11 + HORA 5 + assai 6 + SPED 4 = 51.
- **Modelo default**: `app/agente/config/settings.py:36` `model="claude-opus-4-8"`;
  `sdk/pricing.py:45` `DEFAULT_MODEL='claude-opus-4-8'` (migracao 4.7->4.8 em 2026-05-28,
  documentada em `app/agente/SDK_CHANGELOG.md`).
- **system_prompt**: v4.3.3, last_updated 2026-05-21 (`app/agente/prompts/system_prompt.md:4-5`).
- **Separacao listeners** (`app/separacao/models.py`): `setar_falta_pagamento_inicial:215`,
  `atualizar_status_automatico:251`, `log_reversao_status:300`, `recalcular_totais_embarque:333`
  (termina ~449) — TODOS conferem com REGRAS_CARTEIRA_SEPARACAO.md.
- **MEMORY_PROTOCOL**: `_calculate_category_decay:271` (`memory_injection.py`),
  `PROTECTED_PATHS:62` (`memory_consolidator.py`) — conferem.
- **IDS_FIXOS / tolerancias**: `PRODUTO_SERVICO_FRETE_ID=29993`, `LOCAIS_INDISPONIVEL`
  31088/31089/31090/31091 (`app/odoo/constants/locations.py:46-49`), picking types
  FB=1/SC=8/CD=13/LF=19 (`picking_types.py:194-198`), QTD=10%/PRECO=0%
  (`validacao_nf_po_service.py:55,58`), companies FB=1/SC=3/CD=4/LF=5 — TODOS conferem.
- **odoo/ paths**: gotchas G030/G031/G037/G038, `recebimento_lf_odoo_service.py`,
  scripts estoque novos (escrituracao/faturamento/cadastro_fiscal_audit +
  orchestrators/inventario_pipeline) — TODOS existem.
- **INDEX.md**: 15 caminhos verificados, TODOS existem.

## Alteracoes por Grupo

### Root (P0)

- `STUDY_PROMPT_ENGINEERING_2026.md` (24,26): "Opus 4.7 (default)" -> "Opus 4.8
  (default desde 2026-05-28 — migracao sem mudanca de SDK; rollback via env `AGENT_MODEL`)";
  "48 skills invocaveis" -> "51 skills invocaveis".
- `AGENT_DESIGN_GUIDE.md` (42): tier Opus "(4.5, 4.6, 4.7)" -> "(4.5, 4.6, 4.7, 4.8)";
  "Opus 4.7-specific ... valido no SDK 0.2.87" -> "Opus-specific ... valido no SDK 0.2.87 e
  no modelo default atual Opus 4.8, migrado de 4.7 em 2026-05-28".
- `INDEX.md`: header 25/05 -> 2026-06-01; mapeamento Skill->References +3 linhas
  (`escriturando-odoo` -> CLAUDE.md + `fluxos/1.2.1-escriturar-dfe-industrializacao.md` +
  IDS_FIXOS; `auditando-cadastro-fiscal-odoo` -> CLAUDE.md G017/G018/G035/G014 + D-OPS-2/3;
  `faturando-odoo` -> CLAUDE.md + `orchestrators/inventario_pipeline.py` + IDS_FIXOS).
  Todos os paths citados verificados como existentes.
- `PADROES_BACKEND.md`: tabela de callsites `sanitize_for_json` corrigida —
  `cotacao_v2_service.py` 240/385 -> 238/400/500 (3 callsites); nota de adocao ampla +
  ponteiro `grep -rn`. Header -> 2026-06-01.
  FONTE: `app/carvia/services/pricing/cotacao_v2_service.py:238,400,500`.

> Nao modificados (ja corretos): BEST_PRACTICES_2026 (SDK 0.2.87; Opus 4.6 mencao historica),
> MCP_CAPABILITIES_2026 (0.2.87 / 2.1.150), INFRAESTRUTURA, REGRAS_TIMEZONE, MEMORY_PROTOCOL,
> REGRAS_OUTPUT, AGENT_TEMPLATES (16 subagents), SUBAGENT_RELIABILITY (15 NG), S3_STORAGE,
> ROUTING_SKILLS (header 30/05, 51 skills), FRAMEWORK_ARISTOTELICO, MANUAL_CLAUDE_MD,
> PROMPT_INJECTION_HARDENING, ROADMAP_SDK_CLIENT, ROADMAP_PROMPT_ENGINEERING_2026,
> STUDY_QUALITY_REVIEW.

### modelos/ + negocio/ (P1)

- `negocio/MARGEM_CUSTEIO.md`: 3 refs de linha/caminho corrigidas.
  1. `custeio_service.py` -> caminho explicito `app/custeio/services/custeio_service.py`
     (NAO `app/carteira/services/`). Bloco PROTECAO MANUAL `:826-841` -> `:827-841`.
  2. BONIFICACAO `carteira_service.py:1371` -> `:1376` (bloco `# VERIFICAR SE E BONIFICACAO`,
     flag `eh_bonificacao` em :1379).
  3. BOM soma parcial `:1122-1133` -> `app/custeio/services/custeio_service.py:1140,1160`.
  Nota de revisao 2026-06-01 adicionada ao header. Verificado: o service vive em
  `app/custeio/services/` (confirmado por `ls`).

> Nao modificados (ja corretos): REGRAS_CARTEIRA_SEPARACAO, REGRAS_MODELOS, QUERIES_MAPEAMENTO,
> CADEIA_PEDIDO_ENTREGA, REGRAS_NEGOCIO, REGRAS_P1_P7, FRETE_REAL_VS_TEORICO,
> RECEBIMENTO_MATERIAIS (services existem), historia_nacom.

### odoo/ (P2)

- Sem alteracoes. IDS_FIXOS, GOTCHAS (header 27/05/2026 com G037/G038/G-MO-05), ROUTING_ODOO,
  MODELOS_CAMPOS, PIPELINE_RECEBIMENTO, PIPELINE_RECEBIMENTO_LF (service existe),
  AGENT_BOILERPLATE, CONVERSAO_UOM, PADROES_AVANCADOS — TODOS conferem.

### P3-P4 (scan rapido)

- `design/`: GUIA_COMPONENTES_UI (FONTE UNICA, 2026-05-06) atual; refs CSS
  `base/_bootstrap-overrides.css`, `tokens/_design-tokens.css`, `components/_badges.css`
  TODOS existem. MAPEAMENTO_CORES corretamente OBSOLETO.
- `linx/INTEGRACOES.md`: estavel (23/02/2026).
- `ssw/` (309 .md): estavel; INDEX/ROUTING ok; `url-map.json` JSON valido.
- NOTA fora de escopo: `~/.claude/CLAUDE.md` (dev-only) e `app/static/css/README.md`
  referenciam `bootstrap-theme-override.css` que hoje vive em
  `app/static/css/base/_bootstrap-overrides.css` — NAO em `.claude/references/`.

## Itens para Revisao Manual / Pendencias Historicas

- `odoo/IDS_FIXOS.md:112` — `product_tmpl_id (FRETE)` marcado `~~34~~ VERIFICAR`.
  Requer MCP Odoo (fora do escopo de auditoria estatica). Pendencia herdada desde 2026-04-20.
- `STUDY_PROMPT_ENGINEERING_2026.md` — revisao trimestral agendada (proxima 2026-07).

## Estatisticas

- **Arquivos revisados (full)**: 39 (20 P0 + 4 P1 modelos + 6 P1 negocio + 9 P2 odoo)
- **Arquivos com scan rapido**: ~312 (design 2 + linx 1 + ssw 309)
- **Arquivos corrigidos**: 5 (STUDY_PROMPT_ENGINEERING_2026, AGENT_DESIGN_GUIDE, INDEX,
  PADROES_BACKEND, negocio/MARGEM_CUSTEIO)
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 2 (`product_tmpl_id` Odoo desde Jan/2026; revisao trimestral
  STUDY -> Julho/2026)
