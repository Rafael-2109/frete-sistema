# PROMPT PRÓXIMA SESSÃO — orquestrador-Odoo

**Esta sessão visa**: v25+ migração do orchestrator para usar Skill 8 ATÔMICA L2 v24+ via opt-in `--usar-skill8-atomica-v25`. Rename `faturamento_pipeline.py` → `inventario_pipeline.py`. Canary REAL PROD do opt-in. Expand CONSTANTS FB+CD. Folhas L3 1.1.x + 1.3 (Markdown apenas).
**Base**: commit v24+ a fazer (Skill 8 ATÔMICA L2 5 átomos + C5 G007+l10n_br_tipo_produto + 32 pytest novos = baseline 654 verdes).
**Risco**: MÉDIO (opt-in é dispatch fino + canary primeiro; rename exige cuidado com 8 imports atuais; expand CONSTANTS requer XML-RPC discovery).
**Estimativa**: 2-3 sessões.

> **Criado em**: 2026-05-27 v24+ EXECUTED (sucessor do v23+v23.5+ EXECUTED).
> **Audiência**: Claude Code OU agente web na próxima sessão do orquestrador-Odoo.
> **Predecessores executados**: `_prompts_executados/PROMPT_PROXIMA_SESSAO_v{15a,15b,15c,16,17,17_5,18,19,20,21,22,23,24}_EXECUTED_*.md` + `PROMPT_PROXIMA_SESSAO_SKILL2_EXECUTED_*.md`.

---

## §0. CONVENÇÃO DESTE ARQUIVO (atemporal — NÃO ALTERAR sem refator estrutural)

> **Regra de manutenção** (idêntica em todas as sessões):
>
> 1. **Um único `PROMPT_PROXIMA_SESSAO.md` vive no root de `app/odoo/estoque/`**. Sempre 1, nunca 2+.
> 2. Sessão executada renomeia este arquivo para `_prompts_executados/PROMPT_PROXIMA_SESSAO_v<XX>_EXECUTED_<YYYY_MM_DD>.md` ANTES do commit final.
> 3. Sessão executada CRIA um novo `PROMPT_PROXIMA_SESSAO.md` no root com o escopo da sessão N+1 (preserva §0, §1, §6 atemporais; reescreve §2, §3, §4, §5).
> 4. **NÃO MEXER** em `PROTECAO_PROXIMA_SESSAO.md` (escudo atemporal — separado deste PROMPT).
> 5. Histórico cronológico vai em `VALIDACAO_FINAL_SESSAO.md` (regra D-V18-5 do `CLAUDE.md §14`).
>
> **Estrutura padrão de TODA versão**:
> - §0 — Convenção (atemporal — copiar literal)
> - §1 — Primeiro passo (atemporal — copiar literal)
> - §2 — Contexto atual (sessão N atualiza para N+1)
> - §3 — Escopo desta sessão (sessão N decide para N+1)
> - §4 — Checklist desta sessão (sessão N detalha para N+1)
> - §5 — Riscos e mitigações (sessão N elabora para N+1)
> - §6 — Ao terminar (atemporal — copiar literal)

---

## §1. PRIMEIRO PASSO (OBRIGATÓRIO — NÃO PULAR)

> Antes de fazer QUALQUER COISA na sessão (incluindo responder ao usuário com plano detalhado), seguir esta ordem rigorosamente:

