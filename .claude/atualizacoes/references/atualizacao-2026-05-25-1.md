# Atualizacao References 2026-05-25-1

**Data**: 2026-05-25
**Escopo**: Auditoria completa de `.claude/references/` (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files) + scan rapido P3-P4 (design, linx, ssw)
**Status**: CORRIGIDO — refresh de versoes SDK (0.2.82 → 0.2.87), contagem de subagents (15 → 16) e skills (41 → 48), apos commits de 2026-05-22..25.

> Auditoria detectou tres fontes de divergencia desde a auditoria 2026-05-18:
> 1. **SDK bump `claude-agent-sdk` 0.2.82 → 0.2.87** (CLI 2.1.142 → 2.1.150) em 2026-05-25 — 5 bumps de CLI (2.1.146 → 2.1.150) + adocao tardia das Task* tools introduzidas pela breaking 0.2.82 (`TodoWrite -> TaskCreate/TaskUpdate/TaskGet/TaskList`). Sem impacto pratico observado (agente ja nao usava TodoWrite). Diff GitHub `v0.2.82...v0.2.87`: 19 commits, 10 arquivos, ZERO `src/` Python.
> 2. **Novo subagent `gestor-estoque-odoo`** (commit `2af8123e`, 2026-05-24) — elevou contagem de 15 para 16 subagents totais (15 Nacom Goya + 1 orientador-loja Lojas HORA). Opus, sem `effort: xhigh` (usa default da sessao). xhigh continua em 8 subagents.
> 3. **Sete skills de estoque Odoo novas** (commits entre 2026-05-23 e 2026-05-24) — elevou skills de 41 para 48: `ajustando-quant-odoo` (✅ MATURADA), `transferindo-interno-odoo`, `operando-reservas-odoo`, `operando-picking-odoo`, `operando-mo-odoo`, `planejando-pre-etapa-odoo` (READ Odoo + WRITE banco local), `consultando-quant-odoo` (READ ao vivo Odoo).
>
> P0/P1/P2 revisados em profundidade: tolerancias (10% qtd, 0% preco), IDs Odoo (FB=1, SC=3, CD=4, LF=5; picking_types FB=1/SC=8/CD=13/LF=19), listener line numbers Separacao (215-247, 251-297, 300-329, 333-443), `_calculate_category_decay` em `memory_injection.py:271`, `PROTECTED_PATHS` em `memory_consolidator.py:62`, paths e regras de negocio TODOS conferem com o codigo. Nenhum caminho quebrado.

---

## Resumo

39 arquivos revisados em profundidade (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files). P3 design/linx + P4 ssw: scan rapido. **7 arquivos corrigidos** em 9+ alteracoes factuais: refresh SDK 0.2.82 → 0.2.87 (BEST_PRACTICES, MCP_CAPABILITIES, STUDY_PROMPT, AGENT_DESIGN_GUIDE), contagens 15 → 16 subagents + 41 → 48 skills (AGENT_DESIGN_GUIDE, AGENT_TEMPLATES, STUDY_PROMPT, SUBAGENT_RELIABILITY, INDEX), mapeamento Skill->References ampliado em INDEX para as 7 skills de estoque Odoo novas. Headers de data atualizados em todos os arquivos tocados (2026-05-18 → 2026-05-25). Nenhum arquivo deletado ou renomeado.

---

## Verificacoes Factuais

