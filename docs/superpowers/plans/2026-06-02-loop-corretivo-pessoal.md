<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao do loop corretivo pessoal (memoria que adere entre sessoes)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# Loop Corretivo Pessoal — a lição que adere entre sessões — Implementation Plan

> **Papel:** plano executável (TDD, flag-OFF) do loop corretivo pessoal — frente F1 do eixo G.
>
> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (ou superpowers:executing-plans) para implementar task-by-task. Steps usam checkbox (`- [ ]`). Tudo flag-OFF + shadow-first.
> Eixo: `eixos/G-memoria-pessoal.md` (frente F1). Reconciliação: `RECONCILIACAO_MEMORIA.md`. Rastreador: `EXECUCAO.md`.

**Goal:** Fechar o loop de aprendizado corretivo PESSOAL — fazer a correção do usuário ADERIR na sessão seguinte — sem inchar o contexto. Hoje o agente grava a correção mas ela nunca volta ao contexto no fluxo rotineiro (`semantic=0` / `tier2_chars=0` em PROD, Marcus), nunca é promovida a regra dura, e a reincidência gera nova cópia em vez de reforço. Alvo: reincidência do mesmo erro do Marcus cai de ~9 ocorrências para ≤2.

**Architecture:** Reaproveita infraestrutura JÁ construída e desligada: o canal duro `_build_user_rules` (`memory_injection_rules.py`, injeta `priority='mandatory'` fora do budget) e o motor `directive_promotion_service` (gate anti-gaming R9 `_tem_falha_odoo` + eval_gate A3). NÃO é "criar Tier 0" — é **ligar + rotear correções para o que existe** + fechar o write-path (UPDATE-vs-ADD) + medir por outcome. Espelha o pattern da A4 (que faz o mesmo para diretrizes EMPRESA).

**Tech Stack:** Python 3.12 · Flask-SQLAlchemy 2.0 · APScheduler (D8) · pgvector/Voyage (dedup) · pytest. Sonnet (extração pós-sessão já existe) + Haiku (judge, se F8 ligado). Sem fila RQ nova.

---

## CONTEXTO ANTI-DRIFT (ler antes de codar)

- **Elo letal = INJEÇÃO, não só budget.** Em Sonnet o `user.xml` zera o Tier 2 (`memory_injection.py:1077-1078,1183`); MAS em Opus (budget ilimitado) o problema persiste: `semantic=0` no prompt rotineiro + fallback prioriza empresa por recência → correção pessoal nunca é candidata. A cura robusta é o **canal garantido** (independe de similaridade e budget), não só ligar o pointer.
- **Bugs centrais do write-path:** (1) `pattern_analyzer.py:1987` faz `return False` descartando a reincidência sem contar; (2) o branch `tipo=='correcao'` **não chama** `_track_correction_feedback` (só o path MCP empresa chama). Esses dois são o coração.
- **Promoção existe mas é código morto:** `_is_mandatory_trigger` (`pattern_analyzer.py:51-67`) não tem callsite. `directive_promotion_service` só promove `user_id=0` (empresa).
- **Métrica cega:** `effective_count` = eco textual memória↔resposta (`_helpers.py:497-511`), não "preveniu o erro". `correction_count` é dead code (0 em 197/197, fora do composite score `memory_injection.py:945`).
- **Flags (estado PROD confirmado em logs):** `USE_USER_RULES_CHANNEL`=OFF; `USE_USER_XML_POINTER`=OFF; `USE_OPERATIONAL_DIRECTIVES`=ON (só empresa). Em PROD só 1/503 memórias é `priority='mandatory'`.
- **Cap anti-omissão (IFScale arXiv:2507.11538):** adesão despenca >100-150 instruções; `MANDATORY_RULES_MAX_COUNT≈12` ordenado por `correction_count desc`.
- **Gate anti-gaming (arXiv:2310.01798 / CRITIC):** self-correction sem feedback externo confiável piora; reusar R9 `_tem_falha_odoo` (DOMINA) + eval_gate A3.
- **Gotcha worktree:** `export DATABASE_URL` da raiz (localhost) antes de pytest (senão cai em SQLite).
- **Canal compartilhado Web+Teams:** `_build_user_rules`/`memory_injection` afetam os dois — testar no Teams antes de ligar a flag (CLAUDE.md "Export crítico Teams").
- **Pré-requisito de sequência:** medição (Onda 1 / eixo E) antes de ligar atuador; gate de escrita empresa (Onda 0 / eixo F) antes do canal de diretrizes. A Fase 0 abaixo é medição offline (risco zero) e pode rodar já.

---

## Fase 0 — Diagnóstico offline (sem tocar PROD) — APROVADA pelo Rafael

Escada AgingBench P1/P2/P3 (arXiv:2605.26302) sobre as ~9 correções repetidas do Marcus:
- [ ] Script offline reusa as correções existentes do user 18 em 3 condições: P1=memória atual / P2=correção injetada por oracle no topo / P3=regra dura imperativa no topo.
- [ ] Medir acerto por condição. **Se P3 acerta e P1 erra → falha é retrieval/injection** (confirma o diagnóstico → investir no canal duro, Fases 1-2). **Se até P3 erra → correção mal-escrita** (investir em reescrita imperativa, Fase 3 etapa 5).
- [ ] Sem novos arquivos de produção; saída = relatório `/tmp/subagent-findings/aging-marcus.md`.
- **DoD:** decisão registrada no `EXECUCAO.md` (retrieval vs utilization) antes de mexer em flags.

