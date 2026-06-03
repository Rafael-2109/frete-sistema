# EXECUÇÃO — Evolução do Agente (rastreador vivo)

> **Este é o ÍNDICE DE VERDADE do projeto.** Sobrevive entre sessões. NENHUMA onda começa
> sem consultar os gates aqui; NENHUM item é "done" sem marcar o checklist aqui.
> Spec de design: `BLUEPRINT_MESTRE.md` (+ `eixos/*.md` detalhe, `critica/*.md` revisão).
> Planos executáveis por onda: `docs/superpowers/plans/` (formato writing-plans, TDD).
> Branch do projeto: `feat/agente-evolucao` (worktree isolada). Cadência: **subagent-driven**.

---

## COMO USAR (protocolo inviolável)

1. **Ordem por DEPENDÊNCIA, não por esforço.** Os gates abaixo são duros. Não inicie a onda N+1
   sem o GATE da onda N verde (verificado em PROD/shadow, não só pytest local).
2. **1 item = 1 PR pequeno atrás de flag OFF.** Cada item tem um plano writing-plans próprio
   (gerado just-in-time quando a onda chega) executado subagent-driven (1 subagente/tarefa + review).
3. **Definition of Done (DoD) GLOBAL** — um item só vira ✅ quando TODOS batem (ver checklist abaixo).
4. **Atualizar este arquivo a cada item** (status + data + nº do PR/commit). É o que garante "não pular/esquecer".
5. **Flag OFF default** em tudo. Comportamento novo valida em SHADOW antes de virar gate/ativo.

### Definition of Done (DoD) — checklist por item
- [ ] Teste TDD verde (failing test escrito ANTES da implementação)
- [ ] **Wiring contract verificado por teste de INTEGRAÇÃO** (o sinal atravessa produtor→consumidor, não só unit)
- [ ] Migration dupla se houver schema: `scripts/migrations/NOME.{py,sql}` (SQL idempotente `IF NOT EXISTS`)
- [ ] Invariantes da área intactas (ver checklist de regressão abaixo)
- [ ] pytest baseline mantido ou aumentado (não baixa o nº de verdes)
- [ ] Flag OFF por default em `config/feature_flags.py`
- [ ] code-review aprovado (`/code-review` ou workflow adversarial nos itens críticos)
- [ ] Se comportamental (muda resposta/ação): validado em SHADOW antes de ligar a flag
- [ ] Status atualizado neste arquivo

### Checklist de REGRESSÃO — invariantes a NUNCA quebrar (Blueprint §5)
Verificar em TODO PR que toca a área correspondente:
- **INV-1 (R10)**: escrita de turno/passo/resposta no fim da thread PRIMARY, NUNCA no `_stop_hook` (corrida).
- **INV-2 (identidade)**: chave = nosso UUID + `AgentSessionCost.message_id` (UNIQUE `models.py:1413`), NUNCA o SDK session_id efêmero.
- **INV-3 (canais)**: separação Web/Teams — aprovação de plano e feedback explícito nascem Web-only; Teams (Adaptive Card R4) tem caminho próprio.
- **INV-4 (constituição estoque)**: "1 skill = 1 objeto", `--dry-run` first, fluxos>>skills (`estoque/CLAUDE.md`). Verifier `domain` (B) e registry (F) GENERALIZAM, não violam.
- **INV-5 (guards de domínio)**: G021/G031/G-MO-01, direção-MIGRAÇÃO por `diff_qtd`, CICLAMATO, GTIN/SEFAZ G035 são a verdade logística que o verifier `domain` checa.
- **INV-6 (best-effort + thread-safety)**: services em RQ/APScheduler, NUNCA no path SSE; ContextVar por thread; except não-propagado.
- **INV-7 (caching Camada 1)**: `<operational_directives>` e `<world_model>` injetados via hook (dinâmico), fora do system_prompt estático cacheável.

### Riscos transversais (mitigação obrigatória nos itens marcados)
- **Reward-hacking** (Ondas 1,3): judge produz LAUDO causal justificado; componente ambiental não-gameável (audit Odoo R9) DOMINA a decisão de promoção; held-out + spot-check humano 5-10%.
- **`effective_count` semântica** (Onda 1): coluna NOVA `outcome_effective_count`, NUNCA redefinir in-place (3 consumidores acoplados).
- **Recursão de subagente solta** (Onda 2): verificar propagação de `Task` no SDK 0.2.87 ANTES de B4 (instrução contraditória `gestor-estoque-odoo.md:73`).
- **Gate travando atuador autônomo** (Onda 3): eval do D8 = processo EXTERNO + report-only→enforce.

---

## GRAFO DE DEPENDÊNCIAS (resumo — ver Blueprint §2)

```
S0 (entidade passo + registry descritivo)  ──┬─► E (qualidade) ◄──► D (ontologia)   [E↔D ciclo]
   FUNDAÇÃO FÍSICA                            │        │                │
                                              │        ▼                ▼
                              F (registry) ───┴─► A (flywheel) ◄─── B (planejador)
                                  sustenta           │ consome sinal E   │ consome mundo D
                                  e É o espaço        └── promove plano ──┘ produz sinal p/ E
                                  de estados de B
```
Fundações: (i) **S0 schema de passo** (física) · (ii) **par E↔D** (semântica) · (iii) **F registry** (estrutural).

---

## ESTADO DE ATIVAÇÃO (2026-05-31) — FUNCIONAL vs WIRING PENDENTE

> Os 22 itens estão **code-complete + testados + flag-OFF**. Mas "funcional" (roda no loop vivo)
> ≠ "code-complete". Por design GATED (shadow→wire→ativa), parte tem o MECANISMO pronto mas
> SEM caller no loop vivo ainda. Esta tabela é a VERDADE para a fase de wiring.

### ✅ Funcional ao ligar a flag (caller ativo — ativados em PROD 2026-05-31)
| Feature | Flag | Caller ativo |
|---------|------|--------------|
| S0a `agent_step` | — (schema) | `chat.py::_save_messages_to_db` + `teams::_gravar_agent_step_teams` (todo turno) |
| E1 quality spine | `AGENT_QUALITY_SPINE` | `chat.py`/`teams` (frustração) + `feedback.py` (👍👎) |
| D2 bootstrap | `AGENT_ONTOLOGY` | `build.sh 26c` / `scripts/agente/bootstrap_ontologia.py` |
| D4 `query_ontology` | `AGENT_ONTOLOGY` | tool MCP exposta ao agente (`client.py` registro) |
| D3 proveniência | `AGENT_ONTOLOGY` | `memory_mcp_tool` (save de memória) |
| B1 PlanState | `AGENT_PLANNER` | `chat.py` captura Task* events do stream |
| F4/F5 skill-hints | `AGENT_SKILL_RAG` | hook `_user_prompt_submit_hook` |
| D5 world_model | `AGENT_WORLD_MODEL_INJECT` | hook `_user_prompt_submit_hook` |

### 🟡 Shadow scaffolding — lógica+testes prontos, SEM caller no loop (precisa WIRING)
| Feature | O que JÁ existe | O que FALTA wirar (a fase de ativação) |
|---------|----------------|-----------------------------------------|
| **E2** step_judge | `workers/step_judge.py` (`judge_step` job RQ + `_judge_core` + **`enqueue_pending_judges`**) | ✅ **WIRADO CODE-COMPLETE** (`918d7e7af`, flag-OFF) — **módulo 29** D8 (`sincronizacao_incremental_definitiva.py`, por-ciclo 30min, report-only) chama `enqueue_pending_judges` (janela `created_at` 6h + cap 50, filtro Python `'judge' not in outcome_signal`, best-effort). Fila RQ nova `agent_judge` (LEVE, prioridade mínima) nos 3 arquivos. Reusa flag `AGENT_STEP_JUDGE`; âncora `AGENT_ODOO_AUDIT_HOOK` é ideal (judge degrada sem ela). **Pendente: deploy+shadow (GATE-2).** |
| **B2** verifiers | `sdk/verifiers.py` + `workers/plan_verifier.py` (`verify_step_shadow` + `enqueue_pending_verifies`) | ✅ **WIRADO CODE-COMPLETE** (`15b681a8e`, flag-OFF) — job RQ `verify_step_shadow` roda os 3 verifiers (adversarial+arithmetic+domain) e grava combinado em `outcome_signal['verify']`; **módulo 30** D8 (`enqueue_pending_verifies`, por-ciclo, report-only) varre steps sem verify → enfileira (fila `agent_judge`, gate `AGENT_VERIFY`). **Pendente: deploy+shadow (GATE-2).** Nota: domain verify lê `data['plan']['steps']` (B1, sem entities) → mostly skip; consumir entities do triage é integração futura. |
| **B-TRIAGE** | `sdk/plan_triage.py` (`triage_meta`) + `workers/triage_shadow.py` | ✅ **WIRADO CODE-COMPLETE** (`edf72cf7f`, flag-OFF) — job RQ `triage_step_shadow` roda `triage_meta` no meta (msg do usuário) do turno e grava em `outcome_signal['triage']` (NÃO `data['plan']` — B1 clobra a cada turno); **módulo 31** D8 (`enqueue_pending_triages`, gate `AGENT_PLANNER`). **Pendente: deploy+shadow.** |
| **B3** replan-loop | `plan_state.py` (`mark_step_failed`/`should_escalate`/`steps_to_retry`) + `AgentInvocationMetric.marcar_escalonamento` | ⏸️ **ADIADO COM PREMISSA** (decisão Rafael 2026-05-31). Mismatch real: `marcar_escalonamento` escreve em **AgentInvocationMetric** (linha por spawn de SUBAGENTE), mas o `PlanState` em shadow vem de eventos **Task\*** (tarefas do agente principal, SEM `agent_id` de subagente). **PREMISSA p/ wirar**: super-loop INLINE onde os steps de plano SÃO invocações de subagente com `agent_id` — só aí o mapeamento step-falho→AgentInvocationMetric existe. Em shadow batch, chamar `marcar_escalonamento` é prematuro/mal-definido. NÃO esquecer (ver memória `b3-escalate-adiado-premissa`). |
| **A3** eval-gate | `eval_gate_service.py` (`run_evals`/`eval_gate`) + `build_subprocess_invoke_fn` + `workers/eval_runner.py` + tabela `agent_eval_scores` + módulo 28 D8 | ✅ **FASE 1 WIRADA CODE-COMPLETE** (`9042023bb`, flag-OFF, verificada por MOCK). `build_subprocess_invoke_fn` = `claude -p --agent <nome>` (spike confirmou CLI 2.1.159 suporta `--agent`); job RQ `run_eval_batch` (fila NOVA `agent_eval` **PESADA**) roda os 4 datasets, persiste em `agent_eval_scores` (baseline ANTES de insert), report-only; módulo 28 passa a ENFILEIRAR (não inline — eval é 20-50min). **FASE 2 (supervisionada) PENDENTE**: UMA execução real (custo API + valida headless) — usar `python -m app.agente.workers.eval_runner --agent <nome>`; inspecionar `cases[].evidence` na 1ª rodada (I2: stdout vazio rc=0 vira 'fail', não sinaliza infra). report-only→enforce só após baseline estável. |
| **A4** promoção | `directive_promotion_service.py` + módulo D8 32 | ✅ **LIVE em PROD (2026-06-01)**: batch varre PlanStates → propõe → R9 anti-gaming + gate A3 → persiste `directive_status='shadow'` (nunca injetada — filtro do builder exclui shadow). `AGENT_DIRECTIVE_PROMOTION`=ON (no-op até PlanStates surgirem). Ativação shadow→ativa = manual. |