| Item | Documentado (antes) | Real | Acao |
|------|---------------------|------|------|
| `claude-agent-sdk` | 0.2.82 | **0.2.87** (`requirements.txt:65`, atual desde 2026-05-25) | ATUALIZADO |
| `claude-agent-sdk` CLI bundled | 2.1.142 | **2.1.150** | ATUALIZADO |
| `anthropic` | 0.98.1 | 0.98.1 (`requirements.txt:64`) | OK |
| `mcp` | >=1.26.0 | >=1.26.0 (`requirements.txt`) | OK |
| `sentry-sdk[flask]` | 2.54.0 (INFRAESTRUTURA) | 2.54.0 (`requirements.txt:185`) | OK |
| `system_prompt.md` | v4.3.3 (STUDY_PROMPT) | v4.3.3 (last_updated 2026-05-21) | OK |
| Subagents em `.claude/agents/` | 15 (AGENT_TEMPLATES, AGENT_DESIGN_GUIDE) | **16** (`ls .claude/agents/*.md`, +`gestor-estoque-odoo.md` desde 2026-05-24 commit `2af8123e`) | ATUALIZADO |
| Subagents com `effort: xhigh` | 8 (AGENT_DESIGN_GUIDE linha 42) | **8** (`grep "^effort: xhigh"` — `gestor-estoque-odoo` NAO declara xhigh) | OK + nota explicita adicionada |
| Skills inventario | 41 invocaveis (ROUTING_SKILLS antes; ja era 48 no proprio ROUTING_SKILLS) | **48** (`ls -d .claude/skills/*/`) | ATUALIZADO em INDEX e STUDY |
| `_calculate_category_decay` | linha 271 (MEMORY_PROTOCOL) | linha 271 (`app/agente/sdk/memory_injection.py:271`) | OK |
| `PROTECTED_PATHS` | linha 62-65 (MEMORY_PROTOCOL) | linha 62 (`app/agente/services/memory_consolidator.py`) | OK |
| Listener `setar_falta_pagamento_inicial` | linhas 215-247 (REGRAS_CARTEIRA_SEPARACAO) | linhas 215-247 (`app/separacao/models.py`) | OK |
| Listener `atualizar_status_automatico` | linhas 251-297 | linhas 251-297 | OK |
| Listener `log_reversao_status` | linhas 300-329 | linhas 300-329 | OK |
| Listener `recalcular_totais_embarque` | linhas 333-443 | linhas 333-443 | OK |
| Tolerancia qtd | 10% (`TOLERANCIA_QTD_PERCENTUAL`) | 10% em `app/recebimento/services/validacao_nf_po_service.py:55` | OK |
| Tolerancia preco | 0% (`TOLERANCIA_PRECO_PERCENTUAL`) | 0% em `app/recebimento/services/validacao_nf_po_service.py:58` | OK |
| Companies Odoo | FB=1, SC=3, CD=4, LF=5 | confirmado em `app/relatorios_fiscais/services/sped_ecd_constantes.py` | OK |
| Picking types | FB=1, SC=8, CD=13, LF=19 | atualizado 2026-05-17 (audit `00b_investigar_gotchas.py`) | OK |
| `app/utils/json_helpers.py` | citado em PADROES_BACKEND | EXISTE | OK |
| `app/utils/timezone.py` | citado em REGRAS_TIMEZONE | EXISTE | OK |
| `.claude/hooks/ban_datetime_now.py` | citado em REGRAS_TIMEZONE | EXISTE | OK |
| `.claude/skills/rastreando-odoo/scripts/rastrear.py` | citado em AGENT_BOILERPLATE | EXISTE | OK |
| Services validacao/recebimento citados em RECEBIMENTO_MATERIAIS | 4 services | EXISTEM (fiscal/nfpo/fisico/LF) | OK |

---

## Divergencias Encontradas e Corrigidas

### 1. `BEST_PRACTICES_2026.md` — SDK 0.2.82 desatualizado

- **Documentado**: `claude-agent-sdk` 0.2.82 (CLI 2.1.142 bundled)
- **Real**: `claude-agent-sdk` 0.2.87 (CLI 2.1.150 bundled), atualizado 2026-05-25 (`requirements.txt:65`)
- **Acao**: tabela de versoes atualizada, header 18/05 → 25/05, secao "0.1" expandida com bumps 0.2.83 → 0.2.87 (5 bumps CLI + adocao tardia Task* tools); historico GitHub `v0.2.82...v0.2.87` documentado (19 commits, 10 arquivos, ZERO `src/`)
- **Severidade**: ALTA (P0 lido em todas as sessoes; informacao desatualizada por 7 dias)

### 2. `MCP_CAPABILITIES_2026.md` — SDK version desatualizada