### 1.1 Setup técnico (worktree obrigatória)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_estoque_odoo
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
set -a; . <(grep -E '^(DATABASE_URL|ODOO_)' /home/rafaelnascimento/projetos/frete_sistema/.env); set +a
git log --oneline HEAD..origin/main | head -10   # rebase se main avançou
```

### 1.2 Leitura obrigatória em ordem

1. **⭐ `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md`** INTEIRO (escudo contra desvios reincidentes — N1-N26 + AR1-AR12 + lições memories).
2. **`app/odoo/estoque/CLAUDE.md`** — §1.1 (1 SKILL = 1 OBJETO) + §3.1 (orchestrator C3 não é skill) + §6 (4 tabelas catálogo — Skill 8 ATÔMICA L2 NOVA v24+) + §6.5 (antipadrões — AP6 RESOLVIDO PARCIAL v24+) + §14 (histórico desvios — D-V24-1 novo) + §15 (9 princípios canônicos).
3. **`app/odoo/estoque/ROADMAP_SKILLS.md`** — HANDOFF enxuto (≤80 linhas): estado global + próximo passo + pendências + onde NÃO mexer.
4. **Este `PROMPT_PROXIMA_SESSAO.md`** — INTEIRO (§2 contexto + §3 escopo + §4 checklist + §5 riscos).
5. **`app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`** §0 — se sessão tocar Skill 8 / orchestrator (regra inviolável 0).
6. **`.claude/agents/gestor-estoque-odoo.md`** — antipadrões A1-A11 + invariantes 1-10 + árvore + fronteiras.
7. **`app/odoo/constants/operacoes_fiscais.py`** header (60 linhas iniciais) — MATRIZ_INTERCOMPANY + regra CFOP por tipo de produto.
8. **`app/odoo/constants/picking_types.py`** header (15 linhas iniciais) — PICKING_TYPE_POR_DIRECAO + LOCATION_DESTINO_POR_DIRECAO.
9. **`app/odoo/estoque/scripts/faturamento.py`** (NOVA v24+) — 5 átomos Skill 8 ATÔMICA L2 (espelha Skill 7 ABRANGENTE v19+).
10. **`.claude/skills/faturando-odoo/SKILL.md`** — fachada atualizada v24+ (5 átomos + contratos + exemplo composição).

### 1.3 Confirmar baseline pytest

```bash
timeout 90 python -m pytest tests/odoo/ --tb=line -q 2>&1 | tail -3
# Esperado: 654 passed (v24+ baseline)
```

Se ≠ 654 → investigar regressão antes de prosseguir.

### 1.4 Validar entendimento com Rafael (opcional mas recomendado)

Antes de codar: spawn AskUserQuestion confirmando escopo §3 + decisões abertas em §5. Aprovação explícita Rafael.

---

## §2. CONTEXTO ATUAL (atualizado por sessão v24+ — FINALIZADA — Skill 8 ATÔMICA L2 LIVE + C5 G007+tipo_produto + AP6 RESOLVIDO PARCIAL)

### Estado do código
- **Commit base**: v24+ EXECUTED (Skill 8 ATÔMICA L2 com 5 átomos + C5 G007+l10n_br_tipo_produto + 32 pytest novos).
- **Baseline pytest**: 654 verdes (622 baseline + 28 net Skill 8 ATÔMICA + 4 net C5).
- **Worktree**: `feat/estoque-odoo` (main pode ter avançado — rebase em §1.1).

### Estado da arquitetura
- **Skill 8 ATÔMICA L2 LIVE v24+** — `app/odoo/estoque/scripts/faturamento.py` (~750 LOC) com `FaturamentoInvoiceService` + 5 átomos espelhando Skill 7 ABRANGENTE v19+:
  1. `validar_invoice_constants(invoice_id, constants_esperadas, dry_run)` — pre-cond fiscal READ-only
  2. `liberar_faturamento(picking_id, ajuste_ids, dry_run, confirmar)` — DELEGA Skill 5 LEGACY (action_liberar_faturamento)
  3. `polling_invoice(picking_id, ajuste_ids, timeout_s, poll_interval_s, dry_run)` — DELEGA Skill 5 LEGACY (aguardar_invoice_do_robo)
  4. `validar_invoice_pos_robo(invoice_id, ajuste_id_primeiro, perfil, dry_run, confirmar)` — aplica G029+G007+G034 via `_invoice_helpers` (perfil V1 'inventario-inter-company')
  5. `transmitir_sefaz(invoice_id, ajuste_ids, max_tentativas, intervalo_retry, dry_run, confirmar_sefaz)` — Playwright IRREVERSIVEL + D7 HARD_FAIL + D8.3 idempotência + CRITICAL-1 commit pós-SEFAZ + MED C-1/C-2 cstat
- **Orchestrator C3 LEGACY `faturamento_pipeline.py`** — pipeline A-F + recovery + opt-in `--usar-fluxo-l3-v19` AINDA com lógica inline em ETAPAS C+D (~500 LOC). Migração para usar a Skill 8 ATÔMICA via opt-in `--usar-skill8-atomica-v25` planejada NESTA sessão v25+.
- **Sub-skill C5 estendida v24+** — `cadastro_fiscal_audit.py:_check_ncm_weight_tracking` ganhou 2 checks: G007 standard_price=0 (WARN) + l10n_br_tipo_produto ausente (BLOQUEIO).

### Estado FINAL ajustes 176013/176014 PROD (v23+ — preservado v24+)
- id=176013/176014: `status='EXECUTADO', fase_pipeline='F5f_ENTRADA_OK'`
- Picking SAÍDA 321601 (FB/SAI/IND/01602): state=done
- Invoice SAÍDA 716448 RPI/2026/00238: SEFAZ autorizada chave `35260561724241000178550010000945661007164482`
- Invoice ENTRADA 717630 ENTIN/2026/05/0055: posted LF, R$ 12.525,54 untaxed
- PO 42419 C2619591: state=purchase, team=143 RAFAEL, picking 321617 done, invoice 717630
- DFe 43533: criado v22+, lines company=LF (após fix manual v23+)

### Skills LIVE (catálogo §6 do CLAUDE.md estoque)
- Skills L2 atômicas (8): 1, 2 (4 modos A/B/C/D v21+), 2.4, 4, 5 (7 átomos + G-AUDIT-3 v22+), **7 ABRANGENTE v20+ + G039 v23+ + B-V23-1/2 v23.5+ (9 átomos)**, **8 ATÔMICA v24+ (5 átomos NOVA)**, 9 (READ).
- Orchestrators C3 (2): Skill 6 executor, `faturamento_pipeline` (pipeline A-F + recovery + opt-in v19+ — rename para `inventario_pipeline` pendente v25+).
- Sub-skill PRE-FLIGHT: `auditando-cadastro-fiscal-odoo` (V1 'inventario' v14b + G038 v22+ + G007+tipo_produto v24+).
- Fluxos L3 escritos (11): 2.1, 2.2, 2.2.j, 2.4, 2.5, 2.6, 2.9, 3.1, 4.1, 1.2.1 v19+, 1.2.2 v19+.

---

## §3. ESCOPO DESTA SESSÃO (v25+ — opt-in + canary + rename + expand CONSTANTS + folhas L3)

> **CONFIRMAR ESCOPO COM RAFAEL via AskUserQuestion ANTES de codar** (§1.4).

### Objetivo macro
Migrar orchestrator legacy para usar Skill 8 ATÔMICA L2 (criada v24+) via opt-in `--usar-skill8-atomica-v25` + canary REAL PROD validando paridade. Renomear orchestrator. Expand CONSTANTS FB+CD. Escrever folhas L3 1.1.x + 1.3 (Markdown).

### Sub-objetivos (ordem proposta — confirmar com Rafael)

#### S0 — Fixes pipeline INDUSTRIALIZACAO_FB_LF (PRIORITÁRIO v25+, 5 falhas descobertas v24+ cirurgia AVULSO_FRASCO)

**LEITURA OBRIGATÓRIA antes de tocar código S0**: `app/odoo/estoque/CIRURGIA_AVULSO_FRASCO_2026_05_27.md` (análise root cause completa + 8 fixes priorizados P0→P3 + 4 gotchas novos + pattern cirúrgico).

Resumo bugs reais (P0-A e P0-B mais críticos — afetam CADA inter-company silenciosamente):
- **P0-A**: `_executar_etapa_f_via_fluxo_l3` (`faturamento_pipeline.py:3322-3356`) não passa `lotes_data` → default `'MIGRAÇÃO'` aplicado a TODOS MLs. Fix: construir `lotes_data` dos `AjusteEstoqueInventario` + passar.
- **P0-B**: Trocar `lote_default='MIGRAÇÃO'` por `None` + raise (`escrituracao.py:2800` + `picking.py:preencher_lotes_picking`). Falha rápida vs saldo errado silencioso.
- **P0-C**: Tornar L3 v19+ default para todas inter-company (remover opt-in `--usar-fluxo-l3-v19`). Deprecar v17 STRICT.
- **P1-D**: Confirmar `escriturar_dfe` força `tipo='serv-industrializacao'` antes de `gerar_po_from_dfe` (provável já OK; testar).
- **P1-E**: Validar ordem `preencher_po` → `confirmar_po` (provável já OK).
- **P2-F**: Guard `EXECUTADO_PARCIAL` em pipeline_bulk quando ETAPA F skipped.
- **P3-G**: Codificar G-PO-DFE-LOCK (limpar `purchase_fiscal_id` antes reprocessar).
- **P3-H**: Codificar G-DFE-LINE-COMPANY (write `dfe.line.company_id`) — parcialmente já em B-V23-1 v23.5+.

Hipóteses descartadas: G039 NÃO foi causa do original; G-PERM-1 só surgiu na cirurgia.

#### S1 — Opt-in `--usar-skill8-atomica-v25` no orchestrator
- Adicionar flag CLI no `executar_pipeline_bulk` (pattern espelhado de `--usar-fluxo-l3-v19`).
- Quando flag=True, ETAPAS C+D delegam à Skill 8 ATÔMICA (via novo método `_executar_etapas_c_d_via_atomos`).
- Default OFF preserva 100% legacy = zero risco regressão.
- Pytest cobrindo dispatch (3-5 testes mockados).

#### S2 — Canary REAL PROD do opt-in
- Selecionar 1-5 ajustes para canary (mesmo critério v23+: ciclo INVENTARIO_2026_05 ou FATURAMENTO_LF se disponível).
- Rodar `executar_pipeline_bulk --usar-skill8-atomica-v25 --confirmar-sefaz`.
- Validar: paridade com legacy (mesmas chaves SEFAZ, mesmas fase_pipeline finais).

#### S3 — Rename orchestrator + alias compat
- `git mv app/odoo/estoque/orchestrators/faturamento_pipeline.py app/odoo/estoque/orchestrators/inventario_pipeline.py`
- Criar `faturamento_pipeline.py` STUB que re-importa de `inventario_pipeline` (alias compat para 8 imports atuais).
- Atualizar SKILL.md fachada + CLAUDE.md §6 Tabela 2.

#### S4 — Expand CONSTANTS FB+CD
- Discovery XML-RPC `team_id` + `payment_term_id` + `picking_type_id` + `payment_provider_id` para company=1 (FB) e company=4 (CD).
- Mapear `L10N_BR_TIPO_PEDIDO_POR_ACAO` para todas direções via lookup MATRIZ_INTERCOMPANY.
- Pytest mockado cobrindo 3 direções.

#### S5 — Folhas L3 1.1.x + 1.3
- 1.1.x (só saída) compõe Skill 8 ATÔMICA L2.
- 1.3 (transferência completa) compõe Skill 8 ATÔMICA + Skill 7 ABRANGENTE via 1.2.x.
- Markdown apenas (sem código novo).

#### S6 — Após canary OK (se sobrar tempo)
- Remover ETAPAS C+D legacy do orchestrator (~500 LOC).
- Migrar 14 testes C+D de `test_faturamento_pipeline_orchestrator.py` para `test_faturamento_invoice_service.py`.
- Default flip: `--usar-skill8-atomica-v25=True` (e remover flag em vN+).

### O que NÃO entra nesta sessão (escopo declarado fora)
- ❌ Refatorar `RecebimentoLfOdooService` ou `LancamentoOdooService` (NÃO MEXER).
- ❌ Mexer em `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (SUPERADO ao final v22+).

