# Atualizacao References 2026-05-11-1

**Data**: 2026-05-11
**Escopo**: Auditoria completa de `.claude/references/` (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files) + scan rapido P3-P4 (design, linx, ssw)
**Status**: CORRIGIDO — refresh de versoes SDK + contagem de subagents apos bumps de 2026-05-09.

> Auditoria mostra que apenas P0 precisou de correcoes — todas decorrentes de duas mudancas recentes:
> 1. SDK bumps (`claude-agent-sdk` 0.1.66 -> 0.1.80, `anthropic` 0.84.0 -> 0.98.1) aplicados em 2026-05-09 (commits referenciados em `app/agente/SDK_CHANGELOG.md`).
> 2. Novo subagent `gestor-motos-assai` (commits `450b4e28` + `6e9a19af`, 2026-05-09) elevou contagem de 13 -> 14 subagents.
>
> P1 (modelos/ + negocio/) e P2 (odoo/) revisados em profundidade: listeners, tolerancias, IDs Odoo, paths e regras de negocio TODOS conferem com a base de codigo. Nenhum caminho quebrado.

---

## Resumo

39 arquivos revisados em profundidade (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files). P3 design/linx + P4 ssw: scan rapido. 5 alteracoes factuais aplicadas em 4 arquivos P0: refresh das versoes SDK (`BEST_PRACTICES_2026.md`, `MCP_CAPABILITIES_2026.md`, `STUDY_PROMPT_ENGINEERING_2026.md`), e contagem 13 -> 14 subagents (`AGENT_DESIGN_GUIDE.md`, `AGENT_TEMPLATES.md`). Headers de data atualizados onde tocados. Nenhum arquivo deletado ou renomeado.

---

## Verificacoes Factuais

| Item | Documentado (antes) | Real | Acao |
|------|---------------------|------|------|
| `claude-agent-sdk` | 0.1.66 | 0.1.80 (`requirements.txt:65`, atual desde 2026-05-09) | ATUALIZADO |
| `anthropic` | 0.84.0 | 0.98.1 (`requirements.txt:64`) | ATUALIZADO |
| `mcp` | 1.26.0 | >=1.26.0 (`requirements.txt`) | NORMALIZADO ("pin recomendado" -> "pin atual em requirements.txt") |
| `sentry-sdk[flask]` | 2.54.0 (INFRAESTRUTURA) | 2.54.0 (`requirements.txt`) | OK |
| `system_prompt.md` | v4.3.2 (STUDY_PROMPT) | v4.3.3 (head -1 do arquivo, atualizado 2026-05-09) | ATUALIZADO em STUDY_PROMPT |
| Subagents em `.claude/agents/` | 13 (AGENT_TEMPLATES, AGENT_DESIGN_GUIDE) | 14 (ls `.claude/agents/*.md`, +`gestor-motos-assai.md` desde 2026-05-09) | ATUALIZADO |
| Skills inventario | 36 invocaveis (ROUTING_SKILLS) | 36 (ls `.claude/skills/`, excluindo SKILL_IMPROVEMENT_ROADMAP.md) | OK |
| `_calculate_category_decay` | linha 271 (MEMORY_PROTOCOL) | linha 271 (`app/agente/sdk/memory_injection.py:271`) | OK |
| Listener `setar_falta_pagamento_inicial` | linhas 208-240 | 208-240 (next listener inicia em 242) | OK |
| Listener `atualizar_status_automatico` | linhas 244-290 | 244-290 (next em 292) | OK |
| Listener `log_reversao_status` | linhas 293-322 | 293-322 (next em 324) | OK |
| Listener `recalcular_totais_embarque` | linhas 326-436 | 326-436 (`raise` em 436, decoracao seguinte em 443) | OK |
| Tolerancia qtd | 10% (`TOLERANCIA_QTD_PERCENTUAL`) | 10% em `validacao_nf_po_service.py:55` | OK |
| Tolerancia preco | 0% (`TOLERANCIA_PRECO_PERCENTUAL`) | 0% em `validacao_nf_po_service.py:58` | OK |
| Companies Odoo | FB=1, SC=3, CD=4, LF=5 | confirmado em `odoo/IDS_FIXOS.md` | OK |
| `gestor-motos-assai` no system_prompt | nao mencionado em refs P0 | wired em commit `6e9a19af` (2026-05-09) com `model: opus`, `effort: xhigh`, `max_turns: 50` | INFORMADO em AGENT_DESIGN_GUIDE (effort: xhigh exemplo real) |