- **Documentado**: `claude-agent-sdk` 0.2.82 (CLI 2.1.142)
- **Real**: SDK 0.2.87, CLI 2.1.150
- **Acao**: header 2026-05-18 → 2026-05-25; tabela de versoes atualizada (SDK 0.2.82 → 0.2.87, CLI 2.1.142 → 2.1.150)
- **Severidade**: ALTA (P0 referenciado para decisoes de MCP/SDK)

### 3. `STUDY_PROMPT_ENGINEERING_2026.md` — SDK + contagens

- **Documentado** (linhas 25-26): SDK 0.2.82 + "15 subagents (14 Nacom Goya + 1 orientador-loja), 41 skills invocaveis"
- **Real**: SDK 0.2.87 (CLI 2.1.150, bump 2026-05-25); 16 subagents (15 Nacom Goya + 1 orientador-loja), 48 skills invocaveis
- **Acao**: linhas 25-26 atualizadas. Tambem linha 23 (system_prompt last_updated atualizado para 2026-05-21)
- **Severidade**: MEDIA (snapshot de contexto do estudo — descritivo)

### 4. `AGENT_DESIGN_GUIDE.md` — contagem 15 subagents + nota nova sobre gestor-estoque-odoo

- **Documentado**: "15 subagents Nacom Goya" + "8 subagents Opus pesados com effort: xhigh"
- **Real**: 15 subagents Nacom Goya (12 originais + `gestor-motos-assai` 2026-05-09 + `auditor-sped-ecd` 2026-05-16 + `gestor-estoque-odoo` 2026-05-24) + 1 `orientador-loja` = 16 totais; 8 com xhigh (mesmo conjunto — `gestor-estoque-odoo` Opus mas sem xhigh)
- **Acao**:
  - Header: 2026-05-18 → 2026-05-25 (refresh SDK 0.2.87 + contagem 16 subagents)
  - Linha 39 (campo `memory`): "14 subagents Nacom Goya" → "15 subagents Nacom Goya (12 originais + gestor-motos-assai 2026-05-09 + auditor-sped-ecd 2026-05-16 + gestor-estoque-odoo 2026-05-24)"
  - Linha 42 (campo `effort`): "continua valido no SDK 0.2.82" → "continua valido no SDK 0.2.87"; adicionada nota explicita "O `gestor-estoque-odoo` (Opus, 2026-05-24) NAO declara xhigh — usa default da sessao"
- **Severidade**: MEDIA (afeta contagem em manual prescritivo)

### 5. `AGENT_TEMPLATES.md` — contagem 15 subagents

- **Documentado**: "15 subagents (14 Nacom Goya + 1 orientador-loja)"
- **Real**: 16 subagents (15 Nacom Goya + 1 orientador-loja)
- **Acao**: Header 2026-05-18 → 2026-05-25; "15 subagents" → "16 subagents" com referencia commit `2af8123e`
- **Severidade**: BAIXA (cosmetico — apenas contagem)

### 6. `SUBAGENT_RELIABILITY.md` — contagem 14 Nacom Goya

- **Documentado**: header dizia "14 Nacom Goya com `auditor-sped-ecd` adicionado em 2026-05-16"; linha 202 dizia "hoje 14"
- **Real**: 15 Nacom Goya com `gestor-estoque-odoo` adicionado 2026-05-24
- **Acao**: Header 18/05/2026 → 25/05/2026; "14 Nacom Goya" → "15 Nacom Goya com `gestor-estoque-odoo` adicionado em 2026-05-24, alem do `auditor-sped-ecd` adicionado em 2026-05-16"; linha 202 atualizada ("hoje 15")
- **Severidade**: BAIXA

### 7. `INDEX.md` — header + mapeamento Skill→References ampliado

- **Documentado**: "Ultima atualizacao: 18/05/2026"; mapeamento Skill→References sem as 7 novas skills de estoque Odoo
- **Real**: 7 skills novas precisam ser mapeadas (`ajustando-quant-odoo`, `transferindo-interno-odoo`, `operando-reservas-odoo`, `operando-picking-odoo`, `operando-mo-odoo`, `planejando-pre-etapa-odoo`, `consultando-quant-odoo`)
- **Acao**: 18/05/2026 → 25/05/2026; adicionadas 7 linhas ao mapeamento apontando para `app/odoo/estoque/CLAUDE.md` + ROADMAP + docs especificos (G019/G020 invariante, G030 gotcha, G-MO-01 guard, D007 pre-etapa)
- **Severidade**: MEDIA (skill discovery via INDEX)