### Ordem GATED de WIRING (recomendada — cada fase depende da anterior validada em PROD)
1. **Fundação** (S0a/E1/B1/D*/F4-F5) validada em PROD — **em teste agora** (GATE-0/1).
2. **E2-enqueuer** ✅ CODE-COMPLETE na branch (`918d7e7af`, flag-OFF) — pendente deploy+shadow do Rafael. (judge em shadow, gravando vereditos; depois de agent_step OK + audit hook.)
3. **Super-loop do planejador** (shadow): ✅ **2a** fix `pending_questions` (`b31c18760`, baseline 2 falhas → 0) + ✅ **2b** B2 verify shadow (`15b681a8e`) + ✅ **2c** B-TRIAGE shadow (`edf72cf7f`) CODE-COMPLETE na branch (flags OFF). **B3 replan/escalate ADIADO COM PREMISSA** (super-loop inline com steps=subagentes). Pendente deploy+shadow (GATE-2) do Rafael.
4. **A3-invoke** ✅ FASE 1 CODE-COMPLETE na branch (`9042023bb`, flag-OFF, mock) — Fase 2 (run real supervisionado) + baseline pendente do Rafael. → **A4-batch** (fecha o flywheel ativo) — GATE-3.

> Detalhe de design por eixo: `eixos/A-flywheel.md` (E2/A3/A4), `eixos/B-planejador.md` (B2/B-TRIAGE/B3).

### 📍 CHECKPOINT 2026-05-31 — Plano inicial de WIRING: FEITO vs FALTA

> Plano inicial = as 4 fases de wiring (E2 → super-loop → A3 → A4) que tornam funcionais as features
> shadow. Sessão de 2026-05-31: 13 commits em `feat/agente-evolucao` (NÃO pushada), **607 passed / 0 failed**
> (pós-wiring; baseline pré-wiring era 572/2 — as 2 falhas eram `pending_questions`, agora zeradas).
> tudo flag-OFF. `main` intocada. Cadência: subagent-driven (TDD + spec-review + code-review por sub-task).

| Fase do plano | Status | Commits | O que falta |
|---|---|---|---|
| **1. E2-enqueuer** (judge shadow) | ✅ CODE-COMPLETE | `ec61021bb`→`366e62a0a` | só GATE (deploy+shadow Rafael) |
| **2. Super-loop** (B2+B-TRIAGE shadow) | ✅ CODE-COMPLETE | `b31c18760`→`687c55ef3` | só GATE; **B3 ⏸️ ADIADO COM PREMISSA** |
| **3. A3 gate de regressão** (FIEL À SPEC) | ✅ **R1-R4 CODE-COMPLETE** (2026-06-01) | `a3b293be1`→`0d104ec42` + `ba2e7dbd3`→`7adfa798b` | só GATE (deploy + ligar flags Rafael) |
| **4. A4-batch** (promoção diretriz) | ⬜ **NÃO INICIADA** | — | recon + plano + impl (a mais arriscada; muda comportamento ativo; pré-req baseline A3) |

**A3 FASE 2 — resultado (2026-05-31, local supervisionado, Rafael autorizou bypass restrito):**
- Smoke + 5 casos `analista-carteira` via `claude -p --agent` (CLI 2.1.159). **I2 CHECK passou** (5 rc=0, out 2194-3824 bytes, 0 fail-por-infra). 1º baseline binário = **0.600 (3/5)**.
- **Caveat I2 revelou 2 falsos-negativos**: ac-03 (limite carreta) e ac-04 (devolução) — o agente ACERTOU (li os outputs); o judge binário puniu por literalidade. Score real ≈ 5/5.
- **2 BUGS REAIS corrigidos (uncommitted, TDD, 627 passed):**
  1. **Judge binário** (`eval_gate_service.py`): `_call_haiku_eval_granular` retorna `{passed_items,total_items,failing}`; `_judge_case` calcula `case_score` parcial; `run_evals` = média; `PASS_THRESHOLD=0.80`. Retrocompat str pass/fail. **Cap em 1.0** (code-review HIGH-1). +16 testes.
  2. **SSL-drop na persistência** (`eval_runner.py`): `run_eval_batch` ficava 8-50min idle → `OperationalError` no commit → `agentes=0`. Fix: FASE 1 invokes / FASE 2 persistência com rollback+retry; **close()+dispose() quando rollback falha** (code-review HIGH-2, evita duplicata). +4 testes.
- Code-review adversarial: 0 CRITICAL, 2 HIGH (ambos corrigidos), MEDIUM-1 (semântica baseline pré/pós-fix) documentado no docstring.