---

## Divergencias Encontradas e Corrigidas

### 1. `BEST_PRACTICES_2026.md` — SDK versions desatualizadas

- **Documentado**: `anthropic` 0.84.0, `claude-agent-sdk` 0.1.66
- **Real**: `anthropic` 0.98.1, `claude-agent-sdk` 0.1.80 (atualizados em 2026-05-09, ver `app/agente/SDK_CHANGELOG.md`)
- **Acao**: tabela de versoes atualizada, header 27/04 -> 11/05, secao "0.1 SDK anthropic" expandida para mencionar 0.79.0 -> 0.84.0 -> 0.98.1 com beneficios novos (`APIStatusError.type`, `stop_details` estruturado em streaming) e ponteiro para SDK_CHANGELOG
- **Severidade**: ALTA (P0 lido em todas as sessoes; informacao desatualizada por 2 dias)

### 2. `MCP_CAPABILITIES_2026.md` — SDK versions + header

- **Documentado**: `claude-agent-sdk` 0.1.66, `mcp` 1.26.0 (sem mencao a anthropic na tabela)
- **Real**: SDK 0.1.80, mcp >=1.26.0, anthropic 0.98.1
- **Acao**: header 2026-04-27 -> 2026-05-11; tabela de versoes atualizada com linha nova para `anthropic` 0.98.1; mencao ao SDK 0.1.77 (`skills` option em `ClaudeAgentOptions`) e bumps 0.1.78/0.1.79/0.1.80 com ponteiro para SDK_CHANGELOG; titulo "Estado do Sistema (Abr/2026)" -> "(Mai/2026)"
- **Severidade**: ALTA (P0 referenciado para decisoes de MCP/SDK)

### 3. `AGENT_DESIGN_GUIDE.md` — contagem 12 subagents + SDK version

- **Documentado**: "Os 12 subagents Nacom Goya..." (linha 39, contagem ja qualificada na auditoria anterior); "SDK 0.1.66" no Literal type (linha 42)
- **Real**: 13 subagents Nacom Goya (12 originais + `gestor-motos-assai` 2026-05-09) + 1 `orientador-loja` Lojas HORA = 14 totais em `.claude/agents/`; SDK 0.1.80 atual
- **Acao**:
  - Header: 2026-05-05 -> 2026-05-11 (refresh SDK 0.1.80 + contagem 14 subagents)
  - Linha 39: "Os 12 subagents Nacom Goya" -> "Os 13 subagents Nacom Goya (12 originais + `gestor-motos-assai` adicionado em 2026-05-09)"
  - Linha 42: "Literal type do SDK 0.1.66" -> "Literal type do SDK 0.1.80" + nota de uso real: `gestor-motos-assai` declara `effort: xhigh` no frontmatter
- **Severidade**: MEDIA (afeta contagem em manual prescritivo; afirmacao sobre `xhigh` continua factualmente correta)

### 4. `AGENT_TEMPLATES.md` — contagem 13 subagents

- **Documentado**: "Blocos canonicos referenciados pelos 13 subagents..." + nota "(12 Nacom Goya + 1 orientador-loja)"
- **Real**: 14 subagents (13 Nacom Goya: 12 originais + `gestor-motos-assai` + 1 `orientador-loja`)
- **Acao**: Header 2026-05-05 -> 2026-05-11 (contagem 13 -> 14); texto explicita o motivo (commit `450b4e28`, 2026-05-09)
- **Severidade**: BAIXA (cosmetico — apenas contagem)