### Outras mencoes nao modificadas (historicas/temporais)

| Arquivo | Linha | Por que nao modificado |
|---------|-------|------------------------|
| `BEST_PRACTICES_2026.md:23` | "claude-agent-sdk 0.1.80 → 0.2.82 (2026-05-16)" | Trecho historico do trajeto de bumps — CORRETO |
| `MCP_CAPABILITIES_2026.md:11` | "Atualizado de 0.2.82 em 2026-05-25" | Trecho historico — CORRETO |
| `SUBAGENT_RELIABILITY.md:273,297` | "15 casos piloto em 3 agents" | Refere-se aos 15 CASOS do golden dataset, NAO subagents — sem ambiguidade |
| `AGENT_TEMPLATES.md:351` | "Criacao inicial baseada em revisao dos 12 subagents" | Historico de criacao em 2026-04-09 — CORRETO |
| `AGENT_DESIGN_GUIDE.md:10` | "Este guia foi criado na revisao de Abril/2026 dos 12 subagents existentes" | Contexto historico — CORRETO |

---

## P0 — VERIFICADOS OK (sem divergencias)

| Arquivo | Verificacao |
|---------|-------------|
| `MEMORY_PROTOCOL.md` | linha 33 `memory_injection.py:271` — confere; linha 74 `memory_consolidator.py:62-65` — confere (PROTECTED_PATHS set em linha 62) |
| `INDEX.md` | header atualizado 18/05 → 25/05; todos os 21 paths verificados existem |
| `INFRAESTRUTURA.md` | header 22/04/2026; servicos Render IDs reais; Sentry vars no codigo (sentry-sdk 2.54.0 confere) |
| `S3_STORAGE.md` | header 16/04/2026; `app/utils/file_storage.py` existe |
| `PADROES_BACKEND.md` | header 14/04/2026; `app/utils/json_helpers.py` existe |
| `REGRAS_OUTPUT.md` | header 31/03/2026; I1, I5, I6 mantem |
| `REGRAS_TIMEZONE.md` | header 12/02/2026; `app/utils/timezone.py` + hook `ban_datetime_now.py` OK |
| `MANUAL_CLAUDE_MD.md` | header 06/05/2026; hierarquia oficial mantida |
| `FRAMEWORK_ARISTOTELICO.md` | atemporal |
| `PROMPT_INJECTION_HARDENING.md` | header 12/04/2026; 6 layers/12 checklist OK |
| `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` | header 12/04/2026 com nota update |
| `ROADMAP_PROMPT_ENGINEERING_2026.md` | header 12/04/2026; P0 100% resolvido — gatilho `>= 0.2.0` ja atingido em 2026-05-16, revisao trimestral em 2026-07 |
| `ROADMAP_SDK_CLIENT.md` | header 04/04/2026; status pausado coerente (`toggle_mcp_server` continua nao implementado; vale para 0.2.87) |
| `ROUTING_SKILLS.md` | header 24/05/2026 (48 skills) — ja correto, header recente |

## P1 — modelos/ + negocio/ (10 files) — sem divergencias

- `REGRAS_CARTEIRA_SEPARACAO.md` (07/02/2026, refresh 18/05): listener line numbers 215-247, 251-297, 300-329, 333-443 — CONFEREM com `app/separacao/models.py` (verificado nesta auditoria)
- `REGRAS_MODELOS.md` (14/04/2026): regras de Pedido (view), Embarque, EmbarqueItem, FaturamentoProduto, DespesaExtra mantem
- `CADEIA_PEDIDO_ENTREGA.md`: cadeia consistente
- `QUERIES_MAPEAMENTO.md`: queries Q1-Q20 OK
- `REGRAS_NEGOCIO.md` (08/03/2026): regras Nacom Goya, grupos empresariais OK
- `REGRAS_P1_P7.md` (08/02/2026): hierarquia P1-P7 consistente
- `FRETE_REAL_VS_TEORICO.md` (06/04/2026): 4 valores corretos
- `MARGEM_CUSTEIO.md` (10/05/2026): atualizado com nota sobre ICMS-ST + tipos de custo
- `RECEBIMENTO_MATERIAIS.md` (07/03/2026): Fases 1-4 IMPLEMENTADAS — 4 services confirmados como existentes
- `historia_nacom.md`: historico (atemporal)

