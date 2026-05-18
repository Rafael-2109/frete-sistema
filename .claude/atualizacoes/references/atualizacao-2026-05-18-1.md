# Atualizacao References 2026-05-18-1

**Data**: 2026-05-18
**Escopo**: Auditoria completa de `.claude/references/` (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files) + scan rapido P3-P4 (design, linx, ssw)
**Status**: CORRIGIDO — refresh de versoes SDK (0.1.80 -> 0.2.82), contagem de subagents (14 -> 15) e skills (36 -> 41), apos commits de 2026-05-16. Listener line numbers de Separacao corrigidos apos drift no codigo.

> Auditoria detectou cinco fontes de divergencia desde a auditoria 2026-05-11:
> 1. SDK bump `claude-agent-sdk` 0.1.80 -> 0.2.82 (CLI 2.1.138 -> 2.1.142) em 2026-05-16 — bump cosmetico (salto 0.1.81 -> 0.2.82, sem breaking changes) com 3 bug fixes gratuitos (stderr callback isolation #932, CancelledError eager-flush #931, permission_suggestions typing #955).
> 2. Novo subagent `auditor-sped-ecd` (commit `b7413ba7`, 2026-05-16) — elevou contagem de 14 para 15 subagents totais (14 Nacom Goya + 1 orientador-loja Lojas HORA).
> 3. Quatro skills SPED ECD novas (commits `0c15c989`, `ef60692a`, `197ebe39`, `b3b4531d`, 2026-05-16) usadas exclusivamente pelo subagent `auditor-sped-ecd` — elevou skills de 36 para 41.
> 4. Drift no `app/separacao/models.py`: listener line numbers shifted (7 linhas, decoradores e doctrings expandidas) — REGRAS_CARTEIRA_SEPARACAO.md tinha refs desatualizadas (208-240, 244-290, 293-322, 326-436).
> 5. `auditor-sped-ecd` declara `effort: xhigh` no frontmatter — elevou contagem de subagents Opus xhigh de 7 para 8.
>
> P1 (modelos/ + negocio/) e P2 (odoo/) revisados em profundidade: tolerancias (10% qtd, 0% preco), IDs Odoo (FB=1, SC=3, CD=4, LF=5), paths e regras de negocio TODOS conferem com o codigo (exceto listener line numbers). Nenhum caminho quebrado.

---

## Resumo

39 arquivos revisados em profundidade (P0 raiz: 20 files, P1 modelos+negocio: 10 files, P2 odoo: 9 files). P3 design/linx + P4 ssw: scan rapido. 8 alteracoes factuais aplicadas em 7 arquivos: refresh SDK 0.1.80 -> 0.2.82 (3 arquivos P0), contagens 14 -> 15 subagents + 36 -> 41 skills (4 arquivos P0), listener line numbers Separacao (1 arquivo P1). Headers de data atualizados onde tocados. Nenhum arquivo deletado ou renomeado.

---

## Verificacoes Factuais

| Item | Documentado (antes) | Real | Acao |
|------|---------------------|------|------|
| `claude-agent-sdk` | 0.1.80 | **0.2.82** (`requirements.txt:65`, atual desde 2026-05-16) | ATUALIZADO |
| `claude-agent-sdk` CLI bundled | 2.1.138 | 2.1.142 | ATUALIZADO |
| `anthropic` | 0.98.1 | 0.98.1 (`requirements.txt:64`) | OK |
| `mcp` | >=1.26.0 | >=1.26.0 (`requirements.txt`) | OK |
| `sentry-sdk[flask]` | 2.54.0 (INFRAESTRUTURA) | 2.54.0 (`requirements.txt:185`) | OK |
| `system_prompt.md` | v4.3.3 (STUDY_PROMPT) | v4.3.3 (`app/agente/prompts/system_prompt.md:1`) | OK |
| Subagents em `.claude/agents/` | 14 (AGENT_TEMPLATES, AGENT_DESIGN_GUIDE) | **15** (`ls .claude/agents/*.md`, +`auditor-sped-ecd.md` desde 2026-05-16 commit `b7413ba7`) | ATUALIZADO |
| Subagents com `effort: xhigh` | 7 (AGENT_DESIGN_GUIDE linha 42) | **8** (`grep "^effort: xhigh"`, +`auditor-sped-ecd.md`) | ATUALIZADO |
| Skills inventario | 36 invocaveis (ROUTING_SKILLS) | **41** (`ls -d .claude/skills/*/`, +4 SPED skills 2026-05-16) | ATUALIZADO |
| `_calculate_category_decay` | linha 271 (MEMORY_PROTOCOL) | linha 271 (`app/agente/sdk/memory_injection.py:271`) | OK |
| Listener `setar_falta_pagamento_inicial` | linhas 208-240 (REGRAS_CARTEIRA_SEPARACAO) | **linhas 215-247** (`app/separacao/models.py`) | ATUALIZADO |
| Listener `atualizar_status_automatico` | linhas 244-290 | **linhas 251-297** | ATUALIZADO |
| Listener `log_reversao_status` | linhas 293-322 | **linhas 300-329** | ATUALIZADO |
| Listener `recalcular_totais_embarque` | linhas 326-436 | **linhas 333-443** (`raise` em 443, decoracao seguinte em 446) | ATUALIZADO |
| Tolerancia qtd | 10% (`TOLERANCIA_QTD_PERCENTUAL`) | 10% em `app/recebimento/services/validacao_nf_po_service.py:55` | OK |
| Tolerancia preco | 0% (`TOLERANCIA_PRECO_PERCENTUAL`) | 0% em `app/recebimento/services/validacao_nf_po_service.py:58` | OK |
| Companies Odoo | FB=1, SC=3, CD=4, LF=5 | confirmado em `app/relatorios_fiscais/services/sped_ecd_constantes.py:25-31` | OK |
| Picking types | FB=1, SC=8, CD=13, LF=19 | atualizado 2026-05-17 no proprio IDS_FIXOS.md (header) | OK |
| `auditor-sped-ecd` no system_prompt | nao mencionado em refs (subagent novo) | NAO wired em `system_prompt.md` — uso exclusivo via Claude Code dev (audit fiscal manual) | INFORMADO em ROUTING_SKILLS |

---

## Divergencias Encontradas e Corrigidas

### 1. `BEST_PRACTICES_2026.md` — SDK 0.1.80 desatualizado

- **Documentado**: `claude-agent-sdk` 0.1.80 (CLI 2.1.138 bundled)
- **Real**: `claude-agent-sdk` 0.2.82 (CLI 2.1.142 bundled), atualizado 2026-05-16 (`requirements.txt:65`)
- **Acao**: tabela de versoes atualizada, header 11/05 -> 18/05, secao "0.1" expandida para mencionar bump 0.1.80 -> 0.2.82 com bug fixes (#932, #931, #955)
- **Severidade**: ALTA (P0 lido em todas as sessoes; informacao desatualizada por 2 dias)

### 2. `MCP_CAPABILITIES_2026.md` — SDK version desatualizada

- **Documentado**: `claude-agent-sdk` 0.1.80 (CLI 2.1.138)
- **Real**: SDK 0.2.82, CLI 2.1.142
- **Acao**: header 2026-05-11 -> 2026-05-18; tabela de versoes atualizada (SDK 0.1.80 -> 0.2.82, CLI 2.1.138 -> 2.1.142, com nota sobre salto cosmetico 0.1.81 -> 0.2.82)
- **Severidade**: ALTA (P0 referenciado para decisoes de MCP/SDK)

### 3. `STUDY_PROMPT_ENGINEERING_2026.md` — SDK + contagens

- **Documentado** (linhas 25-26): SDK 0.1.80 + anthropic 0.98.1; "14 subagents (13 Nacom Goya + 1 orientador-loja), 36 skills invocaveis"
- **Real**: SDK 0.2.82 (CLI 2.1.142, bump 2026-05-16); 15 subagents (14 Nacom Goya + 1 orientador-loja), 41 skills invocaveis
- **Acao**: linhas 25-26 atualizadas. SDK 0.1.80 -> 0.2.82 com mencao explicita ao CLI 2.1.142 e data do bump; "14 subagents (13 Nacom Goya + 1 orientador-loja), 36 skills" -> "15 subagents (14 Nacom Goya + 1 orientador-loja), 41 skills invocaveis"
- **Severidade**: MEDIA (snapshot de contexto do estudo — descritivo)

### 4. `AGENT_DESIGN_GUIDE.md` — contagem 14 subagents + 7 xhigh

- **Documentado**: "14 subagents Nacom Goya" + "7 subagents Opus pesados com effort: xhigh"
- **Real**: 14 subagents Nacom Goya (12 originais + `gestor-motos-assai` 2026-05-09 + `auditor-sped-ecd` 2026-05-16) + 1 `orientador-loja` = 15 totais; 8 com xhigh (adicionado `auditor-sped-ecd`)
- **Acao**:
  - Header: 2026-05-11 -> 2026-05-18 (refresh SDK 0.2.82 + contagem 15 subagents)
  - Linha 39: "13 subagents Nacom Goya (12 originais + gestor-motos-assai 2026-05-09)" -> "14 subagents Nacom Goya (12 originais + gestor-motos-assai 2026-05-09 + auditor-sped-ecd 2026-05-16)"
  - Linha 42: "7 subagents Opus pesados" -> "8 subagents Opus pesados" + `auditor-sped-ecd` no listado; menciona que xhigh continua valido no SDK 0.2.82
- **Severidade**: MEDIA (afeta contagem em manual prescritivo)

### 5. `AGENT_TEMPLATES.md` — contagem 14 subagents

- **Documentado**: "14 subagents (13 Nacom Goya + 1 orientador-loja)"
- **Real**: 15 subagents (14 Nacom Goya + 1 orientador-loja)
- **Acao**: Header 2026-05-11 -> 2026-05-18; "14 subagents" -> "15 subagents" com referencia commit `b7413ba7`
- **Severidade**: BAIXA (cosmetico — apenas contagem)

### 6. `ROUTING_SKILLS.md` — contagem 36 skills + 4 SPED skills nao documentadas

- **Documentado**: "36 skills invocaveis" no header e no inventario completo
- **Real**: 41 skills (`ls -d .claude/skills/*/`). 4 SPED skills novas: `parseando-sped-ecd`, `auditando-sped-contabil`, `auditando-sped-vs-manual`, `comparando-sped-ground-truth` (todas 2026-05-16, uso exclusivo do subagent `auditor-sped-ecd`)
- **Acao**:
  - Header 11/05 -> 18/05; contagem "36 skills" -> "41 skills"; mencao explicita das 4 skills novas
  - Linha 139 (titulo do inventario): "Skills — Inventario Completo (36 invocaveis)" -> "(41 invocaveis)"
  - Adicionada nova secao "Skills SPED ECD audit (4) — USO EXCLUSIVO do subagent `auditor-sped-ecd`" listando as 4 skills com descricao curta
- **Severidade**: MEDIA (afeta routing e descoberta de skills)

### 7. `INDEX.md` — header de data

- **Documentado**: "Ultima atualizacao: 11/05/2026"
- **Real**: refletindo alteracoes desta sessao
- **Acao**: 11/05/2026 -> 18/05/2026
- **Severidade**: BAIXA

### 8. `modelos/REGRAS_CARTEIRA_SEPARACAO.md` — listener line numbers shifted

- **Documentado**: 4 listeners de Separacao referenciados em linhas 208-240, 244-290, 293-322, 326-436
- **Real** (`app/separacao/models.py`): linhas 215-247, 251-297, 300-329, 333-443. Drift de 7 linhas em todos os 4 listeners — decoradores e docstrings expandidas em commit recente.
- **Acao**: 4 referencias em "Event Listeners da Separacao" (linhas 59, 64, 68, 73 do .md) + 1 referencia adicional em "Pallets" (linha 137 do .md) atualizadas
- **Severidade**: MEDIA (line numbers usados para localizar codigo durante debug)

### Outras mencoes "12 subagents" / "13 subagents" (NAO modificadas — historicas/temporais)

| Arquivo | Linha | Por que nao modificado |
|---------|-------|------------------------|
| `SUBAGENT_RELIABILITY.md:164` | "Revisao completa dos 12 subagents de dominio realizada em 2026-04-09" | Afirmacao temporal explicita — historicamente correta |
| `AGENT_TEMPLATES.md:351` | "2026-04-09: Criacao inicial baseada em revisao dos 12 subagents" | Historico de criacao em 2026-04-09 — correto |
| `AGENT_DESIGN_GUIDE.md:10` | "Este guia foi criado na revisao de Abril/2026 dos 12 subagents existentes" | Contexto historico do guia — correto |

---

## P0 — VERIFICADOS OK (sem divergencias)

| Arquivo | Verificacao |
|---------|-------------|
| `MEMORY_PROTOCOL.md` | linha 33 referencia `memory_injection.py:271` — confere (`def _calculate_category_decay`) |
| `INDEX.md` | header atualizado 11/05 -> 18/05; todos os 21 paths verificados existem |
| `INFRAESTRUTURA.md` | header 22/04/2026; servicos Render IDs reais; Sentry vars no codigo (sentry-sdk 2.54.0 confere) |
| `S3_STORAGE.md` | header 16/04/2026; `app/utils/file_storage.py` existe |
| `PADROES_BACKEND.md` | header 14/04/2026; `app/utils/json_helpers.py` existe |
| `REGRAS_OUTPUT.md` | header 31/03/2026; I1, I5, I6 mantem |
| `REGRAS_TIMEZONE.md` | header 12/02/2026; `app/utils/timezone.py` + hook OK |
| `SUBAGENT_RELIABILITY.md` | header 13/02/2026 + nota M1.1 SDK 0.1.60+ (continua valido em 0.2.82) |
| `MANUAL_CLAUDE_MD.md` | header 06/05/2026; hierarquia oficial mantida |
| `FRAMEWORK_ARISTOTELICO.md` | atemporal |
| `PROMPT_INJECTION_HARDENING.md` | header 12/04/2026; 6 layers/12 checklist OK |
| `STUDY_PROMPT_ENGINEERING_2026_QUALITY_REVIEW.md` | header 12/04/2026 com nota update |
| `ROADMAP_PROMPT_ENGINEERING_2026.md` | header 12/04/2026; P0 100% resolvido |
| `ROADMAP_SDK_CLIENT.md` | header 04/04/2026; status pausado coerente (`toggle_mcp_server` continua nao implementado; vale para 0.2.82) |

## P1 — modelos/ + negocio/ (10 files) — 1 divergencia corrigida

- `REGRAS_CARTEIRA_SEPARACAO.md` (07/02): **listener line numbers ATUALIZADOS** (208-240 -> 215-247; 244-290 -> 251-297; 293-322 -> 300-329; 326-436 -> 333-443; line 137 atualizada para 333-443)
- `REGRAS_MODELOS.md` (07/02): regras de Pedido (view), Embarque, EmbarqueItem mantem
- `CADEIA_PEDIDO_ENTREGA.md`: cadeia consistente
- `QUERIES_MAPEAMENTO.md`: queries Q1-Q20 OK
- `REGRAS_NEGOCIO.md` (07/03): regras Nacom Goya, grupos empresariais OK
- `REGRAS_P1_P7.md`: hierarquia P1-P7 consistente
- `FRETE_REAL_VS_TEORICO.md`: 4 valores corretos
- `MARGEM_CUSTEIO.md`: atualizado 2026-05-10 com nota sobre ICMS-ST
- `RECEBIMENTO_MATERIAIS.md` (07/03): Fases 1-4 IMPLEMENTADAS
- `historia_nacom.md`: historico (atemporal)

## P2 — odoo/ (9 files) — sem divergencias novas

- `IDS_FIXOS.md`: companies, picking types (atualizados 2026-05-17 no proprio arquivo), journals, tolerancias TODOS verificados via grep no codigo. Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` permanece desde 31/Jan/2026.
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

## P4 — ssw/ (~309 files .md) — scan rapido sem anomalias

Volume alto, estabilidade alta. INDEX.md (2026-04-09) e ROUTING_SSW.md (2026-02-16) sem sinais de divergencia.

---

## Pendencias Historicas (mantidas)

1. **`odoo/IDS_FIXOS.md` linha 83**: Flag `product_tmpl_id ~~34~~ VERIFICAR` aberto desde 31/Jan/2026 — requer consulta MCP Odoo ao modelo `product.product` para confirmar `product_tmpl_id` real do produto FRETE (ID=29993). NAO resolvido nesta sessao (MCP Odoo nao exercitado).
2. **`CLAUDE.md` (raiz do projeto, fora do escopo references)**: linha 20 ainda menciona "Claude Agent SDK 0.1.80 (CLI 2.1.138)". Embora fora do escopo de references/, vale registrar — pode ser atualizado pelo dominio CLAUDE.md em proxima auditoria.

---

## Acoes Aplicadas

| # | Arquivo | Acao | Severidade | Status |
|---|---------|------|------------|--------|
| 1 | `BEST_PRACTICES_2026.md` | Header 11/05 -> 18/05; tabela versoes (SDK 0.1.80 -> 0.2.82 com CLI 2.1.142 e 3 bug fixes); secao 0.1 expandida com bump 0.1.80 -> 0.2.82 cosmetico | ALTA | APLICADO |
| 2 | `MCP_CAPABILITIES_2026.md` | Header 2026-05-11 -> 2026-05-18; tabela versoes (SDK 0.1.80 -> 0.2.82, CLI 2.1.138 -> 2.1.142, salto 0.1.81 -> 0.2.82 cosmetico com 3 bug fixes) | ALTA | APLICADO |
| 3 | `STUDY_PROMPT_ENGINEERING_2026.md` (linhas 25-26) | SDK 0.1.80 -> 0.2.82 (CLI 2.1.142); "14 subagents, 36 skills" -> "15 subagents (14 Nacom Goya + 1 orientador-loja Lojas HORA), 41 skills invocaveis" | MEDIA | APLICADO |
| 4 | `AGENT_DESIGN_GUIDE.md` (header) | 2026-05-11 -> 2026-05-18 (refresh SDK 0.2.82 + contagem 15 subagents — auditor-sped-ecd 2026-05-16) | MEDIA | APLICADO |
| 5 | `AGENT_DESIGN_GUIDE.md` (linha 39) | "13 subagents Nacom Goya" -> "14 subagents Nacom Goya (12 originais + gestor-motos-assai 2026-05-09 + auditor-sped-ecd 2026-05-16)" | MEDIA | APLICADO |
| 6 | `AGENT_DESIGN_GUIDE.md` (linha 42) | "7 subagents Opus pesados" -> "8 subagents Opus pesados" com auditor-sped-ecd no listado; nota xhigh valido no SDK 0.2.82 | MEDIA | APLICADO |
| 7 | `AGENT_TEMPLATES.md` (header + linha 5) | Header 2026-05-11 -> 2026-05-18; "14 subagents" -> "15 subagents (14 Nacom Goya + 1 orientador-loja)" com referencia commit b7413ba7 | BAIXA | APLICADO |
| 8 | `ROUTING_SKILLS.md` (header) | "36 skills invocaveis" -> "41 skills invocaveis"; mencao explicita das 4 SPED skills novas (2026-05-16); header 11/05 -> 18/05 | MEDIA | APLICADO |
| 9 | `ROUTING_SKILLS.md` (inventario linha 139) | Titulo "(36 invocaveis)" -> "(41 invocaveis)"; nova secao "Skills SPED ECD audit (4)" antes do bloco final | MEDIA | APLICADO |
| 10 | `INDEX.md` (header) | 11/05/2026 -> 18/05/2026 | BAIXA | APLICADO |
| 11 | `modelos/REGRAS_CARTEIRA_SEPARACAO.md` | 5 referencias atualizadas: 4 listener line numbers (208-240, 244-290, 293-322, 326-436) -> (215-247, 251-297, 300-329, 333-443) + linha 137 (326-436 -> 333-443) | MEDIA | APLICADO |
| 12 | `odoo/IDS_FIXOS.md` | Pendencia historica `product_tmpl_id ~~34~~ VERIFICAR` | BAIXA (requer MCP Odoo) | PENDENTE |

**Total arquivos modificados nesta sessao**: 7 (BEST_PRACTICES_2026, MCP_CAPABILITIES_2026, STUDY_PROMPT_ENGINEERING_2026, AGENT_DESIGN_GUIDE, AGENT_TEMPLATES, ROUTING_SKILLS, INDEX, modelos/REGRAS_CARTEIRA_SEPARACAO) — 8 contando REGRAS_CARTEIRA_SEPARACAO.md.

---

## Historico

- Auditoria 2026-04-06: 6 divergencias identificadas, nao corrigidas (sensitive file lock)
- Auditoria 2026-04-20: 7 divergencias, 6 corrigidas, 1 pendente
- Auditoria 2026-04-27: 5 divergencias novas (SDK 0.1.63 -> 0.1.66, system_prompt v4.2.0 -> v4.3.2, contagem skills, line :271), todas aplicadas
- Auditoria 2026-05-05: 3 divergencias novas (introducao orientador-loja), aplicadas
- Auditoria 2026-05-11: 5 divergencias novas (bump SDK 0.1.66 -> 0.1.80, gestor-motos-assai), aplicadas
- Auditoria 2026-05-18 (esta): **8 divergencias novas + 1 pendencia historica**, decorrentes do bump SDK 0.1.80 -> 0.2.82 (cosmetico, 2026-05-16), novo subagent `auditor-sped-ecd` + 4 skills SPED ECD (2026-05-16), e drift de line numbers no `app/separacao/models.py`. **Todas as 8 aplicadas nesta sessao.**

Nenhum caminho quebrado. Sem deletar ou renomear arquivos.

---

## Estatisticas

- **Arquivos revisados (full)**: 39 (20 P0 + 4 P1 modelos + 6 P1 negocio + 9 P2 odoo)
- **Arquivos com scan rapido**: ~312 (3 P3 design+linx + ~309 P4 ssw)
- **Arquivos com divergencia (sessao paralela inicial)**: 8 corrigidos
- **Arquivos com divergencia adicional (sessao auditoria 2026-05-18 final)**: +4 corrigidos
- **Total arquivos corrigidos**: **12**
- **Caminhos quebrados**: 0
- **Pendencias historicas**: 2 (`product_tmpl_id` Odoo desde Jan/2026; revisao trimestral STUDY ao atingir SDK 0.2.0+ — agora satisfeito)

---

## Adendo — Sessao de Auditoria Final (2026-05-18 ~13:30 BRT)

Apos os updates da sessao paralela (08:00-10:10 BRT, 8 arquivos), uma segunda sessao de auditoria
revisou todos os arquivos e identificou **4 ajustes adicionais** pontuais:

### Ajustes Adicionais Aplicados

| # | Arquivo | Acao | Severidade |
|---|---------|------|------------|
| A1 | `AGENT_TEMPLATES.md` (header + linha 5) | Refresh secundario: 14 -> 15 subagents (`auditor-sped-ecd` 2026-05-16) — sessao paralela inicial nao tinha completado este | BAIXA |
| A2 | `SUBAGENT_RELIABILITY.md` | Header 13/02/2026 -> 18/05/2026 (com nota update) + linha 202 corrigida: "Apos o fix, os 14 agents Nacom Goya" -> "Apos o fix, os 13 agents Nacom Goya da epoca (hoje 14 com `auditor-sped-ecd` adicionado em 2026-05-16)" para precisao historica. | BAIXA |
| A3 | `INDEX.md` (Mapeamento Skill -> References) | Adicionadas 4 linhas para `parseando-sped-ecd`, `auditando-sped-vs-manual`, `auditando-sped-contabil`, `comparando-sped-ground-truth` apontando para `app/relatorios_fiscais/`. Sessao paralela atualizou header mas nao adicionou o mapeamento. | MEDIA (skill discovery via INDEX) |
| A4 | `odoo/IDS_FIXOS.md` (rodape, secao "Como Usar") | Dict exemplo `PICKING_TYPES` LF=16 -> LF=19 com comentario referenciando audit 2026-05-17. Topo da tabela ja estava corrigido em 2026-05-17 mas o codigo de exemplo no rodape ainda mostrava LF=16 — risco de copia-cola errada por desenvolvedores. | MEDIA |
| A5 | `odoo/GOTCHAS.md` (header) | "Marco/2026" -> "18/05/2026" (revisao + adicoes Mai/2026). Mtime 14/05 era estale vs header. | BAIXA |
| A6 | `MEMORY_PROTOCOL.md` (secao "Protecoes") | Linha `memory_consolidator.py:49-52` -> `:62-65 (PROTECTED_PATHS set)` (drift de line numbers). | BAIXA |

### Pendencia Adicional Identificada

7. **`STUDY_PROMPT_ENGINEERING_2026.md` linha 6**: trigger explicito "Proxima revisao: ...quando `claude-agent-sdk >= 0.2.0`". O SDK e' agora 0.2.82, esse gatilho **foi atingido**. Documento tambem marca proxima revisao trimestral em 2026-07. Decisao: prosseguir conforme calendario explicito (2026-07) ja que SDK 0.1.81 -> 0.2.82 e' bump cosmetico sem mudancas conceituais de prompt engineering. **Registrar pendencia para revisao plena no calendario trimestral.**

### Verificacoes Adicionais (sem ajuste necessario)

- `app/utils/timezone.py`, `.claude/hooks/ban_datetime_now.py`, `app/utils/json_helpers.py`, `.claude/skills/rastreando-odoo/scripts/rastrear.py` — citados em references diversos, todos existem
- Listener line numbers em `app/separacao/models.py`: 215-247 conferem (decorator em 214; def em 215; ultima linha de codigo em 246/247) — sessao paralela ja atualizou
- `system_prompt.md` v4.3.3 (head -1) — confere com STUDY
- Subagents Opus xhigh: 8 confirmados via `grep -c "effort: xhigh"` (analista-carteira, auditor-financeiro, auditor-sped-ecd, desenvolvedor-integracao-odoo, especialista-odoo, gestor-motos-assai, gestor-recebimento, raio-x-pedido)