### 5. `STUDY_PROMPT_ENGINEERING_2026.md` — SDK versions + system_prompt + contagem

- **Documentado** (linhas 23, 25-26): system_prompt v4.3.2 (2026-04-14); SDK 0.1.66 + anthropic 0.84.0; "12 subagents, 18+ skills"
- **Real**: system_prompt v4.3.3 (2026-05-09 com `gestor-motos-assai` wired); SDK 0.1.80 + anthropic 0.98.1; 14 subagents (13 Nacom Goya + 1 orientador-loja), 36 skills invocaveis
- **Acao**: Linhas 23, 25, 26 atualizadas. v4.3.2 -> v4.3.3, SDK 0.1.66 -> 0.1.80, anthropic 0.84.0 -> 0.98.1, "12 subagents, 18+ skills" -> "14 subagents (13 Nacom Goya + 1 orientador-loja Lojas HORA), 36 skills invocaveis"
- **Severidade**: MEDIA (snapshot de contexto do estudo — descritivo, nao prescritivo)

### Outras mencoes "12 subagents" (NAO modificadas — historicas/temporais)

| Arquivo | Linha | Por que nao modificado |
|---------|-------|------------------------|
| `SUBAGENT_RELIABILITY.md:164` | "Revisao completa dos 12 subagents de dominio realizada em 2026-04-09" | Afirmacao temporal explicita — historicamente correta |
| `AGENT_TEMPLATES.md:351` | "2026-04-09: Criacao inicial baseada em revisao dos 12 subagents" | Historico de criacao em 2026-04-09 — correto |
| `AGENT_DESIGN_GUIDE.md:10` | "Este guia foi criado na revisao de Abril/2026 dos 12 subagents existentes" | Contexto historico do guia — correto |

---

## P0 — VERIFICADOS OK (sem divergencias)

| Arquivo | Verificacao |
|---------|-------------|
| `MEMORY_PROTOCOL.md` | linha 33 referencia `memory_injection.py:271` — confere |
| `ROUTING_SKILLS.md` | header 27/04/2026; 36 skills (9+2+1+1+1+1+1+10+5+6) confere com `ls .claude/skills/` |
| `INDEX.md` | header atualizado 27/04 -> 11/05; todos os 21 paths verificados existem |
| `INFRAESTRUTURA.md` | header 22/04/2026; servicos Render IDs reais; Sentry vars no codigo (sentry-sdk 2.54.0 confere) |
| `S3_STORAGE.md` | header 16/04/2026; `app/utils/file_storage.py` existe |
| `PADROES_BACKEND.md` | header 14/04/2026; `app/utils/json_helpers.py` existe |
| `REGRAS_OUTPUT.md` | header 31/03/2026; I1, I5, I6 mantem |
| `REGRAS_TIMEZONE.md` | header 12/02/2026; `app/utils/timezone.py` + hook OK |
| `SUBAGENT_RELIABILITY.md` | header 13/02/2026 + nota M1.1 SDK 0.1.60+ (continua valido em 0.1.80) |
| `MANUAL_CLAUDE_MD.md` | header 06/05/2026; hierarquia oficial mantida |
| `FRAMEWORK_ARISTOTELICO.md` | atemporal |
| `PROMPT_INJECTION_HARDENING.md` | header 12/04/2026; 6 layers/12 checklist OK |
| `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` | header 12/04/2026 com nota update |
| `ROADMAP_PROMPT_ENGINEERING_2026.md` | header 12/04/2026; P0 100% resolvido |
| `ROADMAP_SDK_CLIENT.md` | header 04/04/2026; status pausado coerente (toggle_mcp_server nao implementado, vale para 0.1.80 ainda) |

## P1 — modelos/ + negocio/ (10 files) — sem divergencias

