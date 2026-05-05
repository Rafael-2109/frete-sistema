# Atualizacao References 2026-05-05-1

**Data**: 2026-05-05
**Escopo**: Auditoria completa de `.claude/references/` (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files) + scan rapido P3-P4 (design, linx, ssw)
**Status**: CORRIGIDO — 3 divergencias factuais aplicadas, 1 pendencia historica permanece (product_tmpl_id Odoo desde Jan/2026).

> Auditoria mostra que o trabalho corretivo intenso da auditoria anterior (2026-04-27) deixou os P0/P1/P2 em excelente estado: SDK versions, listener line numbers, paths, schemas, IDs Odoo e regras de negocio TODOS conferem com a base de codigo. As 3 divergencias novas decorrem da introducao do Agente Lojas HORA (`app/agente_lojas/`) e de seu subagente isolado `orientador-loja`, que aumentou a contagem de subagents em `.claude/agents/` de 12 para 13. Nenhum caminho quebrado.

---

## Resumo

39 arquivos revisados em profundidade (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files). P3 design/linx + P4 ssw: scan rapido. 3 divergencias factuais novas, todas relacionadas a contagem "12 subagents" agora desatualizada. Aplicado tambem um refresh de versao (SDK 0.1.60 -> 0.1.66 confirmado em AGENT_DESIGN_GUIDE.md sobre `xhigh`/Literal type). Nenhum arquivo deletado ou renomeado.

---

## Verificacoes Factuais (todas OK)

| Item | Documentado | Real | Status |
|------|-------------|------|--------|
| `claude-agent-sdk` | 0.1.66 (BEST_PRACTICES, MCP_CAPABILITIES, STUDY_PROMPT) | 0.1.66 (`requirements.txt:65`) | OK |
| `anthropic` | 0.84.0 | 0.84.0 (`requirements.txt:64`) | OK |
| `mcp` | 1.26.0 | 1.26.0 (instalado) | OK |
| `sentry-sdk[flask]` | 2.54.0 (INFRAESTRUTURA) | 2.54.0 (`requirements.txt`) | OK |
| `system_prompt.md` | v4.3.2 (STUDY_PROMPT linha 23) | v4.3.2 (verificado via head -1) | OK |
| Skills inventario | 30 invocaveis (ROUTING_SKILLS) | 30 (ls `.claude/skills/`) | OK |
| `_calculate_category_decay` | linha 271 (MEMORY_PROTOCOL) | linha 271 (`memory_injection.py`) | OK |
| Listener `recalcular_totais_embarque` | linhas 326-436 | linha 326 inicia, ~441 final (REGRAS_CARTEIRA_SEPARACAO) | OK (drift <5 linhas) |
| Listener `setar_falta_pagamento_inicial` | 208-240 | 208 inicia, 241 final | OK |
| Listener `atualizar_status_automatico` | 244-290 | 244 inicia, 291 final | OK |
| Listener `log_reversao_status` | 293-322 | 293 inicia, 323 final | OK |
| Tolerancia qtd | 10% (`TOLERANCIA_QTD_PERCENTUAL`) | 10% em `validacao_nf_po_service.py:55` | OK |
| Tolerancia preco | 0% (`TOLERANCIA_PRECO_PERCENTUAL`) | 0% em `validacao_nf_po_service.py:58` | OK |
| Companies Odoo | FB=1, SC=3, CD=4, LF=5 | confirmado em `odoo/IDS_FIXOS.md` | OK |
| Picking Types | FB=1, SC=8, CD=13, LF=16 | confirmado | OK |
| FRETE product_id | 29993 | NAO testado nesta sessao (precisa MCP Odoo) | PENDENCIA HISTORICA |

---

## Divergencias Encontradas e Corrigidas

### 1. `AGENT_TEMPLATES.md` linha 5 — contagem "12 subagents"

- **Documentado**: "Blocos canonicos referenciados pelos 12 subagents em `.claude/agents/`"
- **Real**: 13 arquivos `.md` em `.claude/agents/` (12 Nacom Goya + 1 `orientador-loja` Lojas HORA, adicionado em 2026-04-29 pelo commit `40fcbeb9 feat(agente_lojas): M2 — 3 skills recebimento + subagente orientador-loja`)
- **Acao**: header atualizado para 2026-05-05 + texto explicita "13 subagents (12 Nacom Goya + 1 orientador-loja Lojas HORA)"
- **Severidade**: BAIXA (linhas adjacentes ja estavam OK; apenas contagem)

### 2. `AGENT_DESIGN_GUIDE.md` — escopo Nacom Goya nao explicito + contagem "12 subagents"

- **Documentado**: "manual prescritivo para criar e editar subagents no sistema de fretes Nacom Goya" + linha 39 "Os 12 subagents ja tem acesso via 6 tools no allowlist..."
- **Real**: Existe agora um 13o subagent (`orientador-loja`) em `app/agente_lojas/` que tem allowlist diferente (sem acesso a memory MCP, escopo isolado por `<loja_context>`).
- **Acao**: 
  - Linha 4: header atualizado, escopo clarificado (parentese explicando que `orientador-loja` segue mesmos principios mas tem allowlist/contexto separados)
  - Linha 39: "Os 12 subagents Nacom Goya..." (qualificado) + nota sobre `orientador-loja` ter allowlist proprio sem memory MCP