---

## §4. CHECKLIST DESTA SESSÃO

Antes de codar:
- [ ] Setup técnico §1.1 OK (worktree + venv + env + git status limpo)
- [ ] Leitura §1.2 completa (10 documentos incluindo Skill 8 ATÔMICA v24+)
- [ ] Baseline pytest 654 confirmado
- [ ] Cross-check Odoo: estado dos ajustes 176013/14, PO 42419, invoice 717630 (estado preservado v23+)
- [ ] AskUserQuestion §1.4 confirmou escopo S1-S6 com Rafael

Implementação:
- [ ] S1 — Opt-in `--usar-skill8-atomica-v25` + helper `_executar_etapas_c_d_via_atomos` + 3-5 pytest dispatch
- [ ] S2 — Canary REAL PROD 1-5 ajustes (paridade com legacy)
- [ ] S3 — Rename + alias compat (8 imports atuais preservados)
- [ ] S4 — Expand CONSTANTS FB+CD via discovery XML-RPC + pytest
- [ ] S5 — Folhas L3 1.1.x + 1.3 (Markdown)
- [ ] S6 — Se canary OK: remover ETAPAs C+D legacy + migrar 14 testes

Validação:
- [ ] Pytest baseline ≥ 654 + novos testes (estimativa 5-10 novos)
- [ ] ≥1 code-reviewer paralelo (S1 dispatch + S2 canary)
- [ ] Atualizações cross-refs: SKILL.md fachada + ROADMAP HANDOFF + PROTECAO