- `REGRAS_CARTEIRA_SEPARACAO.md` (07/02): listener line numbers (208-240, 244-290, 293-322, 326-436) **REVERIFICADOS** em `app/separacao/models.py` — TODOS exatos
- `REGRAS_MODELOS.md` (07/02): regras de Pedido (view), Embarque, EmbarqueItem mantem
- `CADEIA_PEDIDO_ENTREGA.md`: cadeia consistente
- `QUERIES_MAPEAMENTO.md`: queries Q1-Q20 OK
- `REGRAS_NEGOCIO.md` (07/03): regras Nacom Goya, grupos empresariais OK
- `REGRAS_P1_P7.md`: hierarquia P1-P7 consistente
- `FRETE_REAL_VS_TEORICO.md`: 4 valores corretos
- `MARGEM_CUSTEIO.md`: atualizado 2026-05-10 com nota sobre ICMS-ST (recente)
- `RECEBIMENTO_MATERIAIS.md` (07/03): Fases 1-4 IMPLEMENTADAS
- `historia_nacom.md`: historico (atemporal)

## P2 — odoo/ (9 files) — sem divergencias novas

- `IDS_FIXOS.md`: companies, picking types, journals, tolerancias TODOS verificados via grep no codigo. Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` permanece desde 31/Jan/2026.
- `MODELOS_CAMPOS.md`: mapeamento `l10n_br_fiscal.*` -> `l10n_br_ciel_it_account.*` OK
- `GOTCHAS.md`: timeouts, campos inexistentes, commit preventivo OK
- `ROUTING_ODOO.md`: arvore de decisao Odoo coerente
- `AGENT_BOILERPLATE.md`: scripts referenciados existem
- `PIPELINE_RECEBIMENTO.md`: 4 fases consistentes
- `PIPELINE_RECEBIMENTO_LF.md` (21/02): 37 etapas LF
- `CONVERSAO_UOM.md` (14/01): fluxo MILHAR/UN documentado
- `PADROES_AVANCADOS.md`: auditoria por etapa, batch, retry OK

## P3 — design/ (2 files) + linx/ (1 file) — sem divergencias

- `MAPEAMENTO_CORES.md`: DESCOMISSIONADO em 2026-05-06 (placeholder de redirect para GUIA_COMPONENTES_UI.md) — correto
- `GUIA_COMPONENTES_UI.md` (06/05/2026): fonte unica, recente
- `INTEGRACOES.md` (23/02/2026): 5 interfaces de integracao Linx OK

## P4 — ssw/ (309 files .md) — scan rapido sem anomalias

Volume alto, estabilidade alta. Nenhum arquivo modificado desde a ultima auditoria (2026-05-05). INDEX.md e ROUTING_SSW.md sem sinais de divergencia.

---

## Pendencias Historicas (mantidas)

1. **`odoo/IDS_FIXOS.md` linha 80**: Flag `product_tmpl_id ~~34~~ VERIFICAR` aberto desde 31/Jan/2026 — requer consulta MCP Odoo ao modelo `product.product` para confirmar `product_tmpl_id` real do produto FRETE (ID=29993). NAO resolvido (sem evidencia direta nesta sessao; MCP Odoo nao foi exercitado).

---

## Acoes Aplicadas

| # | Arquivo | Acao | Severidade | Status |
|---|---------|------|------------|--------|
| 1 | `BEST_PRACTICES_2026.md` | Header 27/04 -> 11/05; tabela versoes (anthropic 0.84.0 -> 0.98.1, SDK 0.1.66 -> 0.1.80, mcp pin "atual"); secao 0.1 expandida com beneficios 0.87.0/0.88.0/0.98.0 e ponteiro SDK_CHANGELOG | ALTA | APLICADO |
| 2 | `MCP_CAPABILITIES_2026.md` | Header "Abr/2026" -> "Mai/2026", 2026-04-27 -> 2026-05-11; tabela versoes (SDK 0.1.66 -> 0.1.80 com 0.1.77 skills option, anthropic linha nova 0.98.1, mcp >=1.26.0 + ponteiro SDK_CHANGELOG) | ALTA | APLICADO |
| 3 | `AGENT_DESIGN_GUIDE.md` (header) | 2026-05-05 -> 2026-05-11 (refresh SDK 0.1.80 + contagem 14 subagents) | MEDIA | APLICADO |
| 4 | `AGENT_DESIGN_GUIDE.md` (linha 39) | "12 subagents Nacom Goya" -> "13 subagents Nacom Goya (12 originais + gestor-motos-assai 2026-05-09)" | MEDIA | APLICADO |
| 5 | `AGENT_DESIGN_GUIDE.md` (linha 42) | "Literal type do SDK 0.1.66" -> "Literal type do SDK 0.1.80" + exemplo `gestor-motos-assai` (effort: xhigh) | MEDIA | APLICADO |
| 6 | `AGENT_TEMPLATES.md` | Header 2026-05-05 -> 2026-05-11; "13 subagents" -> "14 subagents (13 Nacom Goya + 1 orientador-loja)" com referencia commit 450b4e28 | BAIXA | APLICADO |
| 7 | `STUDY_PROMPT_ENGINEERING_2026.md` (linha 23) | system_prompt v4.3.2 -> v4.3.3 (2026-05-09 com gestor-motos-assai wired) | MEDIA | APLICADO |
| 8 | `STUDY_PROMPT_ENGINEERING_2026.md` (linhas 25-26) | SDK 0.1.66 + anthropic 0.84.0 -> 0.1.80 + 0.98.1; "12 subagents, 18+ skills" -> "14 subagents (13 Nacom Goya + 1 orientador-loja), 36 skills invocaveis" | MEDIA | APLICADO |
| 9 | `INDEX.md` (header) | 27/04/2026 -> 11/05/2026 | BAIXA | APLICADO |
| 10 | `odoo/IDS_FIXOS.md` | Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` | BAIXA (requer MCP Odoo) | PENDENTE |