- **Severidade**: BAIXA (escopo do guia continua sendo Nacom Goya, apenas explicitamos a fronteira)

### 3. `AGENT_DESIGN_GUIDE.md` linha 42 — versao SDK obsoleta no comentario sobre `xhigh`

- **Documentado**: "ainda nao exposto no Literal type do SDK 0.1.60"
- **Real**: SDK 0.1.66 atual continua sem `xhigh` no Literal type (`Literal["low", "medium", "high", "max"]` em `.venv/lib/python3.12/site-packages/claude_agent_sdk/types.py:98,1541`). A afirmacao continua factualmente correta — apenas a versao referenciada esta desatualizada.
- **Acao**: linha 42 atualizada para "Literal type do SDK 0.1.66" (com path verificado para evidencia)
- **Severidade**: MUITO BAIXA (cosmetico — afirmacao continua correta)

### Outras mencoes "12 subagents" (NAO modificadas — historicas)

| Arquivo | Linha | Por que nao modificado |
|---------|-------|------------------------|
| `SUBAGENT_RELIABILITY.md:164` | "Revisao completa dos 12 subagents de dominio realizada em 2026-04-09" | Afirmacao temporal explicita ("2026-04-09") — historicamente correta |
| `STUDY_PROMPT_ENGINEERING_2026.md:26` | "12 subagents, 18+ skills, 7 MCP servers (35 tools)" | Snapshot de contexto do estudo (Abril/2026); recontextualizado pela linha 25 que ja menciona system_prompt v4.3.2 mas nao precisa atualizar a linha 26 |
| `AGENT_TEMPLATES.md:351` | "Criacao inicial baseada em revisao dos 12 subagents" | Historico de criacao em 2026-04-09 — afirmacao temporal correta |

---

## P0 — VERIFICADOS OK (sem divergencias)

| Arquivo | Verificacao |
|---------|-------------|
| `BEST_PRACTICES_2026.md` | header 27/04/2026; SDK 0.1.66 OK; Phase 1 + Phase 2 corretos |
| `MCP_CAPABILITIES_2026.md` | header 2026-04-27; SDK + MCP OK; 7 servers / 35 tools confere |
| `MEMORY_PROTOCOL.md` | linha 33 referencia `memory_injection.py:271` — confere |
| `ROUTING_SKILLS.md` | header 27/04/2026; 30 skills (9+2+1+1+1+1+10+5) confere |
| `STUDY_PROMPT_ENGINEERING_2026.md` | linha 23 cita system_prompt v4.3.2; linha 25 cita SDK 0.1.66 — confere |
| `INDEX.md` | header 27/04/2026; todos os 21 paths verificados existem |
| `INFRAESTRUTURA.md` | header 22/04/2026; servicos Render IDs reais; Sentry vars no codigo |
| `S3_STORAGE.md` | header 16/04/2026; `app/utils/file_storage.py` existe |
| `PADROES_BACKEND.md` | header 14/04/2026; `app/utils/json_helpers.py` existe |
| `REGRAS_OUTPUT.md` | header 31/03/2026; I1, I5, I6 mantem |
| `REGRAS_TIMEZONE.md` | header 12/02/2026; `app/utils/timezone.py` + hook OK |
| `SUBAGENT_RELIABILITY.md` | header 13/02/2026 + nota M1.1 SDK 0.1.60+ (continua valido em 0.1.66) |
| `MANUAL_CLAUDE_MD.md` | header 14/02/2026; hierarquia oficial mantida |
| `FRAMEWORK_ARISTOTELICO.md` | atemporal |
| `PROMPT_INJECTION_HARDENING.md` | header 12/04/2026; 6 layers/12 checklist OK |
| `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` | header 12/04/2026 com nota update |
| `ROADMAP_PROMPT_ENGINEERING_2026.md` | header 12/04/2026; P0 100% resolvido |
| `ROADMAP_SDK_CLIENT.md` | header 04/04/2026; status pausado coerente |

## P1 — modelos/ + negocio/ (10 files) — sem divergencias

- `REGRAS_CARTEIRA_SEPARACAO.md` (07/02): listener line numbers (208, 244, 293, 326) confirmados em `app/separacao/models.py`
- `REGRAS_MODELOS.md` (07/02): regras de Pedido (view), Embarque, EmbarqueItem mantem
- `CADEIA_PEDIDO_ENTREGA.md`: cadeia consistente
- `QUERIES_MAPEAMENTO.md`: queries Q1-Q20 OK
- `REGRAS_NEGOCIO.md` (07/03): regras Nacom Goya, grupos empresariais OK
- `REGRAS_P1_P7.md`: hierarquia P1-P7 consistente
- `FRETE_REAL_VS_TEORICO.md`: 4 valores corretos
- `MARGEM_CUSTEIO.md`: formulas margem OK
- `RECEBIMENTO_MATERIAIS.md` (07/03): Fases 1-4 IMPLEMENTADAS
- `historia_nacom.md`: historico (atemporal)