Documentação:
- [ ] Atualizar PROTECAO (sem novos antipadrões esperados — checklist)
- [ ] Atualizar CLAUDE.md §6.5 (AP6 → RESOLVIDO se S6 entregue) + §14 (D-V25-X se novo desvio)
- [ ] Memórias `[[skill8-atomica-pattern]]` salva via `mcp__memory__save_memory`
- [ ] Append em VALIDACAO_FINAL_SESSAO.md (regra D-V18-5)

---

## §5. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Opt-in dispatch tem comportamento divergente vs legacy (chave SEFAZ diferente, fase_pipeline diferente) | ALTA | ALTO | Canary 1 ajuste primeiro + diff manual logs legacy vs opt-in; só escalar se 100% paridade. |
| Rename quebra imports externos (8 atuais) | MÉDIA | MÉDIO | Grep `faturamento_pipeline` ANTES; criar alias compat `faturamento_pipeline.py` stub que re-exporta de `inventario_pipeline`. Pytest CI valida imports OK. |
| Discovery XML-RPC FB/CD não encontra IDs corretos (cadastro fiscal não pronto) | MÉDIA | MÉDIO | Documentar pendência por company; adiar entries não disponíveis para sessão v26+; canary só company com discovery completo. |
| Refator orchestrator quebra testes existentes ETAPAs C+D (14 testes) | ALTA | MÉDIO | Migrar testes em vez de deletar; validar baseline incrementalmente; usar opt-in para preservar legacy path em paralelo até S6. |
| Sessão estoura tokens com S1+S2+S3+S4+S5 | ALTA | ALTO | Spawn subagente `gestor-estoque-odoo` para S2 canary; principal só S1+S3+S4+S5 (puro código + markdown). |

