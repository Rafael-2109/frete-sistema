<!-- doc:meta
tipo: explanation
camada: L2
sot_de: —
hub: .claude/atualizacoes/references/historico.md
superseded_by: —
atualizado: 2026-06-08
-->
# Atualizacao References — 2026-06-08-1

**Data**: 2026-06-08
**Grupos revisados**: P0 (root, 22 files), P1 (modelos/ + negocio/, 10 files), P2 (odoo/, 9 files) em profundidade; P3-P4 (design/, linx/, ssw/) scan rapido
**Arquivos modificados**: 7

## Resumo

Auditoria completa de P0-P2 com verificacao de versoes contra `requirements.txt`,
caminhos no filesystem e citacoes de linha contra o codigo real. Duas fontes de drift
desde 2026-06-01: (1) bump **`claude-agent-sdk` 0.2.87 -> 0.2.89** (2026-06-03; CLI bundled
2.1.150 -> 2.1.162; cosmetico — so CLI, 0.2.88 traz 1 fix `session_store` que afeta apenas
runtime trio que nao usamos); (2) **3 skills novas** em 2026-06-02 (`carregando-motos-assai`,
`consultando-venda-loja`, `padronizando-docs`), elevando o inventario de 51 -> 54 invocaveis.
Adicionalmente, **drift de +6 linhas** nos event listeners da Separacao (refactor de
`app/separacao/models.py`). Subagents (16), xhigh (8), modelo default (Opus 4.8),
system_prompt (v4.3.3), IDs Odoo, tolerancias e MEMORY_PROTOCOL TODOS conferem.
Zero caminhos quebrados.

## Verificacoes de Versao (Fase 1)

| Componente | requirements.txt | Documentado (antes) | Acao |
|-----------|------------------|---------------------|------|
| `claude-agent-sdk` | 0.2.89 (CLI 2.1.162) | 0.2.87 / 2.1.150 | CORRIGIDO em 4 files |
| `anthropic` | 0.98.1 | 0.98.1 | OK |
| `mcp` | >=1.26.0 | >=1.26.0, 7 servers / 35 tools | OK |
| `sentry-sdk[flask]` | 2.54.0 | 2.54.0 | OK |

> Ground truth do bump: `app/agente/SDK_CHANGELOG.md` (atualizado 2026-06-03) — `0.2.89` com
> CLI bundled `2.1.162` (via 0.2.88/2.1.161). venv local: `claude-agent-sdk==0.2.89`,
> `_cli_version.py` = 2.1.162. CLI standalone instalado = 2.1.168 (nao relevante; o que
> entrega features a PROD e o CLI BUNDLED do wheel).
> Nota: venv local tem `anthropic==0.84.0` (artefato de instalacao); o pin de `requirements.txt`
> (0.98.1) e a fonte de verdade e e o que esta documentado.

## Verificacoes de Fato (Fase 1)

- **Subagentes**: 16 arquivos `.claude/agents/*.md` = 15 Nacom Goya + 1 `orientador-loja`.
  Confere com AGENT_DESIGN_GUIDE/AGENT_TEMPLATES (16) e SUBAGENT_RELIABILITY (15 NG).
- **xhigh**: 8 subagents com `effort: xhigh` (analista-carteira, auditor-financeiro,
  auditor-sped-ecd, desenvolvedor-integracao-odoo, especialista-odoo, gestor-motos-assai,
  gestor-recebimento, raio-x-pedido) — bate com AGENT_DESIGN_GUIDE:73.
- **Skills**: 54 diretorios em `.claude/skills/` (53 com SKILL.md + `consultando-sql` data
  folder). As 3 novas de 2026-06-02 (git): `carregando-motos-assai` (assai 6->7),
  `consultando-venda-loja` (HORA 5->6), `padronizando-docs` (util 11->12).
- **Modelo default**: `app/agente/config/settings.py:36` `model="claude-opus-4-8"` — OK.
- **system_prompt**: v4.3.3, last_updated 2026-05-21 (`system_prompt.md:4-5`) — sem mudanca.
- **Separacao listeners** (`app/separacao/models.py`) — **DRIFT +6 linhas** (refactor):
  `setar_falta_pagamento_inicial` 215->**221**, `atualizar_status_automatico` 251->**257**,
  `log_reversao_status` 300->**306**, `recalcular_totais_embarque` 333->**339** (termina ~455).
- **MEMORY_PROTOCOL**: `_calculate_category_decay` em `app/agente/sdk/memory_injection.py:271`
  (NAO `services/` — doc ja cita o caminho correto); `PROTECTED_PATHS:62` em
  `app/agente/services/memory_consolidator.py` — conferem.
- **IDS_FIXOS / tolerancias**: `LOCAIS_INDISPONIVEL` 31088/31089/31090/31091
  (`app/odoo/constants/locations.py:46-49`), companies FB=1/SC=3/CD=4/LF=5, QTD=10%/PRECO=0%
  (`app/recebimento/services/validacao_nf_po_service.py:55,58`) — TODOS conferem.