## P2 — odoo/ (9 files) — sem divergencias novas

- `IDS_FIXOS.md`: companies, picking types, journals, tolerancias **TODOS verificados via grep no codigo** (ver tabela Verificacoes Factuais acima). Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` permanece desde 31/Jan/2026.
- `MODELOS_CAMPOS.md`: mapeamento `l10n_br_fiscal.*` -> `l10n_br_ciel_it_account.*` OK
- `GOTCHAS.md`: timeouts, campos inexistentes, commit preventivo OK
- `ROUTING_ODOO.md`: arvore de decisao Odoo coerente
- `AGENT_BOILERPLATE.md`: scripts referenciados existem (`rastrear.py`, `auditoria_faturas_compra.py`, `descobrindo.py`)
- `PIPELINE_RECEBIMENTO.md`: 4 fases consistentes
- `PIPELINE_RECEBIMENTO_LF.md` (21/02): 37 etapas LF
- `CONVERSAO_UOM.md` (14/01): fluxo MILHAR/UN documentado
- `PADROES_AVANCADOS.md`: auditoria por etapa, batch, retry OK

## P3 — design/ (2 files) + linx/ (1 file) — sem divergencias

- `MAPEAMENTO_CORES.md` (18/12/2025): paths corrigidos auditoria 2026-04-20 OK
- `GUIA_COMPONENTES_UI.md` (02/03/2026): tabela botoes/badges OK
- `INTEGRACOES.md` (23/02/2026): 5 interfaces de integracao Linx OK

## P4 — ssw/ (309 files .md) — scan rapido sem anomalias

Volume alto, estabilidade alta. Nenhum arquivo modificado desde a ultima auditoria (2026-04-27). Sem sinais de atencao do README.

---

## Pendencias Historicas (mantidas)

1. **`odoo/IDS_FIXOS.md` linha 80**: Flag `product_tmpl_id ~~34~~ VERIFICAR` aberto desde 31/Jan/2026 — requer consulta MCP Odoo ao modelo `product.product` para confirmar `product_tmpl_id` real do produto FRETE (ID=29993). NAO resolvido (sem evidencia direta nesta sessao).

---

## Acoes Aplicadas

| # | Arquivo | Acao | Severidade | Status |
|---|---------|------|------------|--------|
| 1 | `AGENT_TEMPLATES.md` | Header 09/04 -> 05/05; "12 subagents" -> "13 subagents (12 Nacom Goya + 1 orientador-loja)" | BAIXA | APLICADO |
| 2 | `AGENT_DESIGN_GUIDE.md` (linha 4) | Header 09/04 -> 05/05; clarificacao Nacom Goya vs Lojas HORA | BAIXA | APLICADO |
| 3 | `AGENT_DESIGN_GUIDE.md` (linha 39) | "Os 12 subagents" -> "Os 12 subagents Nacom Goya" + nota orientador-loja | BAIXA | APLICADO |
| 4 | `AGENT_DESIGN_GUIDE.md` (linha 42) | SDK 0.1.60 -> SDK 0.1.66 (xhigh continua nao exposto) | MUITO BAIXA | APLICADO |
| 5 | `odoo/IDS_FIXOS.md` | Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` | BAIXA (requer MCP Odoo) | PENDENTE |

---

## Historico

- Auditoria 2026-04-06: 6 divergencias identificadas, nao corrigidas (sensitive file lock)
- Auditoria 2026-04-20: 7 divergencias, 6 corrigidas, 1 pendente
- Auditoria 2026-04-27: 5 divergencias novas (SDK 0.1.63 -> 0.1.66, system_prompt v4.2.0 -> v4.3.2, contagem skills, line :271), todas aplicadas no mesmo dia em sessao Claude Code dev
- Auditoria 2026-05-05 (esta): **3 divergencias novas + 1 pendencia historica**, todas decorrentes da introducao do Agente Lojas HORA (`orientador-loja` em `.claude/agents/`). **Aplicadas nesta sessao.**

Nenhum caminho quebrado. Sem deletar ou renomear arquivos.

---

## Estatisticas

- **Arquivos revisados (full)**: 39 (20 P0 + 4 P1 modelos + 6 P1 negocio + 9 P2 odoo)
- **Arquivos com scan rapido**: ~312 (3 P3 design+linx + 309 P4 ssw)
- **Arquivos com divergencia**: 2 (AGENT_TEMPLATES, AGENT_DESIGN_GUIDE)
- **Arquivos corrigidos**: 2 (3 alteracoes em AGENT_DESIGN_GUIDE + 1 em AGENT_TEMPLATES)
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 1 (`product_tmpl_id` Odoo desde Jan/2026)