---

## §6. AO TERMINAR ESTA SESSÃO (atemporal — copiar literal nas próximas)

> **OBRIGATÓRIO** antes do commit final:

### 6.1 Documentação
1. Append bloco "Sessão YYYY-MM-DD vXX" em `VALIDACAO_FINAL_SESSAO.md` (NÃO no ROADMAP HANDOFF — regra D-V18-5).
2. Atualizar `ROADMAP_SKILLS.md` HANDOFF (≤80 linhas) — estado global + próximo passo refinado.
3. Atualizar `CLAUDE.md` estoque (catálogo §6 se skill mudou status; §6.5 se antipadrão resolvido; §14 se novo desvio detectado).
4. Se detectou NOVO antipadrão reincidente → atualizar `PROTECAO_PROXIMA_SESSAO.md` (ARN + Nij + Lições).
5. Se padrão emergiu → salvar memória `[[<slug>-pattern]]` via `mcp__memory__save_memory`.

### 6.2 Sanitizar prompts (regra desta convenção — D-V18-PROMPTS)
1. Renomear este `PROMPT_PROXIMA_SESSAO.md` para `_prompts_executados/PROMPT_PROXIMA_SESSAO_v<XX>_EXECUTED_<YYYY_MM_DD>.md`.
2. Criar **novo** `PROMPT_PROXIMA_SESSAO.md` no root de `app/odoo/estoque/` com escopo da sessão N+1:
   - §0 + §1 + §6 — copiar literal deste arquivo (atemporais).
   - §2 — atualizar com commit novo + estado pós-sessão.
   - §3 — definir escopo da próxima sessão (sub-objetivos).
   - §4 — checklist concreto.
   - §5 — riscos + mitigações específicos.

### 6.3 Commit consolidado
```bash
git add <arquivos modificados>
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
export PATH="/home/rafaelnascimento/projetos/frete_sistema/.venv/bin:$PATH"
git commit -m "<tipo>(estoque): <sumário> — v<XX> (YYYY-MM-DD)
<corpo do commit detalhado>
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### 6.4 Validação final
- [ ] Pytest verde ≥ baseline atual
- [ ] `git status` limpo
- [ ] `PROMPT_PROXIMA_SESSAO.md` novo criado (1 só vivo no root)
- [ ] Histórico em `VALIDACAO_FINAL_SESSAO.md`
- [ ] `PROTECAO_PROXIMA_SESSAO.md` atualizado se houve novo antipadrão

---

> **TEMPLATE END**. Para próxima sessão (após executar esta), substituir §2-§5 mantendo §0, §1, §6 literais.