## P2 — odoo/ (9 files) — sem divergencias novas

- `IDS_FIXOS.md` (atualizado 2026-05-19): companies, picking types (FB=1/SC=8/CD=13/LF=19), locais Indisponivel (31088-31091), journals, tolerancias TODOS verificados via grep no codigo. Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` permanece desde 31/Jan/2026.
- `MODELOS_CAMPOS.md` (Janeiro/2026): mapeamento `l10n_br_fiscal.*` → `l10n_br_ciel_it_account.*` OK
- `GOTCHAS.md` (header 18/05/2026): timeouts, campos inexistentes, commit preventivo OK
- `ROUTING_ODOO.md` (18/03/2026): arvore de decisao Odoo coerente
- `AGENT_BOILERPLATE.md` (09/04/2026): scripts referenciados (`rastrear.py`, `descobrindo.py`, `auditoria_faturas_compra.py`) existem
- `PIPELINE_RECEBIMENTO.md` (Janeiro/2026): 4 fases consistentes
- `PIPELINE_RECEBIMENTO_LF.md` (21/02/2026): 37 etapas LF — service `recebimento_lf_odoo_service.py` existe
- `CONVERSAO_UOM.md` (14/01/2026): fluxo MILHAR/UN documentado
- `PADROES_AVANCADOS.md` (Janeiro/2026): auditoria por etapa, batch, retry OK

## P3 — design/ (2 files) + linx/ (1 file) — sem divergencias

- `MAPEAMENTO_CORES.md`: DESCOMISSIONADO em 2026-05-06 (placeholder de redirect para GUIA_COMPONENTES_UI.md) — correto
- `GUIA_COMPONENTES_UI.md` (06/05/2026): fonte unica, recente
- `INTEGRACOES.md` (23/02/2026): 5 interfaces de integracao Linx OK

## P4 — ssw/ (~309 files .md) — scan rapido sem anomalias

Volume alto, estabilidade alta. INDEX.md (09/04/2026) e ROUTING_SSW.md (14/04/2026) sem sinais de divergencia.

---

## Pendencias Historicas (mantidas)

1. **`odoo/IDS_FIXOS.md` linha 112**: Flag `product_tmpl_id ~~34~~ VERIFICAR` aberto desde 31/Jan/2026 — requer consulta MCP Odoo ao modelo `product.product` para confirmar `product_tmpl_id` real do produto FRETE (ID=29993). NAO resolvido nesta sessao (MCP Odoo nao exercitado).
2. **Revisao trimestral STUDY_PROMPT_ENGINEERING_2026**: gatilho explicito "Proxima revisao: quando `claude-agent-sdk >= 0.2.0`" — gatilho **foi atingido** em 2026-05-16. Documento marca proxima revisao em 2026-07. Decisao: prosseguir conforme calendario explicito ja que bumps 0.2.82 → 0.2.87 sao cosmeticos (CLI bumps + Task* tools sem impacto no agente). Registrar para revisao plena em Julho/2026.

---

## Acoes Aplicadas

| # | Arquivo | Acao | Severidade | Status |
|---|---------|------|------------|--------|
| 1 | `BEST_PRACTICES_2026.md` | Header 18/05 → 25/05; tabela versoes (SDK 0.2.82 → 0.2.87 com CLI 2.1.150); secao 0.1 expandida com bumps 0.2.83 → 0.2.87 | ALTA | APLICADO |
| 2 | `MCP_CAPABILITIES_2026.md` | Header 2026-05-18 → 2026-05-25; tabela versoes (SDK 0.2.82 → 0.2.87, CLI 2.1.142 → 2.1.150) | ALTA | APLICADO |
| 3 | `STUDY_PROMPT_ENGINEERING_2026.md` (linhas 23,25-26) | SDK 0.2.82 → 0.2.87 (CLI 2.1.150); "15 subagents, 41 skills" → "16 subagents (15 Nacom Goya + 1 orientador-loja), 48 skills invocaveis"; system_prompt last_updated atualizado para 2026-05-21 | MEDIA | APLICADO |
| 4 | `AGENT_DESIGN_GUIDE.md` (header + linhas 39,42) | 2026-05-18 → 2026-05-25 (refresh SDK 0.2.87 + contagem 16); linha 39: "14 Nacom Goya" → "15 Nacom Goya (12 originais + gestor-motos-assai + auditor-sped-ecd + gestor-estoque-odoo 2026-05-24)"; linha 42: "SDK 0.2.82" → "SDK 0.2.87" + nota explicita sobre gestor-estoque-odoo NAO declarar xhigh | MEDIA | APLICADO |
| 5 | `AGENT_TEMPLATES.md` (header + linha 5) | Header 2026-05-18 → 2026-05-25; "15 subagents" → "16 subagents (15 Nacom Goya + 1 orientador-loja)" com referencia commit `2af8123e` | BAIXA | APLICADO |
| 6 | `SUBAGENT_RELIABILITY.md` (header + linha 202) | Header 18/05 → 25/05; "14 Nacom Goya" → "15 Nacom Goya com `gestor-estoque-odoo` adicionado em 2026-05-24" | BAIXA | APLICADO |
| 7 | `INDEX.md` (header + mapeamento) | 18/05/2026 → 25/05/2026; adicionadas 7 linhas no mapeamento Skill→References para skills de estoque Odoo novas | MEDIA | APLICADO |
| 8 | `odoo/IDS_FIXOS.md` | Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` | BAIXA (requer MCP Odoo) | PENDENTE |