- **Paths**: 100% dos `app/*` citados em P0+P1+P2 existem; 100% dos `.claude/*` no INDEX
  existem; CSS de design existe; todo JSON do `ssw/` valido. **Zero caminhos quebrados.**

## Alteracoes por Grupo

### Root (P0) — 5 arquivos

- `MCP_CAPABILITIES_2026.md`: tabela de versoes `claude-agent-sdk` 0.2.87/2.1.150 ->
  0.2.89/2.1.162 + nota de bump; header -> 2026-06-08.
- `BEST_PRACTICES_2026.md`: tabela `claude-agent-sdk` -> 0.2.89/2.1.162; nova bullet de
  changelog "0.2.88 -> 0.2.89 (2026-06-03)"; ref de historico "0.1.49 -> 0.2.89";
  header -> 2026-06-08. (Linhas 17/52/58 mantidas — sao anchors/historico do bump anterior.)
- `STUDY_PROMPT_ENGINEERING_2026.md`: linha 88 SDK -> 0.2.89/CLI 2.1.162; linha 89
  "51 skills" -> "54 skills invocaveis".
- `AGENT_DESIGN_GUIDE.md`: header -> 2026-06-08 (refresh SDK 0.2.89/CLI 2.1.162);
  linha 73 "valido no SDK 0.2.87" -> "0.2.89".
- `ROUTING_SKILLS.md`: header (51 -> 54 skills, data -> 2026-06-08, +3 skills novas
  documentadas com historico 2026-05-30 preservado); TOC e titulo do inventario 51 -> 54;
  TOC Util 11->12, HORA 5->6, assai 6->7; secao Util ganhou `padronizando-docs` (12 itens).
  As secoes-corpo de HORA(6) e assai(7) ja listavam `consultando-venda-loja` e
  `carregando-motos-assai` — so o header/TOC/Util estavam stale.
- `INDEX.md`: header -> 2026-06-08; mapeamento Skill->References +3 linhas
  (`carregando-motos-assai` -> motos_assai/CLAUDE.md; `consultando-venda-loja` -> hora/CLAUDE.md;
  `padronizando-docs` -> ARQUITETURA_DE_ARTEFATOS.md + scripts/audits/doc_audit.py).
  Todos os 4 targets verificados como existentes.

### modelos/ + negocio/ (P1) — 1 arquivo

- `modelos/REGRAS_CARTEIRA_SEPARACAO.md`: 4 ranges de listeners corrigidos (+6 linhas cada)
  para 221-254 / 257-304 / 306-336 / 339-455; ref de linha 162 `models.py:333-443` ->
  `:339-455`; header -> 2026-06-08.

> Nao modificados (ja corretos): REGRAS_MODELOS, QUERIES_MAPEAMENTO, CADEIA_PEDIDO_ENTREGA,
> REGRAS_NEGOCIO, REGRAS_P1_P7, FRETE_REAL_VS_TEORICO, MARGEM_CUSTEIO, RECEBIMENTO_MATERIAIS,
> historia_nacom.

### odoo/ (P2) — 0 arquivos

- Sem alteracoes. IDS_FIXOS, GOTCHAS, ROUTING_ODOO, MODELOS_CAMPOS, PIPELINE_RECEBIMENTO,
  PIPELINE_RECEBIMENTO_LF, AGENT_BOILERPLATE, CONVERSAO_UOM, PADROES_AVANCADOS — TODOS conferem.
  PIPELINE_RECEBIMENTO ja cita `app/recebimento/services/validacao_nf_po_service.py` (caminho
  correto pos-migracao de `app/odoo/services/`).

### P3-P4 (scan rapido) — 0 arquivos

- `design/`: GUIA_COMPONENTES_UI (2026-06-02) e MAPEAMENTO_CORES atuais; refs CSS existem.
- `linx/INTEGRACOES.md`: estavel (2026-06-02).
- `ssw/` (319 .md): estavel; INDEX/ROUTING ok; todo JSON valido.

## Itens para Revisao Manual / Pendencias Historicas

- `odoo/IDS_FIXOS.md` — `product_tmpl_id (FRETE)` marcado `~~34~~ VERIFICAR`. Requer MCP Odoo
  (fora do escopo de auditoria estatica). Pendencia herdada desde 2026-04-20.
- `STUDY_PROMPT_ENGINEERING_2026.md` — revisao trimestral agendada (proxima 2026-07).

## Estatisticas

- **Arquivos revisados (full)**: 41 (22 P0 + 4 P1 modelos + 6 P1 negocio + 9 P2 odoo)
- **Arquivos com scan rapido**: ~322 (design 2 + linx 1 + ssw 319)
- **Arquivos corrigidos**: 7 (MCP_CAPABILITIES_2026, BEST_PRACTICES_2026,
  STUDY_PROMPT_ENGINEERING_2026, AGENT_DESIGN_GUIDE, ROUTING_SKILLS, INDEX,
  modelos/REGRAS_CARTEIRA_SEPARACAO)
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 2 (`product_tmpl_id` Odoo desde Jan/2026; revisao trimestral
  STUDY -> Julho/2026)