**Total arquivos modificados nesta sessao**: 6 (BEST_PRACTICES_2026, MCP_CAPABILITIES_2026, AGENT_DESIGN_GUIDE, AGENT_TEMPLATES, STUDY_PROMPT_ENGINEERING_2026, INDEX).

---

## Historico

- Auditoria 2026-04-06: 6 divergencias identificadas, nao corrigidas (sensitive file lock)
- Auditoria 2026-04-20: 7 divergencias, 6 corrigidas, 1 pendente
- Auditoria 2026-04-27: 5 divergencias novas (SDK 0.1.63 -> 0.1.66, system_prompt v4.2.0 -> v4.3.2, contagem skills, line :271), todas aplicadas
- Auditoria 2026-05-05: 3 divergencias novas (introducao orientador-loja), aplicadas no mesmo dia
- Auditoria 2026-05-11 (esta): **5 divergencias novas + 1 pendencia historica**, decorrentes do bump SDK em 2026-05-09 (`claude-agent-sdk` 0.1.66 -> 0.1.80, `anthropic` 0.84.0 -> 0.98.1) e do novo subagent `gestor-motos-assai`. **Todas aplicadas nesta sessao.**

Nenhum caminho quebrado. Sem deletar ou renomear arquivos.

---

## Estatisticas

- **Arquivos revisados (full)**: 39 (20 P0 + 4 P1 modelos + 6 P1 negocio + 9 P2 odoo)
- **Arquivos com scan rapido**: ~312 (3 P3 design+linx + 309 P4 ssw)
- **Arquivos com divergencia**: 6 (BEST_PRACTICES_2026, MCP_CAPABILITIES_2026, AGENT_DESIGN_GUIDE, AGENT_TEMPLATES, STUDY_PROMPT_ENGINEERING_2026, INDEX)
- **Arquivos corrigidos**: 6
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 1 (`product_tmpl_id` Odoo desde Jan/2026)