**Total arquivos modificados nesta sessao**: 7 (BEST_PRACTICES_2026, MCP_CAPABILITIES_2026, STUDY_PROMPT_ENGINEERING_2026, AGENT_DESIGN_GUIDE, AGENT_TEMPLATES, SUBAGENT_RELIABILITY, INDEX).

---

## Historico

- Auditoria 2026-04-06: 6 divergencias identificadas, nao corrigidas (sensitive file lock)
- Auditoria 2026-04-20: 7 divergencias, 6 corrigidas, 1 pendente
- Auditoria 2026-04-27: 5 divergencias novas, todas aplicadas
- Auditoria 2026-05-05: 3 divergencias novas (introducao orientador-loja), aplicadas
- Auditoria 2026-05-11: 5 divergencias novas (bump SDK 0.1.66 → 0.1.80, gestor-motos-assai), aplicadas
- Auditoria 2026-05-18: 8 divergencias + 1 pendencia historica (bump SDK 0.1.80 → 0.2.82, auditor-sped-ecd + 4 skills SPED ECD, drift de line numbers), todas aplicadas
- Auditoria 2026-05-25 (esta): **7 divergencias factuais corrigidas + 1 pendencia historica mantida + 1 pendencia trimestral registrada**, decorrentes do bump SDK 0.2.82 → 0.2.87 (cosmetico + Task* tools, 2026-05-25), novo subagent `gestor-estoque-odoo` (2026-05-24), e 7 skills de estoque Odoo novas (2026-05-23 / 2026-05-24). **Todas as 7 aplicadas nesta sessao.**

Nenhum caminho quebrado. Sem deletar ou renomear arquivos.

---

## Estatisticas

- **Arquivos revisados (full)**: 39 (20 P0 + 4 P1 modelos + 6 P1 negocio + 9 P2 odoo)
- **Arquivos com scan rapido**: ~312 (3 P3 design+linx + ~309 P4 ssw)
- **Arquivos corrigidos nesta sessao**: **7**
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 2 (`product_tmpl_id` Odoo desde Jan/2026; revisao trimestral STUDY agendada para Julho/2026)