## Fase 1 — QUICK WIN: ligar canal + promover passivo (esforço baixo)

- [ ] `config/feature_flags.py`: `AGENT_USER_RULES_CHANNEL` (canary); novas `AGENT_CORRECTION_PROMOTION` (def. false), `AGENT_CORRECTION_PROMOTION_THRESHOLD` (def. 2), `MANDATORY_RULES_MAX_COUNT` (def. 12). **Migration N/A** (sem schema).
- [ ] `memory_injection_rules.py:34` (`_build_user_rules`): `order_by(correction_count.desc())` + `.limit(MANDATORY_RULES_MAX_COUNT)` — cap IFScale. **Teste TDD:** com 20 regras mandatory, injeta só as 12 de maior `correction_count`.
- [ ] Backfill one-shot (script): fundir as ~9 correções de escopo do Marcus em 1 canônica `priority='mandatory'` (preservando a prescrição). Idempotente, dry-run-first.
- **DoD:** canal pessoal injeta no fluxo rotineiro (log `[MEMORY_INJECT_RULES]` aparece p/ user 18); teste de integração (regra mandatory atravessa para o prompt); flag OFF default; validado em Teams.

## Fase 2 — WRITE-PATH: UPDATE-vs-ADD na reincidência (esforço médio) — coração

- [ ] `pattern_analyzer.py:~1980-1987` (branch `tipo=='correcao'`): substituir `if dup_path: return False` por reconciliação — buscar canônica (banda cosine 0.6-0.9); se existe → UPDATE (`correction_count+=1`, `importance=min(0.95, 0.7+0.05·cc)`, `last_accessed_at=now`, merge via `_merge_memories_via_sonnet`); só ADD se não há canônica. **E chamar `_track_correction_feedback`** (hoje ausente neste branch). **Teste TDD RED→GREEN:** 2ª correção do mesmo tema vira UPDATE (cc=2), não novo arquivo.
- [ ] `memory_mcp_tool.py` (`_check_memory_duplicate`): variante que retorna `(path, similarity)` para decidir UPDATE (0.6-0.9) vs NOOP (>0.85). Mem0 arXiv:2504.19413.
- [ ] `directive_promotion_service.py` (`run_directive_promotion_batch`): 3ª fonte CORRECTION-RECURRENCE (`correction_count>=THRESHOLD`) passando pelo MESMO gate R9+A3 → `priority='mandatory'`. **Teste:** correção com cc=2 + sem falha Odoo é promovida; com falha Odoo é bloqueada.
- [ ] `routes/_helpers.py` (S1 pós-extração): chamar `promote_recurrent_corrections` em daemon thread/RQ (zero custo no response path).
- [ ] `config/feature_flags.py`: `AGENT_CORRECTION_RECONCILER` (def. OFF p/ canary).
- **DoD:** nº de arquivos em `/memories/corrections/` por usuário **para de crescer linearmente**; pytest baseline mantido; shadow antes de ligar.

## Fase 3 — FEEDBACK FECHADO: outcome + enquadramento + enforcement (médio-alto)

- [ ] Migration dupla (`scripts/migrations/NOME.{py,sql}`, SQL idempotente): coluna `error_signature` (VARCHAR indexável) em `agent_memories`.
- [ ] `pattern_analyzer.py` (prompt de extração): Sonnet emite `error_signature` (intenção normalizada, não texto) + reescreve a prescrição em SEMPRE/NUNCA + WHEN/DO na promoção (frame imperativo — Compiled Memory arXiv:2603.15666).
- [ ] `routes/_helpers.py` (`_track_memory_effectiveness`): manter para dashboard, DESACOPLAR do sinal de promoção. Nova medição por OUTCOME: regra injetada + reincidência (`error_signature` casou) → `harmful++`; injetada + sem reincidência por K sessões → `helpful++` (ACE arXiv:2510.04618). Reusa `injected_memory_ids`.
- [ ] `memory_injection.py:945`: somar eixo recorrência ao composite score (`0.3 decay+0.3 imp+0.4 sim` ignora recorrência).
- [ ] `sdk/hooks.py` (base R9 PreToolUse): HARD enforcement (HAC, Meta-Policy Reflexion arXiv:2509.03990) só p/ invariantes formalizáveis promovidas (nome de campo, op destrutiva).
- [ ] `directive_promotion_service.py`: `demote_stale_rules` (harmful pós-promoção por N → reescrita; K sessões limpas → mantém/demote para liberar o canal duro).
- [ ] `insights_service.py`: painel "adesão de regras" (reincidência por assinatura antes/depois da promoção).
- **DoD:** **métrica primária** — taxa de reincidência por `error_signature` ANTES vs DEPOIS da promoção estagna (compounding_detection deixa de ser não-decrescente). Alvo: Marcus ~9 → ≤2.

---

## Rollback global (sem redeploy)
`AGENT_CORRECTION_PROMOTION=false` + `AGENT_USER_RULES_CHANNEL=false` + `AGENT_CORRECTION_RECONCILER=false` + `AGENT_CORRECTION_OUTCOME_METRIC=false`.

## Riscos (ver `eixos/G` §riscos e `RECONCILIACAO_MEMORIA.md`)
Inchar o canal duro → omissão (cap+demote); promover ruído (gate R9+A3); judge não calibrado (calibração humana como gate); budget starvation (pointer+reserva junto); falso-merge no dedup (banda conservadora + "na dúvida ADD"); regressão Web/Teams (testar Teams; flag-OFF/shadow).