**A3 RE-ESCOPO COMO GATE DE REGRESSÃO (2026-06-01) — fidelidade à spec:** após reler `eixos/A-flywheel.md:257-266` + `critica/*`, corrigi um desvio de interpretação: a A3 é **gate de regressão** (fecha Ruptura #5/#3), NÃO vestibular. O score absoluto (0.600/0.721) é de baixo valor por design; o que importa é o **Δ código-antes vs código-depois**. Os 2 fails do baseline granular (ac-03/ac-05) **se cancelam no Δ** (viés constante do dataset) — por isso NÃO reescrevi datasets (era tratar sintoma errado). Plano: `docs/superpowers/plans/2026-05-31-a3-gate-regressao.md`. 4 itens, todos commitados, flag-OFF, **668 passed**:
  - **R1 N-runs** (`3eebca5b9`): `run_evals` roda cada caso 3× (env `AGENT_EVAL_N_RUNS`), `case_score`=MEDIANA (doma o flaky — `run_eval.md:121`); `case_score_variance` + `invoke_failures` (caveat I2: distingue infra instável de agente ruim).
  - **R2 gate Δ** (`c5896ed90`): `run_eval_regression_gate(agent, sha_baseline)` mede Δ via `AgentEvalScore.get_score_by_git_sha`; `eval_gate` **report-only SEMPRE** (NUNCA bloqueia — testado com regressão máxima). 1ª medição: baseline=candidate.
  - **R3 calibração** (`e93893e1b`): migration dupla `agent_eval_case` (aplicada local); spot-check humano 5-10% (`sample_unreviewed` determinística + `concordance_rate`); gated `AGENT_EVAL_CALIBRATION` OFF. Code-review: M4 (fraction=0) + M3 (doc) corrigidos.
  - **R4 gate no D8** (`7adfa798b`): PASSO 3.5 no `dominio-8` — roda o gate ANTES do commit, report-only (registra `regressed`, fecha Ruptura #3: verified=Δ medido).

**NÃO pushado. main intocada quanto ao WIRING (lógica shadow já em main; faltam os commits de wiring).** Pendente: deploy + ligar flags (GATE do Rafael) → coletar baseline real em PROD.

> **CORREÇÃO factual (2026-05-31)**: o "main intocada" acima é IMPRECISO. Verificado via git: os 22 itens do blueprint (lógica shadow `step_judge`/`eval_gate_service` + tabela `agent_step` + TODAS as flags) JÁ ESTÃO em `origin/main` (mergeados em fase anterior). O que NÃO está em main são os **15 commits de WIRING** (`ec61021bb`→`2cf9280c6`): `eval_runner.py`, tabela `agent_eval_scores`, os `enqueue_*` e os **módulos 28-31 no scheduler**. Consequência: ligar as flags em PROD HOJE = no-op (ninguém chama `enqueue_*`). Big bang exige PUSH dos 15 commits → deploy. Branch SEM upstream, ausente em origin.

**Subprodutos colaterais entregues:** baseline `pending_questions` **2 falhas → 0** (fix threading 2a); 3 sinais coexistindo em `outcome_signal` (judge/verify/triage); 2 filas RQ novas (`agent_judge` LEVE, `agent_eval` PESADA); tabela `agent_eval_scores` (migration aplicada local).

**O QUE FALTA (acionável), em ordem:**
1. **Rafael — destravar GATEs:** push/deploy da branch → ligar flags em shadow (`AGENT_STEP_JUDGE`/`AGENT_VERIFY`/`AGENT_PLANNER`/`AGENT_EVAL_GATE`) → coletar vereditos ≥1 semana.
2. **Rafael+Claude — A3 Fase 2:** `python -m app.agente.workers.eval_runner --agent <nome>` (1 dataset, custo API) → **conferir `cases[].evidence` ANTES de confiar no baseline (caveat I2: stdout vazio com rc=0 — agente não-encontrado/sem-tools no headless — é julgado `fail`, não sinaliza erro de infra)** → estabelecer baseline real em `agent_eval_scores`.
3. **Claude — A4-batch** (após baseline A3): recon + plano + impl flag-OFF (migration dupla `directive_status`; reusa `_build_operational_directives`; gate A3 + anti-gaming R9).
4. **Claude — B3** (quando existir super-loop INLINE com steps=subagente/`agent_id`): wirar replan/escalate. Ver memória `b3-escalate-adiado-premissa`.

**Caveats conhecidos (quando LIGAR as flags em shadow):**
- **Concorrência `update_outcome` (LOW, auto-curável):** os 3 jobs do mesmo step (judge/verify/triage) podem rodar em Workers paralelos; `update_outcome` faz read-merge-write com `.first()` sem `SELECT FOR UPDATE` → possível lost-update de 1 sinal. **Auto-cura:** o varredor do sinal perdido re-enfileira no próximo ciclo (30min), pois o filtro `'X' not in outcome_signal` detecta a ausência. Impacto em shadow = atraso de ≤30min num veredito, nunca corrupção. Se virar problema sob volume: `with_for_update()` em `update_outcome`.
- `_ultimo_eval_gate`/`_ultimo_*` são process-local: restart do scheduler no mesmo dia re-enfileira (report-only, insere linha extra — ruído inofensivo).

> Prompt de teste + continuação: `docs/blueprint-agente/PROMPT_PROXIMA_SESSAO_WIRING.md` (criado nesta sessão).

---

### 📍 CHECKPOINT 2026-06-01 — A3 GATE DE REGRESSÃO MERGEADA + DEPLOY PROD + FLAGS

> Marco: a A3 (reconstruída como gate de regressão fiel à spec) + toda a fase de WIRING + Ondas 0-4
> foram MERGEADAS em `main` (merge `62e66e483`, `--no-ff`) e PUSHADAS (deploy PROD auto). **668 testes
> verdes na main pós-merge.** A árvore de trabalho do Rafael (148 schemas regenerados + settings.local)
> foi preservada via stash/pop (não entrou no deploy).

**O que foi para PROD (flags OFF — comportamento inerte até ligar):**
- WIRING shadow: E2-enqueuer (judge), super-loop (B2 verify + B-TRIAGE), A3-invoke.
- A3 gate de regressão: R1 N-runs · R2 gate Δ · R3 calibração (agent_eval_case) · R4 PASSO 3.5 no dominio-8.
- 2 fixes: judge granular + SSL-drop. Migrations agent_eval_scores + agent_eval_case (NÃO em build.sh).

**ORDEM DE ATIVAÇÃO EM PROD (obrigatória — code-review final pré-merge identificou):**
1. ✅ Deploy live (web `sistema-fretes` srv-d13m38vfte5s738t6p60 + worker srv-d2muidggjchc73d4segg).
2. ⚠️ **Rodar as 2 migrations no Render Shell ANTES de ligar flags** (tabelas NÃO estão no build.sh,
   PROD roda SKIP_DB_CREATE=true):
   `python scripts/migrations/2026_05_31_agent_eval_scores.py` +
   `python scripts/migrations/2026_06_01_agent_eval_case.py`.
3. Ligar flags em shadow (env vars no Render): `AGENT_STEP_JUDGE`, `AGENT_VERIFY`, `AGENT_PLANNER`,
   `AGENT_EVAL_GATE` (+ idealmente `AGENT_ODOO_AUDIT_HOOK` p/ a âncora do judge). `AGENT_EVAL_CALIBRATION`
   só após confirmar agent_eval_case criada.
4. Coletar vereditos ≥1 semana (shadow). Observar queries da Etapa A.4 do PROMPT_WIRING + logs
   `[JUDGE_ENQUEUER]`/`[VERIFY_ENQUEUER]`/`[TRIAGE_ENQUEUER]`/`[EVAL_GATE]` no Render.

**Achados do code-review final (não-bloqueantes, anotados):**
- MED-1 (pré-existente, fora de escopo): `agent_validation` ausente do `--queues` hardcoded em
  `start_worker_render.sh:301` → jobs `validate_subagent_output` não processados em PROD. **Corrigir
  numa próxima sessão** (não introduzido pela A3).
- MED-2: migrations agent_eval_* fora do build.sh → ação manual no Render Shell (padrão do projeto).

**Próximo:** A4-batch — ver `docs/blueprint-agente/PROMPT_PROXIMA_SESSAO_A4.md` (criado com regra
anti-drift: RELER a spec antes de decidir escopo, lição da sessão A3).

---

### 📍 CHECKPOINT 2026-06-01 (tarde) — VALIDAÇÃO DE FUNCIONAMENTO + MEDIÇÃO (Ondas 0-4)

> Sessão READ-ONLY de medição (PROD via MCP Render, Postgres `dpg-d13m38vfte5s738t6p50-a`,
> web `srv-d13m38vfte5s738t6p60`, worker `srv-d2muidggjchc73d4segg`). Nada foi ligado/alterado.
> **JANELA DE DADOS ≈ 14h, PRELIMINAR**: 1ª linha `agent_step` 2026-05-31 20:48 BRT (1 teste, user 1);
> tráfego real só na manhã de 2026-06-01 (~08:34–10:41 BRT), **67 turnos / 7 sessões / 6 usuários**,
> concentrado em 2 power-users (82=25 steps, 17=15+13). Fim de semana/feriado ≈ 0. **Qualquer conclusão
> de "qualidade melhorou" é prematura** (held-out anti-gaming pede ≥2 semanas — GATE-3).

**⚠️ DISCIPLINA DE TIMEZONE (lição desta sessão):** `agent_step.created_at`/`agent_sessions.updated_at`
gravam **Brasil-naive (UTC-3)**; `now()` do Postgres é **UTC**. Comparar os dois inventa um gap de 3h.
Regra para queries de recência: usar `now() AT TIME ZONE 'America/Sao_Paulo'`. (Quase reportei um falso
"S0a parou de gravar há 3h" — era só o offset. Verificado: último step há ~65s, 48 steps/última hora,
`n_steps == message_count/2` em toda sessão ativa → **S0a 100% saudável, 1 step/turno**.)

**ESTADO REAL DAS FLAGS (todas VERIFICADAS por dado/log, não assumidas):**
| Flag | Estado | Evidência |
|---|---|---|
| `AGENT_QUALITY_SPINE` | **ON** | `frustration_score` em 67/67 steps |
| `AGENT_STEP_JUDGE` | **ON** | `outcome_signal.judge` em 51/67; log `[JUDGE_ENQUEUER]` a cada ~30min |
| `AGENT_VERIFY` | **ON** | `outcome_signal.verify` (3 verifiers) em 51/67; log `[VERIFY_ENQUEUER]` |
| `AGENT_PLANNER` | **ON** | `outcome_signal.triage` em 50/67; log `[TRIAGE_ENQUEUER]`. **MAS B1 PlanState=0** |
| `AGENT_ODOO_AUDIT_HOOK` | **ON** | `operacao_odoo_auditoria` contexto=`execute_kw_hook` = 350 linhas (último 10:07) |
| `AGENT_ONTOLOGY` | **ON** | log `MCP 'ontology' registrada (query_ontology)` por turno; 3.539 entidades user_id=0 |
| `AGENT_SKILL_RAG` | **ON** | log `[CONTEXT_BUDGET] skill_hints_chars=186..274` (0 quando nada ranqueia) |
| `AGENT_WORLD_MODEL_INJECT` | **ON** | log `world_model_chars=320..452` |
| `AGENT_DIRECTIVE_PROMOTION` | **ON** | log `[directive_promotion] batch concluído {candidatos:0...}` (no-op) |
| `AGENT_OPERATIONAL_DIRECTIVES` | **ON** | log `[OPERATIONAL_DIRECTIVES] directives=5 chars=3220` todo turno |
| `AGENT_EVAL_GATE` | **inerte** | sem log `[EVAL_GATE]` runtime; só criação de tabela no build.sh (26d). `agent_eval_scores`=0 |
| `AGENT_EVAL_CALIBRATION` | **moot** | `agent_eval_case`=0 (sem casos p/ calibrar) |
| `AGENT_CAPABILITY_REGISTRY` | n/d | descritor estático, não observável em dado |

**PARTE 1 — A MAQUINARIA PRODUZ DADO? (validação)** — predominantemente **SIM**:
- ✅ **S0a** `agent_step`: 1 linha/turno, real-time, `n_steps==message_count/2`. **Só canal `web`** — `teams`=0
  (sem tráfego Teams na janela; wiring Teams NÃO exercido → validar com 1 turno de teste no Teams).
- ✅ **E1** quality spine: `frustration_score` 67/67 (maioria 0; alguns 1-5). 👍👎→step: **NÃO exercido**
  (0 feedbacks pós-flag; 12 sessões com feedback historicamente, 0 na janela).
- ✅ **E2** judge: 51 vereditos, score VARIA {15,25,35,45,85}, label success/partial/failure, com evidência+culpado.
- ✅ **B2** verify: 3 verifiers gravando; `domain` **sempre skip=`no_plan`** (consequência de B1=0).
- ✅ **B-TRIAGE**: roda, mas `steps:[]` vazio (tráfego single-shot não decompõe).
- 🔴 **B1 PlanState = 0** (em 725 sessões). **Causa-raiz confirmada: `Task` tool usado 0× em 67 turnos** —
  o agente web responde single-shot/tool-direto, nunca emite Task*. B1 está wired certo; **falta combustível**
  (tráfego não-planejável). Como A4 e o `domain` verifier dependem de PlanState → **gargalo do flywheel**.
- 🟡 **A3 eval**: `agent_eval_scores`=0. Fase 2 (`eval_runner.py --agent analista-carteira`) foi tentada
  **LOCAL** (Rafael, NACOM052) e **falhou ao persistir** (Sentry X7 `[EVAL_RUNNER] commit falhou: invalid
  transaction not rolled back` — o fix SSL-drop NÃO cobriu este caminho). **Baseline ainda inexistente.**
- ✅ **A4** batch: roda limpo, **no-op** (`candidatos=0`, 0 PlanStates). `directive_status`: 606 memórias, TODAS NULL.
- ✅ **R9** âncora: hook grava 350 ops. **PORÉM anti-gaming NÃO testado**: só **1** `FALHA_ODOO` na janela e
  ela **não casa com nenhum `agent_step`** (0 overlap) → a "dominância ambiental" teve n=0 oportunidades reais.
- ✅ **D2/D4** ontologia: substrato 3.539 entidades user_id=0; tool `query_ontology` registrada **mas usada 0×**.
- 🟡 **D3** proveniência bi-temporal: colunas existem, **0/7190 relations + 0/2246 links** têm
  `source_session_id`/`valid_from` → **proveniência não está sendo gravada** apesar de `AGENT_ONTOLOGY` ON
  (investigar se o path de escrita de relações propaga os params — relações nascem por caminho não-instrumentado).
- ✅ **Onda 4** F4/F5+D5: `<skill_hints>`/`<world_model>` injetados (mas pequenos vs ~45K de memória).

**PARTE 2 — O RESULTADO É BOM? (qualidade)** — **NÃO MENSURÁVEL AINDA** (sinal não calibrado + volume fino):
- ⚠️ **Judge tem viés sistemático**: turnos **sem tool** julgados `failure` **88%** (14/16) vs 57% com tool;
  o judge trata "sem ferramenta" ≈ "sem ação" ≈ falha, punindo respostas informativas corretas.
- ⚠️ **Judge vs verify em contradição em 73%**: o verifier `adversarial` **refuta o judge em 37/51** vereditos
  (ex.: refuta "failure por ausência de tool"). Nada reconcilia os dois num sinal corrigido.
- ⚠️ **0 calibração humana** (`agent_eval_case`=0): impossível dizer se judge ou verifier está certo.
- Distribuição judge: 67% failure / 18% partial / 16% success — **inflada pelo viés acima** (não é métrica de
  qualidade do agente). `culpado=odoo` em 23/51 é **inferência do judge** (não a âncora R9, que teve n=0).

**PARTE 4 — REGRESSÃO?** Sentry PROD do agente **LIMPO** quanto ao blueprint. Os 2 erros "novos" (X7
eval_runner, X5 JSONDecodeError `/tmp/c_audit.py`) são **`environment=development` (NACOM052, máquina do
Rafael)** — não PROD. X6/X4 são Odoo XML-RPC (pré-existentes). `escalated_to_human`/`user_correction_received`:
não escritos (B3 adiado + sem feedback). Latência: judge/verify/triage 100% off-path (RQ fila `agent_judge`).

**STATUS DOS GATES (medido):**
- **GATE-0** (S0a ≥48h, web+teams, Sentry limpo): **web ✅ / teams ⬜ não-exercido**. Falta tráfego Teams.
- **GATE-1** (sinal qualidade ≥1sem + judge calibrado): ❌ — só ~14h, judge enviesado, 0 calibração.
- **GATE-2** (super-loop em tarefas reais + verify shadow + `escalated_to_human` escrito): ⚠️ parcial — verify
  grava, mas **sem PlanState/Task* não há super-loop real**; `escalated_to_human` não escrito (B3 adiado).
- **GATE-3** (flywheel fechado shadow ≥2sem + held-out): ❌ — A4 no-op (0 PlanState), 0 baseline A3.

**DECISÕES GATED (para o Rafael — NÃO executar sem aval):**
1. 🔴 **Destravar B1 PlanState** (sem isto o flywheel é no-op eterno): o tráfego web não emite `Task*`. Decidir
   se (a) o agente principal passa a decompor via subagentes/Task em tarefas multi-step, ou (b) capturar plano
   de outra fonte (triage já roda — promover triage→PlanState?). É pré-condição de A4 e do verifier `domain`.
2. **A3 Fase 2**: re-rodar `eval_runner` (LOCAL ou PROD) **corrigindo o bug de transação** (X7) antes — senão
   baseline nunca persiste. Inspecionar `cases[].evidence` (caveat I2).
3. **Judge calibração/viés**: antes de A3-enforce ou A4-ativa, tratar o viés "sem-tool=failure" e ligar
   `AGENT_EVAL_CALIBRATION` p/ spot-check humano 5-10% (hoje 0 casos). Sinal não-calibrado não deve gatear nada.
4. **D3 proveniência = 0**: investigar wiring (baixa prioridade — nice-to-have).
5. **Coletar ≥1-2 semanas de dias úteis** antes de qualquer `shadow→ativa` / enforce. Hoje é PRELIMINAR.

---

## ONDAS E ITENS

> Status: ⬜ pending · 🟡 em progresso · 🔵 shadow (código pronto, validando comportamento) · ✅ done
> Esforço relativo (P/M/G) é orientativo — NÃO é critério de ordem.

### ONDA 0 — FUNDAÇÃO FÍSICA  ·  GATE-0 destrava Ondas 1 e 2
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **S0a** | Tabela `agent_step` (1ª classe), granularidade TURNO, `step_uid` UNIQUE=`'{session_id}:{turn_seq}'` (join com costs por session+janela). Populada no fim da thread PRIMARY (R10), nunca no `_stop_hook`. Migration dupla. | — | (schema, sem flag) | M | ✅ **COMPLETO** — model `c13fb31c4` + wiring web `8287406fa` + **wiring Teams `dbe0e8700`** (S0a-teams, INV-3: helper `_gravar_agent_step_teams` nos 2 pontos de persistência, idempotente). 9 testes (web+teams). |
| **S0b** | Consolidar deny-list dispersa: mover `SPED_SKILLS_RESERVED` (`settings.py:40`) p/ `skills_whitelist.py` (4º grupo); `client.py` lê UMA fonte. | — | — | P | ✅ **COMPLETO** — commit `f3f6227eb`: `SKILLS_SPED_RESERVED` em `skills_whitelist.py` somado à união; `settings` re-exporta (retrocompat); `client.py` lê `SKILLS_DELEGADAS_SUBAGENTE` (fonte única). 4 testes novos; 12 testes SPED verdes; baseline 337→341. |
| **S0c** | Capability Registry DESCRITIVO: `SkillEntry` + `SkillBinding` (aresta N:M skill↔agente — exposure NÃO é escalar). Populado por `agent_loader._parse_skills` + 5 tabelas-catálogo do estoque. Read-only (flag OFF: só descreve). | S0b | `AGENT_CAPABILITY_REGISTRY` | M | ✅ **COMPLETO** — commit `b3a89f97e`: `capability_registry.py` (50 skills, 116 bindings, 17 agentes; `consultando-sql`=11). Flag `AGENT_CAPABILITY_REGISTRY` OFF. 4 testes; baseline 341→345. **Escopo:** enriquecimento via 5 tabelas-catálogo do estoque DIFERIDO p/ F4/D2 (contrato N:M não depende). Nit pendente: `Optional` não-usado → limpeza no fechamento. |

**Wiring S0a**: produtor = `run_async_stream` finally (thread PRIMARY, `client.py`) → grava `agent_step` → consumidores futuros = E1/E2 (sinal), B1 (PlanState), A (recalibração). Reusa: `AgentSessionCost.message_id` UNIQUE (`models.py:1413`), padrão `insert_metric` SAVEPOINT (`models.py:1664-1719`).
**GATE-0 (verde para seguir)**: `agent_step` gravando 1 linha/turno em PROD por ≥48h, joinável com `AgentSessionCost` e `agent_sessions`; zero impacto em latência/erro (Sentry limpo); registry descritivo bate com os 16 frontmatters + catálogos (auditoria read-only).

### ONDA 1 — FUNDAÇÃO SEMÂNTICA (E↔D em paralelo)  ·  GATE-1 destrava Onda 3 (flywheel)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **E1** | Sinais humanos/implícitos → `agent_step`: capturar `score` de `detect_frustration` (`sentiment_detector.py`, hoje só in-memory) + 👍👎 (`data['feedbacks']` não-joinável) na entidade de passo. (`_adjust_importance_for_corrections` NÃO ressuscitada — era dead-code.) | S0a | `AGENT_QUALITY_SPINE` | M | ✅ **COMPLETO** — commit `4e3de61f8`: `AgentStep.update_outcome` (merge JSONB SAVEPOINT) + `get_last_frustration_score` + wiring web/teams (mesmo step_uid, sob flag) + link 👍👎→step. 8 testes (incl. prova flag-OFF=zero write). baseline→360. |
| **E2/A1** | Componente UNIFICADO `attribution_judge`(=step_quality): judge batch (clona `subagent_validator`), ancorado no audit Odoo R9 (`operacao_odoo_auditoria`), produz por passo de risco `{score, label, componente_culpado, evidência}` (Process Reward Model). Ambiental (R9) DOMINA. | S0a, D0.5 | `AGENT_STEP_JUDGE` | G | ✅ **COMPLETO** — `f06ee60fc` + fix `de0e27158`: `workers/step_judge.py` (`_judge_core` testável + `judge_step` job RQ); FALHA_ODOO força score≤35+componente='odoo' (não-gameável); SHADOW (sem enqueue ativo); flag OFF. 11 testes. **Code-review CRITICAL-1**: faltava `commit` no job RQ → corrigido. |
| **D0** | Higiene KG: corrigir leak `:E/:A` (`knowledge_graph_service.py:403`). ~~resolução-ao-nó/`with_key=0`~~ DIFERIDO (premissa não-confirmada — é guard de nome-vazio, precisa dados PROD). | — | — | P | ✅ **COMPLETO** — commit `fb2ecd77b`: strip do sufixo em `parse_contextual_response` (1 linha; `else` preserva `:` legítimo). 2 testes + 3 flags Onda 1 OFF. Resolução canônica diferida. |
| **D0.5** | ESCOPO `user_id=0`: nós canônicos = EMPRESA, `query_graph_memories ANY([user_id,0])`. | — | — | P | ✅ **COMPLETO** — commit `03d0601b9`: JÁ implementado (`query_graph_memories:797` + escrita empresa); blindado com teste de regressão. Bootstrap massivo (onde a irreversibilidade morde) fica na D2/Onda 3 atrás de flag. |

**Wiring E1/E2**: produtor = callsite `detect_frustration` (`chat.py:560`) + `feedback.py` (Web) + judge batch (RQ) → grava em `agent_step.outcome_*` → consumidor = A (recalibração) na Onda 3. Reusa: `subagent_validator` (esqueleto), `friction_analyzer` (4 detectores), `operacao_odoo_auditoria` (R9), `_adjust_importance_for_corrections` (estacionado), `sql_evaluator_falses_service` (calibração).
**GATE-1**: sinal de qualidade step-level gravado e auditável por ≥1 semana; judge calibrado (concordância ≥X% com spot-check humano em held-out); E↔D validado (ontologia não piora retrieval medido pelo sinal).

### ONDA 2 — ATUADOR DE PLANEJAMENTO  ·  GATE-2 destrava promoção de plano (Onda 3 A4)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **B1** | PlanState durável + Plan tools (promover Task* cosméticos) em `AgentSession.data['plan']`, reusa `flag_modified`. | S0a | `AGENT_PLANNER` | M | ✅ **COMPLETO** — `286134082`: `sdk/plan_state.py` (PlanState puro) + captura Task* via stream (`_process_stream_event`→`_save_messages_dedup`→`_save_messages_to_db`, seguindo padrão `tools_used`), 3 guards `USE_AGENT_PLANNER` em série. 18 testes + flag-OFF=zero write. |
| **B-TRIAGE** | Classificador semântico NOVO (NÃO reusar `model_router` — é o inverso): decompõe meta em steps sobre entidades do KG. | B1, D2 | `AGENT_PLANNER` | M | ✅ **COMPLETO** — `561ce71cd`: `sdk/plan_triage.py` (`triage_meta` LLM-decompõe + ancora via `query_ontology_entities`). 13 testes, shadow, degrada sem ontologia/LLM. |
| **B2** | VERIFY, 3 verifiers: `arithmetic` (promove `_self_correct_response`), `adversarial` (job RQ cético), **`domain`** (ontologia D + guards — DIFERIDO pós-D2). Rodar em SOMBRA. | B1, (D2 p/ domain) | `AGENT_VERIFY` | G | ✅ **arith+adv COMPLETO** — `9691d9e62`: `sdk/verifiers.py` (`verify_arithmetic`) + `workers/plan_verifier.py` (`verify_plan_adversarial` job RQ cético, commit explícito). 13 testes, shadow. **`domain` ✅** `cd4f9b893`: `verify_domain` valida step contra ontologia (`query_ontology_entities`); NÃO duplica guards estoque (ficam no dry-run executor); hook `extra_checks`. 9 testes. **B2 completo (3 verifiers).** |
| **B3** | REPLAN com budget + escalate → escreve `escalated_to_human` (campo morto `models.py:1647`). | B1, B2 | `AGENT_PLANNER` | M | ✅ **COMPLETO** — `7ea589f65`: `PlanState` +`mark_step_failed`/`should_escalate`/`steps_to_retry` (budget) + `AgentInvocationMetric.marcar_escalonamento` (SAVEPOINT+commit). 22 testes (+18 B1 intactos). ~~Chamador no loop = shadow sob flag.~~ **WIRING DO CALLER ⏸️ ADIADO COM PREMISSA (2026-05-31)** — `marcar_escalonamento` escreve em AgentInvocationMetric (subagente c/ `agent_id`), incompatível com PlanState-Task* atual; só wirar com super-loop INLINE. Ver tabela 🟡 (linha B3) + memória `b3-escalate-adiado-premissa`. A LÓGICA (este commit) está pronta; só falta o caller. |

**Wiring B**: B emite eventos de plano (SSE) → se novo evento, R8 = 3 camadas (`client.py`→`routes/chat.py`→`chat.js`). VERIFY consome ontologia (D) + guards (código). Aprovação de plano = **Web-only na largada** (INV-3). Reusa: `_self_correct_response` (`client.py:792`), `subagent_validator`, guards de estoque, `pending_questions.py` (R-MULTIWORKER) p/ aprovação.
**GATE-2**: super-loop rodando em tarefas reais com VERIFY em shadow; `escalated_to_human` sendo escrito; zero regressão em tarefas single-shot existentes.

> **ONDA 2 — STATUS (2026-05-31)**: subconjunto buildável (B1, B2-arith, B2-adv, B3) ✅ COMPLETO + revisado. **B-TRIAGE e B2-domain DIFERIDOS** (dependem de D2/ontologia, Onda 3) — fazer após D2. Code-review: 0 CRITICAL; **H1** (`marcar_escalonamento` commitava — inverso do CRITICAL-1: caller é request Flask que já commita → removido, espelha `insert_metric`) + **I1** (import morto) corrigidos em `31aa9496c`. Suíte agente+teams **425 passed / 2 failed** (baseline pending_questions). Tudo flag-OFF. GATE-2 pendente de deploy/shadow.

### ONDA 3 — FECHAR O FLYWHEEL  ·  (muda comportamento ativo — só sobre fundações confiáveis)
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **A3** | Eval runner automatizado + gate no D8 (golden datasets `evals/`). Processo EXTERNO ao agente avaliado, report-only→enforce. | GATE-1 | `AGENT_EVAL_GATE` | M | ✅ **COMPLETO** — `f5883709b`: `services/eval_gate_service.py` (`load_golden_dataset`/`run_evals`/`eval_gate`; invoke do agente = SEAM injetável, Haiku-as-judge) + módulo 28 no D8 (`sincronizacao_incremental_definitiva.py`, flag `AGENT_EVAL_GATE` OFF = no-op, try/except isolado, **report-only NUNCA bloqueia**). 27 testes (sem API). Enforce + wiring real do invoke = ativação pós-deploy. |
| **A4** | Promoção automática de diretriz (liga `USE_OPERATIONAL_DIRECTIVES` com segurança): candidata→shadow/A-B→regression-gate→promove→monitora-drift→auto-despromove. Plano que funcionou (B§5) é o artefato promovível. Reusa `_build_operational_directives` (`memory_injection.py:420`). | A3, GATE-2 | `USE_OPERATIONAL_DIRECTIVES` + `AGENT_DIRECTIVE_PROMOTION` | G | ✅ **V1 LIVE EM PROD (2026-06-01)** — mergeada (`7fef3778c`) + DEPLOYED (web `dep-d8enl64` live após retry — o deploy anterior deu **timeout de health-check**, NÃO erro A4; worker live). Migration `directive_status` rodou via build.sh **26e**; `AGENT_DIRECTIVE_PROMOTION`=ON (batch módulo 32 rodando **no-op**: `candidatos=0`, 0 PlanStates). A4-batch CONSTRUÍDA (lógica shadow original `83d6ce61c`). Migration dupla `directive_status` (`7c0500f76`); builder filtra `directive_status IN (NULL,'ativa')` = **alavanca de ativação** (`b8db8c560`); `_persist_directive` **REAL** escreve `directive_status='shadow'` idempotente, formato = heurística orgânica (`cf0d920cc`); `run_directive_promotion_batch` + **módulo D8 32** INLINE flag-gated `AGENT_DIRECTIVE_PROMOTION` (`e122e43c3`); cleanup docstrings+rollback-por-iteração (`ddb9aa877`). **677 testes verdes** (+9 A4). Subagent-driven (4 implementers + spec+code-review/task + **review holístico final: SHIP-READY, 7/7 invariantes HOLD**). **Dupla segurança**: shadow NUNCA injetada + `AGENT_OPERATIONAL_DIRECTIVES` OFF. R9 anti-gaming DOMINA (`_tem_falha_odoo` antes do gate). Decisão de escopo (spec+PROD): **A/B de produção = A4 V2** (depende de A1/judge signal — 0 em PROD); regression-gate = A3 periódico global (não há golden do agente principal). ⚠️ **DESCOBERTA PROD (2026-06-01)**: `AGENT_OPERATIONAL_DIRECTIVES` **JÁ estava ON** em PROD (injeta top-5 heurísticas legado `NULL` nos prompts — comportamento EXISTENTE, NÃO introduzido pela A4; eu assumira OFF — erro de premissa, devia ter VERIFICADO o valor real). A4 é **transparente**: o filtro `IN(NULL,'ativa')` exclui `shadow` → candidatas promovidas pelo batch **NÃO** são injetadas (dupla segurança intacta mesmo com a flag ON); set injetado idêntico antes/depois do deploy (`directives=5 chars=3220`). **Ativação shadow→ativa = revisão manual**. **build.sh lento (~15-20min: 58 migrations × `create_app()`)** = issue de infra SEPARADO, tratado pelo Rafael em outra sessão (diagnóstico na memória `deploy-web-build-lento`). Plano: `docs/superpowers/plans/2026-06-01-a4-promocao-diretriz.md`. |
| **D2** | Bootstrap ontologia das TABELAS-mestre corretas (`carteira_principal`/`transportadoras`, NÃO `entity_indexer`→`contas_a_pagar`). | D0, D0.5 | `AGENT_ONTOLOGY` | G | ✅ **COMPLETO** — `5ac8ecafc`: `services/ontology_bootstrap.py` (cliente/produto/transportadora → `_upsert_entity` user_id=0, idempotente, **ZERO Voyage**) + CLI `scripts/agente/bootstrap_ontologia.py` (`--dry-run`/`--force`, não auto-run). 23 testes. Read path = D4. |
| **D3** | Fatos bi-temporais + episode subgraph de proveniência (reusa `session_turn_indexer.py`). | D2 | `AGENT_ONTOLOGY` | M | ✅ **COMPLETO** — `b75d90b78`: migration dupla (`2026_05_31_kg_bitemporal`, +valid_from/valid_to/source_session_id/source_step_uid em relations, +source_* em links; aplicada local). `_upsert_relation`/`_link_entity_to_memory`/`extract_and_link_entities` ganham params opcionais (backward-compat None); população de proveniência gated por `AGENT_ONTOLOGY` em `memory_mcp_tool` (flag OFF=NULL); ON CONFLICT 1ª-origem-vence. 8 testes; KG intactos. `valid_to`/`source_step_uid` NULL no MVP (invalidação + ContextVar step_uid = fase posterior). |
| **D4** | Tool MCP `query_ontology` (agente consulta o modelo de mundo). | D2 | `AGENT_ONTOLOGY` | M | ✅ **COMPLETO** — `d36752073`: `tools/ontology_query_tool.py` (`query_ontology_entities` busca DIRETA user_id IN [uid,0]) + tool MCP `query_ontology` registrada flag-gated em `client.py` (invisível com flag OFF). 12 testes (prova busca direta sem HOP-1). **Fecha o gap D2 → destrava B-TRIAGE+B2-domain.** |

**GATE-3**: flywheel fechado em shadow (promoção sugere, não aplica) por ≥2 semanas com held-out anti-gaming OK; ontologia consultável validada contra os ~298 schemas.

#> **2026-05-31 — BLUEPRINT CODE-COMPLETE + 100% REVISADO (22 itens, Ondas 0-4)**: D3 `b75d90b78` · A3 `f5883709b` · A4 `83d6ce61c` (flywheel fechado shadow) · Onda 4 F4/F5+D5 `7ccae5f56`. **Code-review final** (D3/A3/A4/Onda4, `/tmp/subagent-findings/review-final.md`): 0 CRITICAL; **HIGH-1** (`valid_from` sem COALESCE no ON CONFLICT → descartado silenciosamente; inconsistente c/ proveniência) corrigido `1c321e232`. Confirmados OK: migration idempotente, SQL sem-injeção, A3 cron isolado/report-only, A4 anti-gaming, hook Onda 4 best-effort por bloco, flags-OFF=zero mudança, timezone. **Suíte final 572 passed / 2 failed** (baseline `pending_questions`, herdado da main). 71 commits, 32 de código. **TUDO flag-OFF — pendente só os GATEs (deploy do Rafael).**

## ONDA 4 — TETO DE ESCALA
| Item | Descrição | Dep | Flag | Esf | Status |
|------|-----------|-----|------|-----|--------|
| **F4/F5** | Routing gerado + Skill-RAG por domínio. | S0c, B2, D2 | `AGENT_SKILL_RAG` | G | ✅ **COMPLETO (advisory)** — `7ccae5f56`: `sdk/context_enrichment.py` (`rank_skills_for_query` token-overlap sobre registry S0c + `build_skill_hints_block`) injeta `<skill_hints>` via hook. **GAP SDK honesto**: `skills=` fixo no `connect()` (sem `set_skills()` por turno) → versão ADVISORY (aconselha, não filtra o listing). 22 testes (compart. D5). Flag OFF. |
| **D5** | `<world_model>` substitui `_DOMAIN_KEYWORDS` mantendo-o como fallback (cold start). | D2, F4/F5 | `AGENT_WORLD_MODEL_INJECT` | M | ✅ **COMPLETO** — `7ccae5f56`: `build_world_model_block` (ontologia D4 via `query_ontology_entities`) injeta `<world_model>` via MESMO hook `UserPromptSubmit` (INV-7). ADITIVO: `_DOMAIN_KEYWORDS`/`_build_routing_context` intactos = fallback cold-start. Flag OFF = zero mudança. |

---

## EIXOS C + G — MEMÓRIA PESSOAL & VIGILÂNCIA (avaliação de memória, 2026-06-02)

> Avaliação dimensional do sistema de memória (02/06/2026). **Reconciliação:** `RECONCILIACAO_MEMORIA.md`.
> **Eixos:** `eixos/C-vigilancia.md` (vigilância proativa — preenche o "Eixo C" já referenciado por `critica/D-ontologia.md:213,237`), `eixos/G-memoria-pessoal.md` (pipeline de memória pessoal + recuperação).
> **Plano F1 (acionável):** `docs/superpowers/plans/2026-06-02-loop-corretivo-pessoal.md`.
> **Sintoma-gatilho (Marcus, user 18):** correção explicada NÃO adere na sessão seguinte — prova PROD: `semantic=0`/`tier2_chars=0` em toda sessão "atualizar baseline".
> **Tese:** infraestrutura construída e DESLIGADA — *ligar + medir > reconstruir*. **Regra de ouro:** medição (E) antes de atuadores; gate de escrita empresa (F) antes de promover.
> **NÃO duplicar:** F5↔eixo D (KG), F8↔eixo E (qualidade), F3↔A4 (já LIVE) — ver reconciliação. Tudo abaixo ⬜ PENDENTE (diagnóstico+plano; nada implementado). DoD global aplica.

| Item | Descrição | Dep | Flag | Status |
|------|-----------|-----|------|--------|
| **G-F1** | Loop corretivo pessoal: ligar canal `_build_user_rules` + write-path UPDATE-vs-ADD + promoção por reincidência + medição por outcome. (plano dedicado, 3 fases) | E (medir), F (gate escrita) | `AGENT_USER_RULES_CHANNEL`+`AGENT_CORRECTION_PROMOTION`+`AGENT_CORRECTION_RECONCILER` | 🟡 **Fase 0 ✅ (02/06)**: AgingBench P1/P2/P3 offline (3 correções reais do Marcus × 3 cond × 3 rep) → Acc(P1)=0% / P2=67% / P3=89%. **DECISÃO = falha de RETRIEVAL** (correção não chega; quando presente no topo, o agente obedece — P3≫P1). Cura = canal duro (Fases 1-2). Fase 3 (reescrita imperativa) = complemento p/ correções tipo-A que competem com o pedido literal do usuário.<br>**Fase 1 CÓDIGO ✅ (02/06)**: `_build_user_rules` (`memory_injection_rules.py`) `order_by(correction_count desc)` + cap `MANDATORY_RULES_MAX_COUNT=12` (IFScale); `USE_USER_RULES_CHANNEL` **default ON** (decisão Rafael: evitar feature zumbi; seguro = canal aditivo até Fase 2 encher via gate R9+A3); 2 testes TDD (cap+ordenação) → **68 verdes**. **Pendente Fase 1**: (a) backfill das ~9 correções do Marcus → 1 canônica mandatory (write PROD, dry-run+OK); (b) **tuning de posição** — hoje `<user_rules>` entra em tier0, anexado APÓS as estáveis (`memory_injection.py:1214`); a Fase 0 mostrou que o TOPO rende mais → mover p/ topo na Fase 3.<br>**Fase 2 CÓDIGO ✅ (02/06)**: (A) write-path UPDATE — reincidência de correção → `correction_count++` + importance↑ em `pattern_analyzer._save_personal_insight` (substitui o `return False` que descartava); (B) **promoção RECORRENTE** `promover_correcoes_recorrentes` (cc≥`AGENT_CORRECTION_PROMOTION_THRESHOLD`=2 → `priority='mandatory'`) como **3ª fonte do batch DIÁRIO (módulo 32)** — decisão Rafael: recorrente, não script one-shot; idempotente; flags ON. 3 testes TDD → **71 verdes**. "Backfill" = 1º ciclo do batch (dry-run+OK).<br>**Fase 3 CÓDIGO ✅ (02/06)** — 7 itens, TDD, todos flag-gated + aditivos: **3.1** migration dupla `error_signature`+`harmful_count`+`helpful_count` (índice `(user_id,error_signature)`, aplicada local); **3.2** extrator emite `error_signature` (intenção normalizada) + `_reframe_as_compiled_memory` (frame imperativo SEMPRE/NUNCA+WHEN/DO na promoção, idempotente, re-embed); **3.3** medição por OUTCOME desacoplada do eco (`harmful_count` no write-path quando regra dura reincide; `helpful_count` via `_track_outcome_by_recurrence` bounded por `usage_count%K`, wired chat+teams); **3.4** `<user_rules>` no TOPO absoluto (`USE_USER_RULES_TOP` ON) + recorrência no composite score (`USE_RECURRENCE_SCORE` OFF); **3.5** HARD enforcement PreToolUse (`USE_MANDATORY_HARD_ENFORCE` OFF, opt-in por `ENFORCE_DENY_SUBSTR:`, fail-open); **3.6** `demote_stale_rules` (regra dura harmful→contextual+cold, flap-free, `AGENT_CORRECTION_DEMOTION` OFF); **3.7** painel adesão `get_rule_adhesion_panel` (reincidência por assinatura antes/depois + rota admin). **39 verdes** (Fases 1+2+3). Commits no worktree `feat/blueprint-eixo-c-memoria` (52a7b3887 3.1 → 16a851e19 3.7). **FLAGS:** ON = `USE_USER_RULES_CHANNEL`, `USE_USER_RULES_TOP`, `AGENT_CORRECTION_PROMOTION`, `AGENT_OUTCOME_TRACKING`; OFF (riscos/inertes) = `USE_RECURRENCE_SCORE` (cc≈0 até popular), `AGENT_CORRECTION_DEMOTION` (remove regra de circulação), `USE_MANDATORY_HARD_ENFORCE` (pode bloquear op legítima). **Pendente:** (a) **backfill do passivo Marcus** (write PROD, dry-run pronto, aguarda GO do Rafael); (b) migration 3.1 no PROD + push (Rafael); (c) frontend card do painel 3.7 (dado já flui via `get_insights_data['rule_adhesion']`). |
| **G-F2** | Aprendizado procedural POSITIVO: tipo `receita` no extrator + fechar feedback 👍 (hoje descartado, `routes/feedback.py:66-90`). Ratio receita:armadilha ≈ 0:1 hoje | E | `AGENT_POSITIVE_LEARNING` (novo) | ⬜ PENDENTE |
| **G-F4** | Perfil/budget: ligar `USE_USER_XML_POINTER` (`feature_flags.py:201`) + reservar budget Tier 2 (hoje zerado p/ ~5 users) | — | `USE_USER_XML_POINTER` | ⬜ PENDENTE |
| **G-F6** | Recuperação: HyDE + threshold adaptativo por tamanho de prompt (91% <150 chars → `semantic=0`); somar recorrência ao composite (`memory_injection.py:945`) | — | `AGENT_MEMORY_HYDE` (novo) | ⬜ PENDENTE |
| **G-F7** | Continuidade: anti-contaminação `work_context` (overwrite incondicional `pattern_analyzer.py:2064-2072`, usa domínio dominante) + ciclo de pendências | — | (ajuste) | ⬜ PENDENTE |
| **G-F10** | Injeção de memória em subagentes (hoje amnésia): `SubagentStart` hook (`hooks.py:434`) + `additionalContext` | D2 | `AGENT_SUBAGENT_MEMORY` (novo) | ⬜ PENDENTE |
| **C0** | Job offline de coerência (report-only): detecta contradição + staleness no corpus | E, D | `AGENT_MEMORY_VIGILANCE` (novo) | ⬜ PENDENTE |
| **C1** | Bi-temporal em `AgentMemory` (migration dupla `valid_from/valid_to` + invalidação no ingest) — KG tem `valid_from/to` mas **0/7204** preenchidos | C0 | `AGENT_MEMORY_VIGILANCE` | ⬜ PENDENTE |
| **C2** | Reflexão agendada (sleep-time): gera insight de nível superior citando evidência (Generative Agents) | C0, E | `AGENT_MEMORY_VIGILANCE` | ⬜ PENDENTE |

**GATE-MEM:** Fase 0 (AgingBench) decide retrieval vs utilization; depois G-F4/G-F6 (recuperação) + G-F1 Fase 1 (canal) em shadow/canário ≥1 semana; **métrica primária = reincidência por `error_signature` antes/depois da promoção (Marcus ~9 → ≤2)**.

## BASELINE CONHECIDO (herdado da main — NÃO causado pela Onda 0)
- ~~**2× falha em `tests/agente/sdk/test_pending_questions.py`**~~ ✅ **RESOLVIDO 2026-05-31 (Tarefa 2a, `b31c18760`)**: causa real diagnosticada — NÃO era o `call_soon_threadsafe` ausente (já existia); era `_signal_async_event` SEMPRE agendar via `call_soon_threadsafe` mesmo quando chamado de DENTRO da thread do loop dono (testes chamam submit/cancel no próprio loop e checam `is_set()` síncrono, sem `await` → callback agendado não rodou). Fix: quando `asyncio.get_running_loop() is pq._loop`, `set()` direto (imediato); cross-thread (Flask/subscriber) mantém `call_soon_threadsafe` (produção inalterada). **`tests/agente/sdk/` agora 196 passed / 0 failed.** Testado no Teams (sem impacto).

## NÃO VERIFICADO (auditar antes da onda correspondente — Blueprint §honestidade)
- Propagação de `Task` a subprocesso de subagente no SDK 0.2.87 → decide risco de B (Onda 2).
- Volume/custo Voyage no bootstrap D2 + judge online em turnos longos Odoo → dimensiona INFRA (workers/sampling), NÃO o valor.
- Conteúdo de `tool_skill_mapper` (service L5) → possível reuso p/ Skill-RAG (Onda 4).
- Campos exatos de agenda/incoterm em `carteira_principal`/`agendamentos_entrega` → D1 valida contra os 298 schemas.

## DECISÕES DE DESIGN (registradas — não re-decidir)
- **2026-05-30 — agent_step granularidade**: TURNO (1 par user→assistant). Chave UNIQUE `step_uid='{session_id}:{turn_seq}'` (`turn_seq` = nº msgs role=user na sessão). Idempotente p/ retry da defesa (R10). Join com `agent_session_costs` por `session_id`+janela temporal (NÃO por igualdade de message_id — granularidades distintas). Aprovado por Rafael. Plano: `docs/superpowers/plans/2026-05-30-onda-0-fundacao.md`.

## BLOQUEIOS ATIVOS
- _(nenhum — S0b/S0c desbloqueadas)_ — **RESOLVIDO 2026-05-31**: Rafael commitou `skills_whitelist.py` na main (commit `18e57919c`, Solução B allow→deny-list). `feat/agente-evolucao` mergeou main (merge limpo, exit 0), trazendo `skills_whitelist.py` (3 grupos + união) + `client.py` lendo-o. S0b consolidou SPED nele; S0c segue.
- **GATE-0 (fora do meu alcance)**: exige `agent_step` gravando em PROD ≥48h (web E teams) → depende de PUSH/DEPLOY do Rafael. Onda 1 NÃO inicia antes (protocolo §COMO USAR). Implementação Onda 0 fica code-complete na branch, sem push.
- **GATE-A4 ATIVAÇÃO (gate humano, NÃO automático)**: antes de ligar `AGENT_OPERATIONAL_DIRECTIVES=ON` em PROD, a coluna `agent_memories.directive_status` DEVE existir (rodar `scripts/migrations/2026_06_01_agent_memories_directive_status.py` no Render Shell OU wirar no `build.sh` junto ao bloco A3 26d ao mergear na main). Senão o builder cai em `UndefinedColumn` (engolido pelo `except`) e **desliga TODAS as diretrizes silenciosamente** (inclusive legado). A promoção `shadow→ativa` é revisão MANUAL das candidatas. `AGENT_DIRECTIVE_PROMOTION=ON` só produz candidatas úteis quando `USE_AGENT_PLANNER` gera PlanState + `AGENT_STEP_JUDGE` acumula judge signal (senão o batch ABSTÉM = no-op seguro).

## LOG DE EXECUÇÃO (append-only — 1 linha por item concluído)
- 2026-05-30 — Onda 0 planejada (plano writing-plans) + design gate da chave resolvido. S0a liberado para Task 1.
- 2026-05-31 — Task 1 (S0a model `AgentStep` + migration dupla) ✅ commit `c13fb31c4`. TDD 3/3 + baseline; spec review ✅ + code quality ✅ (4 melhorias aplicadas); migration local aplicada. Wiring (Task 2) em andamento.
- 2026-05-31 — Task 2 (S0a wiring no PRIMARY + integração) ✅ commit `8287406fa`. 2 testes integração + 21 baseline; spec ✅ + code quality ✅ (guard `if user_message:` de simetria aplicado). **S0a COMPLETO** — `agent_step` grava 1 linha/turno no PRIMARY (web). Pendente: wiring Teams (sub-tarefa S0a-teams, INV-3) + GATE-0 (validação PROD 48h). Próximo: Task 3 (S0b deny-list).
- 2026-05-31 — **DESBLOQUEIO**: Rafael commitou `skills_whitelist.py` (`18e57919c`). Merge main→`feat/agente-evolucao` LIMPO (trouxe skills_whitelist + client.py + BUG-1/2/DOC-1 das quick-wins, sem conflito com AgentStep).
- 2026-05-31 — Task 3 (S0b deny-list fonte única) ✅ commit `f3f6227eb`. `SKILLS_SPED_RESERVED` em `skills_whitelist.py` somado à união; `settings.SPED_SKILLS_RESERVED` re-exporta (retrocompat, 12 testes SPED verdes); `client.py` exclui via `SKILLS_DELEGADAS_SUBAGENTE` (1 fonte). 4 testes novos; baseline 337→341 verdes. Verificado por mim: diff no escopo, sem import circular, falhas restantes (2× `pending_questions`) são PRÉ-EXISTENTES (falham em isolamento, arquivo idêntico pai↔HEAD, S0b não tocou) → triar separado no fechamento. Próximo: Task 4 (S0c registry).
- 2026-05-31 — S0a-teams (wiring agent_step canal Teams, INV-3) ✅ commit `dbe0e8700`. Helper `_gravar_agent_step_teams` (best-effort, idempotente) chamado nos 2 pontos de persistência do Teams: PRIMÁRIO (antes de `_commit_with_retry`, services.py:440) + FALLBACK pós-SSL-drop (antes de `db.session.commit()`, services.py:467). user_id FK via Rafael(1) no teste. 4 testes teams; baseline 345→349. Verificado por mim: call sites nos lugares certos, R1-R8 intactos. **GATE-0 agora cobre web E teams.**
- 2026-05-31 — Task 4 (S0c Capability Registry descritivo) ✅ commit `b3a89f97e`. `capability_registry.py` (`SkillEntry`/`SkillBinding`/`CapabilityRegistry` frozen + `build_registry()` + CLI de auditoria `__main__`); flag `USE_CAPABILITY_REGISTRY` OFF. Auditoria CLI (verdade-base por mim): 50 skills, 116 bindings, 17 agentes, `consultando-sql`=11 agentes (N:M comprovado), 25 skills no principal. 4 testes; baseline 341→345. Discrepância 11 vs 13 explicada (2 agentes citam no corpo, não no campo `skills:`). Próximo: S0a-teams (wiring Teams) + fechamento.
- 2026-05-31 — **ONDA 1 planejada** (`docs/superpowers/plans/2026-05-31-onda-1-quality-spine.md`) APÓS auditoria de premissas (recon `/tmp/subagent-findings/onda1-recon.md`). Escopos CORRIGIDOS vs blueprint: **D0** reduzido ao leak `:E/:A` (confirmado `knowledge_graph_service.py:396-405`); `entity_key=0` por corrida = premissa NÃO-confirmada (é guard de nome-vazio) → DIFERIDO p/ análise de dados PROD. **D0.5** já implementado (`query_graph_memories:797` + escrita empresa) → vira teste de regressão. **E1** NÃO ressuscita `_adjust_importance_for_corrections` (deletada por dead-code) → captura `detect_frustration` score + 👍👎 em `agent_step.outcome_signal` (novo `AgentStep.update_outcome`). **E2/A1** clona `subagent_validator` (esqueleto ATIVO); âncora `operacao_odoo_auditoria` existe mas `USE_ODOO_AUDIT_HOOK` OFF (judge degrada sem ela). Pré-build atrás de flags OFF (decisão Rafael 2026-05-31). Iniciando Task 1 (D0+flags).
- 2026-05-31 — **ONDA 1 CODE-COMPLETE + revisada**: D0 (`fb2ecd77b`), D0.5 (`03d0601b9`), E1 (`4e3de61f8`), E2/A1 (`f06ee60fc`). **Code-review adversarial Onda 1** (`/tmp/subagent-findings/review-onda1.md`): 0 inválidos; **HIGH-1** (`e8afb153a`) sufixo confiança `:alta/:media/:baixa` vazava no destino de RELACOES (mesma família D0) — corrigido + teste; **CRITICAL-1** (`de0e27158`) `step_judge` fazia flush sem `commit` no job RQ → veredito se perderia em PROD (teste mascarava via sessão de teste compartilhada) — corrigido + teste spy-passthrough + cleanup de órfãos. Demais invariantes (flag-OFF=zero write, INV-6 best-effort, SAVEPOINT, step_uid consistente, timezone, shadow) confirmadas OK. Suíte agente+teams: **372 passed / 2 failed** (baseline pending_questions). Tudo flag-OFF. **GATE-1 (deploy+shadow ≥1sem) pendente do Rafael.** Próximo: Onda 2 (planejador).
- 2026-05-31 — **ONDA 2 planejada** (`docs/superpowers/plans/2026-05-31-onda-2-planejador.md`) após recon/auditoria (`/tmp/subagent-findings/onda2-recon.md`). **Premissa crítica resolvida**: subagentes NÃO têm `Task` (sem recursão) → verifier adversarial (B2) = JOB RQ, não subagente spawnado. **Ordenação cross-onda descoberta**: B-TRIAGE + B2-domain dependem de D2 (ontologia, Onda 3) → DIFERIDOS; buildáveis agora: B1, B2-arith, B2-adv, B3. `escalated_to_human` é de `AgentInvocationMetric` (morta). Iniciando B1 (PlanState).
- 2026-05-31 — **B-TRIAGE + B2-domain + code-review pós-D2** ✅. B-TRIAGE (`561ce71cd`), B2-domain (`cd4f9b893`). Code-review consolidado (D2/D4/B-TRIAGE/B2-domain, `/tmp/subagent-findings/review-posd2.md`): 0 CRITICAL; **HIGH-1** (bootstrap inflava `mention_count` em re-run → `_upsert_entity(increment_mentions=False)`), **HIGH-2** (teste zero-voyage era teatro → assert estrutural por regex de import), **HIGH-3** (helper morto) + nits — todos corrigidos `bea3203c9`. SQL parametrizado/sem-injeção confirmado; flag-OFF/shadow/read-only OK. **483 passed / 2 failed**. **ONDA 2 = 6 itens COMPLETOS.** Próximo: D3.
- 2026-05-31 — **ONDA 3 planejada** (`docs/superpowers/plans/2026-05-31-onda-3-flywheel-ontologia.md`) após recon D2 (`/tmp/subagent-findings/d2-recon.md`). Tabelas-mestre corretas: produto=`cadastro_palletizacao`, transportadora=`transportadoras`, cliente=`carteira_principal`/`contas_a_receber` (cnpj raiz 8d). `entity_indexer` atual é o ERRADO (financial_entity_embeddings, não KG). Tipos cliente/produto/transportadora já válidos; `_upsert_entity(user_id=0)` idempotente; Voyage trivial (<$0.01). **GAP CRÍTICO não-no-blueprint**: nós canônicos sem link de memória NÃO são achados pelo HOP-1 de `query_graph_memories` → **resolução: read path = tool `query_ontology` (D4), não HOP-1**; D2 bootstrapa substrato, D4 consome. D2+D4 destravam B-TRIAGE+B2-domain. Iniciando D2.
- 2026-05-31 — **ONDA 2 (subconjunto) CODE-COMPLETE + revisada**: B1 PlanState (`286134082`), B2 verifiers arith+adv (`9691d9e62`), B3 replan+escalate (`7ea589f65`). Code-review Onda 2 (`/tmp/subagent-findings/review-onda2.md`): 0 CRITICAL; H1+I1 corrigidos (`31aa9496c`); wiring B1 end-to-end (formato SSE) confirmado OK, jobs RQ commitam, flag-OFF=zero write, 18 testes B1 intactos. **425 passed / 2 failed**. B-TRIAGE + B2-domain DIFERIDOS pós-D2. Próximo: D2 (bootstrap ontologia, Onda 3).
- 2026-05-31 — **FECHAMENTO ONDA 0**: limpeza de imports (`b73739108`) + **2 code-reviewers adversariais** (lente correção/invariantes + lente qualidade/segurança). Veredito: **0 CRITICAL**; invariantes INV-1/INV-3/INV-6, timezone, SAVEPOINT, idempotência, migration, `outcome_effective_count` sem colisão → **todas PASSAM**. 2 achados MED corrigidos (`8fc20169f`): (A) guard do `agent_step` Teams alinhado ao web (captura turno mesmo sem texto final → dataset consistente entre canais); (M1) `SKILLS_DELEGADAS_SUBAGENTE` virou `frozenset`. 1 achado (db.JSON vs JSONB) é convenção do projeto → NÃO alterado, anotado p/ Onda 1 se `outcome_signal` precisar GIN. Suíte final: **349 passed / 2 failed** (as 2 = baseline pending_questions herdado da main). **ONDA 0 CODE-COMPLETE na branch.** Falta só GATE-0 (deploy PROD ≥48h — ação do Rafael).
- 2026-05-31 — **WIRING Tarefa 1 / E2-enqueuer** ✅ CODE-COMPLETE (`918d7e7af`, base `ec61021bb`). Subagent-driven: implementer TDD → spec-review ✅ → code-review adversarial. `enqueue_pending_judges` novo em `workers/step_judge.py` (gate `USE_AGENT_STEP_JUDGE` lazy, janela `created_at` indexada 6h + cap 50, filtro Python `'judge' not in outcome_signal` — evita gotcha `?`/psycopg2, `job_id` RQ-safe, best-effort INV-6). **Módulo 29** em `app/scheduler/sincronizacao_incremental_definitiva.py` (espelha módulo 28: por-ciclo 30min SEM hour-guard, try/except isolado, fora de `modulos_sync` = report-only). Fila RQ nova `agent_judge` LEVE (prioridade mínima antes de `default`) nos 3 arquivos (`worker_render.py`/`start_worker_render.sh`/`worker_atacadao.py`); `FILAS_PESADAS` intacto. Decisões do Rafael: fila LEVE + cadência por-ciclo. **Code-review pegou CRITICAL-C1** (`job_id='judge-step:{step_uid}'` continha `:` → RQ 2.6.1 `Job.set_id` levantava ValueError → feature inerte quando ligada; MagicMock mascarou nos testes) → fix `:`→`-` + regression test que falha contra o código antigo; **I1** (prioridade da fila em PROD estava alta/inconsistente) + **I2** (docstring "dedup" enganoso — RQ 2.6.1 não tem `unique=True`) corrigidos. Re-review ✅ (validado empiricamente vs Redis real). 18 testes `test_step_judge.py` (+1 C1), 2 falhas = baseline `pending_questions`. Flag OFF, sem push. **GATE-2 (deploy + shadow ≥1sem gravando vereditos) pendente do Rafael.** Próximo: Super-loop do planejador (B-TRIAGE+B2+B3).
- 2026-05-31 — **WIRING Tarefa 2 / Super-loop (shadow)** ✅ CODE-COMPLETE. Subagent-driven (implementer TDD + spec/code-review por sub-task + minha verificação). **2a** (`b31c18760`): fix `_signal_async_event` (set direto na thread do loop dono) → **baseline `pending_questions` 2 falhas → 0** (`tests/agente/sdk/` 196 passed); code-review threading ✅ 0 issues; testado Teams (inalterado). **2b** (`b8e46f8f0`+guard `15b681a8e`): B2 verify shadow — job RQ `verify_step_shadow` roda os 3 verifiers (adversarial+arithmetic+domain) → `outcome_signal['verify']` combinado; varredor `enqueue_pending_verifies` + **módulo 30** D8 (gate `AGENT_VERIFY`, fila `agent_judge`). Lição C1 carregada (job_id `:`→`-`). Code-review ✅ (1 Minor corrigido: guard `if not verify` p/ permitir retry). **2c** (`edf72cf7f`): B-TRIAGE shadow — job RQ `triage_step_shadow` roda `triage_meta` no meta do turno → `outcome_signal['triage']`; varredor `enqueue_pending_triages` + **módulo 31** D8 (gate `AGENT_PLANNER`). Code-review ✅ (mapeamento turn_seq→user msg exato por construção; merge preserva judge/verify). **B3 (replan/escalate) ADIADO COM PREMISSA** (super-loop inline com steps=subagentes/`agent_id` — `marcar_escalonamento` escreve em AgentInvocationMetric, incompatível com PlanState-Task* atual; registrado aqui + memória `b3-escalate-adiado-premissa`). 49 testes workers verdes. 3 sinais (judge/verify/triage) coexistem em `outcome_signal`. Tudo flag-OFF, sem push. **GATE-2 (deploy+shadow) pendente do Rafael.** Próximo: A3-invoke (eval real) → A4-batch.
- 2026-05-31 — **WIRING Tarefa 3 / A3-invoke FASE 1** ✅ CODE-COMPLETE (flag-OFF, verificada por MOCK — zero API). Precedido de **SPIKE** (decisão Rafael): CLI 2.1.159 tem `--agent` → invoke = `claude -p --agent <nome> --permission-mode bypassPermissions`; subagente recebe skills reais (consultando-sql) + Bash; golden cases são majoritariamente regra (DB importa pouco). **3a** (`a3b293be1`+`d9a3d81b6`): tabela `agent_eval_scores` (migration dupla APLICADA local) + model `AgentEvalScore` (`insert_score`/`get_baseline_score`) espelha AgentInvocationMetric; code-review ✅ (Important: get_baseline ANTES de insert — cravado no 3b; Minor tie-break `id.desc()` corrigido). **3b** (`1e00d1ff1`+`9042023bb`): `build_subprocess_invoke_fn` (subprocess sem shell=True, user_input último arg) + job RQ `run_eval_batch` (fila NOVA `agent_eval` **PESADA** — eval 20-50min fora do Worker 0 interativo; baseline ANTES de insert; commit explícito; best-effort) + `enqueue_eval_batch` + CLI `--agent` p/ Fase 2; módulo 28 troca inline→enqueue (report-only, fora de `modulos_sync`). Code-review ✅ (2 Important: I1 timeout 120→600s anti-falso-positivo + M1 git_sha cwd corrigidos; I2 = nota operacional Fase 2). 46 testes verdes, 27 eval_gate intactos. **FASE 2 (run real supervisionado + baseline) pendente do Rafael** (`python -m app.agente.workers.eval_runner --agent <nome>`). Próximo: A4-batch (promoção de diretriz, fecha o flywheel).
- 2026-06-01 — **A4-batch V1 OFFLINE CODE-COMPLETE + revisada** (subagent-driven). Releitura anti-drift (PROMPT_A4 + eixos/crítica A-flywheel): "offline vs A/B" JÁ decidido pela spec+PROD → **V1 offline** (A/B=V2, depende de A1/judge — 0 em PROD); a Opção "log-only" que cogitei foi descartada por NÃO estar na doc (PROMPT_A4:56 lista `_persist_directive real` no escopo). 4 commits: migration dupla `directive_status` (`7c0500f76`, coluna NOVA, NÃO toca effective_count) → builder filtra `IN(NULL,'ativa')` alavanca (`b8db8c560`) → `_persist_directive` real shadow idempotente formato-orgânico (`cf0d920cc`) → `run_directive_promotion_batch`+módulo D8 32 INLINE (`e122e43c3`) + cleanup (`ddb9aa877`). Cadência: 4 implementers TDD + spec-review + code-review/task; **review holístico final SHIP-READY (7/7 invariantes HOLD, 0 blocker de código)**. **677 passed** (baseline 668 +9 A4); 0 regressão. Dupla segurança (shadow nunca injetada + flag OFF). R9 DOMINA. ⚠️ Gotcha ativação: rodar migration `directive_status` ANTES de `AGENT_OPERATIONAL_DIRECTIVES`=ON (senão UndefinedColumn desliga diretrizes); wirar build.sh no merge da main. **FLYWHEEL DISTILL→DEPLOY CONSTRUÍDO (flag-OFF).** Pendente: PUSH/DEPLOY + GATEs do Rafael (PlanStates+judge+baseline acumularem em PROD para o batch sair do no-op).
- 2026-06-01 — **Verificação PROD pós-flags (Rafael dormindo)**: web `dep-d8egop` + worker `dep-d8egoq` AMBOS `live`; app boot OK (serve requests, D8 cicla); shadow GRAVANDO vereditos (1 agent_step ganhou judge=1+verify=1; triage pendente). Erro recorrente `/e/20/gkpj` (~30min) é **PRÉ-EXISTENTE** (já no deploy `04aeae25` antes das flags) — NÃO causado pela A3/flags; não revertido (só diagnosticado). Gotcha doc: queries `outcome_signal ? 'judge'` falham (coluna é `json`) → usar `::jsonb`.
- 2026-06-01 — **A4 V1 DEPLOYED + LIVE em PROD**: merge `7fef3778c` → push → auto-deploy. **1º deploy web deu timeout de health-check** (`update_failed`; app subiu saudável — gunicorns Listening 5001+5002, sem crash/OOM; worker MESMO commit subiu OK; causa = porta 10000/nginx vs deadline do Render, **NÃO** código A4). **Retry (`dep-d8enl64`) pegou a janela → LIVE** (12:47). Migration 26e rodou (coluna `directive_status` existe). Batch módulo 32 roda limpo: `[directive_promotion] candidatos=0 promovidos=0 abstencoes=0 rejeitados=0` (no-op, 0 PlanStates). **DESCOBERTA: `AGENT_OPERATIONAL_DIRECTIVES` já estava ON em PROD** (injeta 5 legado; comportamento existente — eu assumira OFF: erro de premissa, devia ter VERIFICADO, não assumido pelo default). A4 transparente (filtro exclui shadow; `directives=5 chars=3220` idêntico antes/depois). **build.sh lento (58 `create_app()`, ~15-20min) = Rafael trata em sessão separada** (não toquei; diagnóstico em memória `deploy-web-build-lento`). Ponteiros: `app/agente/CLAUDE.md`→`EXECUCAO.md`; plano `docs/superpowers/plans/2026-06-01-a4-promocao-diretriz.md`. **PRÓXIMO: VALIDAÇÃO de funcionamento + medição de resultados (Ondas 0-4) — ver `docs/blueprint-agente/PROMPT_PROXIMA_SESSAO_VALIDACAO.md`.**
- 2026-06-01 (tarde) — **VALIDAÇÃO + MEDIÇÃO (READ-ONLY) executada** (ver CHECKPOINT acima). 12/13 flags VERIFICADAS por dado/log (não assumidas). Maquinaria PRODUZ DADO (S0a/E1/E2/B2/B-TRIAGE/R9-hook/D2/D4/Onda4 ✅, web; teams=0 não-exercido). **Resultado NÃO mensurável** (janela ~14h preliminar, judge enviesado [sem-tool=failure 88%], adversarial refuta judge em 73%, 0 calibração humana, R9 anti-gaming n=0). **Gargalos**: 🔴 B1 PlanState=0 (Task usado 0× → flywheel/A4 no-op), A3 baseline=0 (Fase 2 local falhou ao persistir, Sentry X7 transação). D3 proveniência=0. Sentry PROD limpo do blueprint (X7/X5 são DEV local NACOM052). **Falso-alarme evitado**: "S0a parou 3h" era offset UTC×BRT-naive (S0a saudável). Decisões GATED p/ Rafael no checkpoint.
- 2026-06-01 (tarde) — **2 CORREÇÕES pós-medição (TDD, autorizadas pelo Rafael)**:
  (1) **Viés do judge E2** (`workers/step_judge.py`): o judge era CEGO ao conteúdo (só via `tools_used`+Odoo) → punia turno informativo sem tool como `failure` (medido: sem-tool=failure 88%). Fix: `_build_judge_prompt`/`_judge_core` agora recebem PERGUNTA+RESPOSTA do turno (reusa `triage_shadow._extract_user_message_text` + `plan_verifier._extract_assistant_response_text`); `JUDGE_SYSTEM_PROMPT` reescrita ("turno sem ferramenta NÃO é falha automática; avalie a resposta vs pergunta"); **R9 (FALHA_ODOO→≤35) preservada**. 4 testes TDD (RED→GREEN, 22 no arquivo). **Smoke A/B com Haiku REAL**: mesmo turno informativo sem tool → ANTIGO `failure`/0 vs NOVO `success`/85 (com raciocínio "não exigia ferramenta"). Destrava confiar no sinal + **A4 V2** (aprender do judge, não de PlanState — judge signal NÃO é 0, são 51 vereditos).
  (2) **Bug X7 eval_runner** (`workers/eval_runner.py`): A3 Fase 2 local falhava ao persistir → `agent_eval_scores` vazio. Root cause (provado na fonte SQLAlchemy `engine/base.py:663`): o disconnect pós-invokes longos surge no commit como `PendingRollbackError` (code `8s2b` = X7 exato), IRMÃ de `OperationalError` → fora do `except OperationalError` da retry → caía no except genérico ("commit falhou") → `scores={}`. Fix: catch `(OperationalError, PendingRollbackError)`. 1 teste TDD (RED→GREEN reproduz X7; 26 no arquivo). **79 workers green** (ambas correções). Pendente: re-rodar A3 Fase 2 (`eval_runner --agent analista-carteira`) + inspecionar `cases[].evidence` (caveat I2).
- 2026-06-01 (tarde) — **DIAGNÓSTICO B1 (gargalo do flywheel) — é COMPORTAMENTO, não bug**: verificado que `TaskCreate/Update/List` ESTÃO em `tools_enabled` (settings.py:66-69), o prompt MANDA usar (`<task_management>`+`<delegation_pattern>`), e o B1 captura certo (`chat.py`→`plan_state.py`). Mesmo assim 0 PlanStates: o agente web é single-shot (TaskCreate/Update=0 em 67 turnos) e não decompõe trabalho trivial — corretamente. **"O que é melhor" (decisão p/ Rafael)**: (A) reforçar prompt p/ envolver delegações a subagente em TaskCreate (gera PlanStates do trabalho real + "efeito Claude Code") OU (B) desacoplar A4 do PlanState e aprender do JUDGE signal (A4 V2, destravado pelo fix do judge). B é a correção de fundo.
- 2026-06-01 (tarde) — **RAFAEL ESCOLHEU OPÇÃO B + corrigir ambiguidade do prompt (implementado, TDD)**:
  (a) **Prompt** (`system_prompt.md` `<delegation_pattern>`): removida a contradição (`<task_management>` dizia "não p/ trivial", `<delegation_pattern>` dizia "sempre criar task p/ delegação"). Agora: **delegação ÚNICA não precisa de TaskCreate** (o spawn já emite task_started/progress/subagent_summary na UI); TaskCreate **só** em orquestração 2+ delegações/passos. (Risco: muda prompt LIVE — mudança cirúrgica.)
  (b) **A4 V2 / Opção B** (`directive_promotion_service.py`): nova fonte de candidata `propose_directive_from_judge_session` (sessão de ALTA QUALIDADE validada pelo judge: ≥2 passos julgados, 0 `failure`, média ≥0.7) — **independente de PlanState**, fiel à spec §2.3 (critério = quality_signal). Wirada como 2ª fonte em `run_directive_promotion_batch` (dedup por session_id; MESMO gate `evaluate_and_promote`: R9 anti-gaming + A3 report-only). Candidatas → `directive_status='shadow'` → **NUNCA injetadas** (dupla segurança intacta). TDD: 7 testes (6 pura + 1 batch judge), 3 batch existentes atualizados; **36 directive + 219 services/workers/sdk green**. **Evidência PROD**: 0 sessões qualificam HOJE (6 sessões ≥2 julgados, TODAS com falhas, média 33-51 < 70) — MAS o "0" deixou de ser **estrutural** (PlanState=Task nunca emitido) e virou **de dados** (janela ~14h só de sessões Odoo que falharam) → resolve sozinho com volume + sessões limpas + o judge corrigido (turnos informativos antes mal-pontuados viram success). **NÃO commitado/deployado** (branch `manutencao/semanal-2026-06-01`).
