<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/blueprint-agente/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Runbook de Validação — Evolução do Agente

> **Papel:** Runbook de Validação — Evolução do Agente.

## Indice

- [Princípio](#princípio)
  - [As 3 classes de testabilidade](#as-3-classes-de-testabilidade)
- [Tabela-Resumo (15 features)](#tabela-resumo-15-features)
- [Sequência de Ativação Recomendada](#sequência-de-ativação-recomendada)
- [Receitas por Feature](#receitas-por-feature)
  - [Classe A_local](#classe-a_local)
  - [S0a — tabela `agent_step` *(sem flag)*](#s0a-tabela-agent_step-sem-flag)
  - [E1 — captura de frustração (`AGENT_QUALITY_SPINE`)](#e1-captura-de-frustração-agent_quality_spine)
  - [E2 — step_judge (PRM) (`AGENT_STEP_JUDGE`)](#e2-step_judge-prm-agent_step_judge)
  - [D2 — Bootstrap de ontologia canônica (`AGENT_ONTOLOGY`)](#d2-bootstrap-de-ontologia-canônica-agent_ontology)
  - [D4 — Tool MCP `query_ontology` (`AGENT_ONTOLOGY`)](#d4-tool-mcp-query_ontology-agent_ontology)
  - [D3 — Proveniência bi-temporal (`AGENT_ONTOLOGY`)](#d3-proveniência-bi-temporal-agent_ontology)
  - [B1 — PlanState durável (`AGENT_PLANNER`)](#b1-planstate-durável-agent_planner)
  - [B2-arith+adv — `verify_arithmetic` + `verify_plan_adversarial` (`AGENT_VERIFY`)](#b2-arithadv-verify_arithmetic-verify_plan_adversarial-agent_verify)
  - [B3 — replan + budget + escalate (`AGENT_PLANNER`)](#b3-replan-budget-escalate-agent_planner)
  - [B-TRIAGE — `triage_meta` (`AGENT_PLANNER`)](#b-triage-triage_meta-agent_planner)
  - [B2-domain — `verify_domain` (`AGENT_VERIFY`)](#b2-domain-verify_domain-agent_verify)
  - [A3 — Eval Runner (`AGENT_EVAL_GATE`)](#a3-eval-runner-agent_eval_gate)
  - [A4 — Promoção automática de diretriz (`AGENT_DIRECTIVE_PROMOTION`)](#a4-promoção-automática-de-diretriz-agent_directive_promotion)
  - [F4/F5 — Skill Hints Advisory (`AGENT_SKILL_RAG`)](#f4f5-skill-hints-advisory-agent_skill_rag)
  - [D5 — World Model Injection (`AGENT_WORLD_MODEL_INJECT`)](#d5-world-model-injection-agent_world_model_inject)
- [Apêndice — Cheatsheet SQL de Inspeção](#apêndice-cheatsheet-sql-de-inspeção)
- [Nota Final](#nota-final)
  - [Falhas pré-existentes (baseline da main)](#falhas-pré-existentes-baseline-da-main)
  - [Tudo está flag-OFF — validar não muda PROD](#tudo-está-flag-off-validar-não-muda-prod)

**Como validar cada feature da evolução do agente.**

---

## Princípio

Os testes unitários já provam o **código** (lógica, invariantes, edge cases). Este runbook é validação **comportamental**: garante que a feature produz o efeito correto no sistema real, com a flag certa ligada, sem quebrar nada quando desligada.

### As 3 classes de testabilidade

| Classe | Significado | Exemplo de evidência |
|--------|-------------|----------------------|
| **A_local** | Smoke local com flag ON + inspecionar efeito direto. Pode ser rodado antes do deploy. | `pytest` passa; smoke python-c retorna PASS |
| **B_shadow** | Feature só grava dados ou é shadow-only (sem caller ativo). Lógica validada local; efeito real só visível observando o banco pós-deploy. | `SELECT ... FROM agent_sessions WHERE data ? 'plan'` após turno real com flag ON |
| **C_prod** | Precisa PROD + tempo real para manifestar o comportamento (crons, turnos SSE, enqueue RQ). Não há atalho local. | Log `[EVAL_GATE]` no Render após cron D8 rodar com flag ON |

> **Tudo está flag-OFF por default.** Rodar qualquer receita abaixo não altera PROD enquanto as env vars correspondentes não forem ligadas no Render.

---

## Tabela-Resumo (15 features)

| # | Feature | Flag | Classe | Verificada local? |
|---|---------|------|--------|:-----------------:|
| 1 | S0a — tabela `agent_step` grava 1 linha/turno (web + teams) | *(sem flag — schema always-on)* | A_local | ✅ |
| 2 | E1 — captura de frustração + 👍👎 em `agent_step.outcome_signal` | `AGENT_QUALITY_SPINE` | A_local | ✅ |
| 3 | E2 — step_judge (PRM) grava `outcome_signal['judge']`; FALHA_ODOO domina e capa score ≤ 35 | `AGENT_STEP_JUDGE` | A_local | ✅ |
| 4 | D2 — Bootstrap de ontologia canônica (cliente/produto/transportadora) via CLI | `AGENT_ONTOLOGY` | A_local | ✅ |
| 5 | D4 — Tool MCP `query_ontology`: busca direta nos nós canônicos | `AGENT_ONTOLOGY` | A_local | ✅ |
| 6 | D3 — Proveniência bi-temporal nas relações do Knowledge Graph (`source_session_id`, `valid_from`) | `AGENT_ONTOLOGY` | A_local | ✅ |
| 7 | B1 — PlanState durável em `AgentSession.data['plan']` (captura Task* events) | `AGENT_PLANNER` | A_local | ✅ |
| 8 | B2-arith+adv — `verify_arithmetic` + `verify_plan_adversarial` (job RQ) | `AGENT_VERIFY` | A_local | ✅ |
| 9 | B3 — replan + budget + escalate: `mark_step_failed` / `should_escalate` / `steps_to_retry` + `marcar_escalonamento` | `AGENT_PLANNER` | A_local | ✅ |
| 10 | B-TRIAGE — `triage_meta` decompõe meta em steps ancorados na ontologia | `AGENT_PLANNER` | A_local | ✅ |
| 11 | B2-domain — `verify_domain` valida step contra ontologia canônica | `AGENT_VERIFY` | A_local | ✅ |
| 12 | A3 — Eval Runner (golden YAML + Haiku-judge) + gate report-only no módulo 28 do D8 | `AGENT_EVAL_GATE` | A_local | ✅ |
| 13 | A4 — Promoção automática de diretriz shadow (`propose_directive_from_plan` + `evaluate_and_promote`, anti-gaming R9) | `AGENT_DIRECTIVE_PROMOTION` | A_local | ✅ |
| 14 | F4/F5 — Skill Hints Advisory: bloco `<skill_hints priority="advisory">` injetado no hook UserPromptSubmit | `AGENT_SKILL_RAG` | A_local | ✅ |
| 15 | D5 — World Model Injection via ontologia | `AGENT_WORLD_MODEL_INJECT` | A_local | ✅ |

**Todas 15 features verificadas localmente (verified_locally=true).**

---

## Sequência de Ativação Recomendada

A ordem abaixo minimiza risco: primeiro confirma infra (S0a), depois spine de qualidade (E1/E2), depois ontologia (D2/D4/D3), depois planejador shadow (B*), depois flywheel (A3/A4), por último context enrichment (F4/F5/D5).

```
GATE-0:  Deploy + 48h de observação
         └─ Validar: agent_step gravando 1 linha/turno ([S0a](#s0a--tabela-agent_step-sem-flag))
         └─ SQL: SELECT count(*), channel FROM agent_step WHERE created_at > now()-'24h' GROUP BY channel

GATE-1:  AGENT_QUALITY_SPINE=true
         └─ Ativar: [E1](#e1--captura-de-frustração-agent_quality_spine)

GATE-2:  AGENT_STEP_JUDGE=true
         └─ Ativar: [E2](#e2--step_judge-prmr-agent_step_judge) (requer worker RQ rodando)

GATE-3:  AGENT_ONTOLOGY=true
         3a. Bootstrap CLI: python scripts/agente/bootstrap_ontologia.py --dry-run; depois real
             └─ [D2](#d2--bootstrap-de-ontologia-agent_ontology)
         3b. Tool MCP query_ontology exposta ao agente
             └─ [D4](#d4--tool-mcp-query_ontology-agent_ontology)
         3c. Proveniência bi-temporal nas relações
             └─ [D3](#d3--proveniência-bi-temporal-agent_ontology)

GATE-4:  AGENT_PLANNER=true (shadow — grava data['plan'] mas não altera resposta)
         └─ [B1](#b1--planstate-durável-agent_planner)
         └─ [B2-arith+adv](#b2-arithmadv--verify_arithmetic--verify_plan_adversarial-agent_verify) (shadow, sem caller ativo)
         └─ [B3](#b3--replan--budget--escalate-agent_planner)
         └─ [B-TRIAGE](#b-triage--triage_meta-agent_planner) (shadow puro, sem wiring)
         └─ [B2-domain](#b2-domain--verify_domain-agent_verify) (shadow puro)

GATE-5:  AGENT_EVAL_GATE=true (D8 cron, report-only)
         └─ [A3](#a3--eval-runner-agent_eval_gate)

GATE-6:  Flywheel
         └─ [A4](#a4--promoção-automática-de-diretriz-agent_directive_promotion) (AGENT_DIRECTIVE_PROMOTION=true, shadow puro)
         └─ USE_OPERATIONAL_DIRECTIVES=true (se aplicável)

GATE-7:  Context Enrichment
         └─ [F4/F5](#f4f5--skill-hints-advisory-agent_skill_rag) (AGENT_SKILL_RAG=true)
         └─ [D5](#d5--world-model-injection-agent_world_model_inject) (AGENT_WORLD_MODEL_INJECT=true — requer D2+D4 executados antes)
```

---

## Receitas por Feature

### Classe A_local

---

### S0a — tabela `agent_step` *(sem flag)*

**Como exercitar:**
```bash
cd /home/rafaelnascimento/projetos/frete_sistema/.claude/worktrees/agente-evolucao
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate

python -m pytest \
  tests/agente/models/test_agent_step.py \
  tests/agente/routes/test_agent_step_wiring.py \
  tests/teams/test_agent_step_teams_wiring.py \
  -v --tb=short
```

Grupos cobertos: `test_agent_step.py` (3 testes: insert direto, idempotência por `step_uid` UNIQUE, não-poisona sessão via SAVEPOINT); `test_agent_step_wiring.py` (2 testes: wiring web via `_save_messages_to_db`, dedup PRIMARY+DEFESA); `test_agent_step_teams_wiring.py` (4 testes: channel='teams', idempotência, session=None não grava, turno só-tools gera step).

**O que observar:**
```sql
-- Conta linhas gravadas nas últimas 24h
SELECT count(*), channel, model
FROM agent_step
WHERE created_at > now() - interval '24 hours'
GROUP BY channel, model ORDER BY count DESC;

-- Inspecionar os últimos steps (colunas da migration)
SELECT id, step_uid, session_id, user_id, channel, model,
       input_tokens, output_tokens, tools_used,
       outcome_signal, outcome_effective_count, created_at
FROM agent_step
ORDER BY created_at DESC LIMIT 10;

-- Confirmar step_uid no formato "{session_id}:{turn_seq}"
SELECT step_uid,
       split_part(step_uid, ':', 1) AS session_id_part,
       split_part(step_uid, ':', 2)::int AS turn_seq
FROM agent_step ORDER BY created_at DESC LIMIT 5;

-- Joinabilidade com agent_sessions (sem FK, join por session_id)
SELECT s.step_uid, s.channel, s.input_tokens,
       ag.title AS session_title, ag.user_id
FROM agent_step s
JOIN agent_sessions ag ON ag.session_id = s.session_id
ORDER BY s.created_at DESC LIMIT 5;
```

Nos logs: ausência de `"[AGENTE] agent_step nao gravado (best-effort)"` = step gravado com sucesso.

**Critério de PASS:** 9/9 testes passam. Pós-deploy: cada turno real produz exatamente 1 nova linha; `step_uid` = `"{session_id}:{turn_seq}"`; `channel` = `'web'` ou `'teams'`; `tokens` populados; `outcome_signal` = NULL (preenche apenas com `AGENT_QUALITY_SPINE=true`); falha hipotética de INSERT não quebra o stream (log best-effort).

**Flag-OFF (zero efeito):** `outcome_signal` permanece NULL enquanto `AGENT_QUALITY_SPINE=false`:
```sql
SELECT count(*) FROM agent_step WHERE outcome_signal IS NOT NULL;
-- Deve retornar 0 enquanto AGENT_QUALITY_SPINE=false
```

**Status de verificação local:** ✅ `9 passed in 8.95s`. Testes exercitam diretamente `_save_messages_to_db` (web) e `_gravar_agent_step_teams` (teams) com `app_context` real + rollback. O logging error no teardown (`I/O operation on closed file` de `shutdown_state.py`) é artefato benigno de teardown do pytest.

---

### E1 — captura de frustração (`AGENT_QUALITY_SPINE`)

**Como exercitar:**
```bash
python -m pytest tests/agente/models/test_agent_step_outcome.py \
                 tests/agente/routes/test_agent_step_wiring.py -v
```

Smoke direto das funções E1 (sem Flask, sem DB):
```bash
AGENT_QUALITY_SPINE=true python -c "
from app.agente.services.sentiment_detector import (
    enrich_message_if_frustrated, get_last_frustration_score, _session_scores
)
sid = 'smoke-e1-manual'
enrich_message_if_frustrated('nao funciona', {}, session_id=sid)
score = get_last_frustration_score(sid)
assert score is not None and score >= 3, f'FALHA: score={score}'
print('PASS frustration_score capturado no cache:', score)
"
```

**O que observar:**
```sql
-- Após turno com mensagem de frustração (com flag ON)
SELECT step_uid, session_id, outcome_signal, outcome_effective_count, created_at
FROM agent_step
WHERE session_id = '<uuid-da-sessao>'
ORDER BY created_at DESC LIMIT 5;
-- PASS: outcome_signal = {"frustration_score": 4}

-- Após POST /api/feedback (merge aditivo)
-- PASS: outcome_signal = {"frustration_score": 4, "feedback": "negative", "error_category": "wrong_answer"}

-- Flag OFF: outcome_signal deve ser NULL
SELECT outcome_signal FROM agent_step WHERE session_id = '<uuid>' ORDER BY created_at DESC LIMIT 1;
```

**Critério de PASS:** 6/6 testes passam. Mensagem de frustração (score ≥ 3) → `outcome_signal` contém `{"frustration_score": N}`. POST `/api/feedback` → chave `"feedback"` mergeada (não sobrescreve `frustration_score`). Mensagem não-frustrada → `outcome_signal` NULL ou sem `frustration_score`.

**Flag-OFF (zero efeito):** Com `AGENT_QUALITY_SPINE=false`: bloco `if USE_AGENT_QUALITY_SPINE:` em `chat.py:1848` e `feedback.py:68` não executa; `outcome_signal` permanece NULL; feedback persiste apenas em `AgentSession.data['feedbacks']` como antes.

**Status de verificação local:** ✅ `6 passed in 6.91s`. Smoke das funções E1 (6 checks OK). O link feedback→step via HTTP não foi exercitado (requer turno real de SDK); coberto indiretamente pelo teste `test_grava_um_step_joinavel`.

---

### E2 — step_judge (PRM) (`AGENT_STEP_JUDGE`)

**Como exercitar:**

Smoke puro sem DB (mock de Haiku):
```bash
python -c "
from unittest.mock import patch
from app.agente.workers.step_judge import _judge_core

class FakeStep:
    tools_used = ['operando-picking-odoo']
    outcome_signal = None
    session_id = 'smoke-001'

class FakeOp:
    def __init__(self, st):
        self.status = st
        self.modelo_odoo = 'stock.picking'
        self.metodo_odoo = 'button_validate'

haiku_resp = '{\"score\": 90, \"label\": \"success\", \"componente_culpado\": null, \"evidencia\": \"ok\"}'

with patch('app.agente.workers.step_judge._call_haiku_judge', return_value=haiku_resp):
    # Cenário 1: sem FALHA_ODOO => score Haiku preservado
    v = _judge_core(FakeStep(), [FakeOp('EXECUTADO')])
    assert v['score'] == 90 and v['label'] == 'success'
    print('PASS cenario1 sem-falha:', v)

    # Cenário 2: com FALHA_ODOO => dominância ambiental, score <= 35
    v2 = _judge_core(FakeStep(), [FakeOp('EXECUTADO'), FakeOp('FALHA_ODOO')])
    assert v2['score'] <= 35 and v2['componente_culpado'] == 'odoo' and v2['label'] == 'failure'
    print('PASS cenario2 dominancia-ambiental:', v2)
"
```

Suite completa:
```bash
python -m pytest tests/agente/workers/test_step_judge.py -v
```

**O que observar:**
```sql
SELECT step_uid,
       outcome_signal -> 'judge' AS judge_veredito,
       outcome_signal -> 'judge' ->> 'score' AS score,
       outcome_signal -> 'judge' ->> 'label' AS label,
       outcome_signal -> 'judge' ->> 'componente_culpado' AS culpado,
       outcome_signal -> 'judge' ->> 'evidencia' AS evidencia
FROM agent_step
WHERE step_uid = '<step_uid_alvo>'
  AND outcome_signal ? 'judge';
```

Log do worker RQ: `[step_judge] concluido: step_uid=<uid> score=<N> label=<s>`.

**Critério de PASS:** Cenário sem `FALHA_ODOO`: `outcome_signal['judge']['score']` == valor do Haiku; `label` == `'success'`; `componente_culpado` == null. Cenário com `FALHA_ODOO`: `score` ≤ 35; `componente_culpado` == `'odoo'`; `label` == `'failure'`. `db.session.commit()` chamado após `update_outcome` (CRITICAL-1). Step inexistente → no-op. JSON inválido do Haiku → não grava, não crasha.

**Flag-OFF (zero efeito):** Com `AGENT_STEP_JUDGE=false`, nenhuma fila RQ é enfileirada automaticamente. Nenhum `outcome_signal['judge']` é gravado em PROD sem invocação explícita:
```sql
SELECT count(*) FROM agent_step WHERE outcome_signal ? 'judge';
-- Deve retornar 0 com flag OFF
```

**Status de verificação local:** ✅ `11 passed in 6.54s` (pytest) + smoke puro (3 cenários OK: sem FALHA_ODOO score=90; com FALHA_ODOO score=35, culpado=odoo; parse tolerante score=75).

---

### D2 — Bootstrap de ontologia canônica (`AGENT_ONTOLOGY`)

**Como exercitar:**
```bash
# Passo 0 — Flag OFF bloqueia escrita (smoke negativo)
python scripts/agente/bootstrap_ontologia.py
# Esperado: returncode=1, stderr: "ERROR: Escrita bloqueada. Use --dry-run..."

# Passo 1 — Dry-run (sem flag, sem escrita)
python scripts/agente/bootstrap_ontologia.py --dry-run --limit 5
# Imprime [DRY-RUN] para produto, transportadora, cliente; zero writes

# Passo 2 — Escrita real com flag ON
AGENT_ONTOLOGY=true python scripts/agente/bootstrap_ontologia.py --limit 5

# Passo 3 — Idempotência
AGENT_ONTOLOGY=true python scripts/agente/bootstrap_ontologia.py --limit 5
# Deve retornar mesmo total sem erro (ON CONFLICT uq_user_entity)
```

**O que observar:**
```sql
-- Contagem de nós por tipo inseridos pelo bootstrap
SELECT entity_type, COUNT(*) AS n
FROM agent_memory_entities
WHERE user_id = 0
GROUP BY entity_type ORDER BY entity_type;
-- PASS: linhas para produto, transportadora, cliente com n >= 1

-- Verificar campos-chave (entity_key preenchido; mention_count=1)
SELECT entity_type, entity_name, entity_key, mention_count, user_id
FROM agent_memory_entities
WHERE user_id = 0
ORDER BY entity_type, id LIMIT 15;

-- Idempotência: após segundo run, mention_count NÃO sobe
SELECT entity_type, entity_key, mention_count
FROM agent_memory_entities WHERE user_id = 0 ORDER BY id LIMIT 10;
-- PASS: mention_count permanece 1 após qualquer número de re-runs
```

**Critério de PASS:** Flag OFF → `returncode=1` com "Escrita bloqueada"; zero writes. Dry-run → `returncode=0`, zero writes. Escrita real → `COUNT(*) WHERE user_id=0` ≥ N rows por tipo; `entity_key` preenchido; `mention_count=1`. Segundo run → sem erros; `mention_count` permanece 1 (ON CONFLICT + `increment_mentions=False`). Zero imports de embeddings/Voyage.

**Flag-OFF (zero efeito):** `returncode=1` com guard do CLI. `SELECT COUNT(*) FROM agent_memory_entities WHERE user_id=0` retorna 0 antes de qualquer bootstrap.

**Status de verificação local:** ✅ `24 passed in 0.24s` (testes unitários). Guard flag OFF (returncode=1) confirmado. Dry-run com `--limit 3` verificado. Escrita real em banco local não executada (sandbox); requer validação com SQL de observação após primeiro deploy com `AGENT_ONTOLOGY=true`.

---

### D4 — Tool MCP `query_ontology` (`AGENT_ONTOLOGY`)

**Como exercitar:**
```bash
# Suite de testes (12 testes, DB local real via mocks)
python -m pytest tests/agente/tools/test_query_ontology.py -v

# Smoke: flag ON → server não-None; flag OFF → server None
AGENT_ONTOLOGY=true python -c "
from app.agente.tools.ontology_query_tool import ontology_server
assert ontology_server is not None
print('PASS: ontology_server criado:', type(ontology_server))
"

AGENT_ONTOLOGY=false python -c "
from app.agente.tools.ontology_query_tool import ontology_server
assert ontology_server is None
print('PASS: flag=OFF -> ontology_server=None')
"

# Smoke função núcleo
AGENT_ONTOLOGY=true python -c "
from app.agente.tools.ontology_query_tool import query_ontology_entities
r = query_ontology_entities(user_id=1, key='SMOKE_KEY_NAO_EXISTE_ZZZ')
assert r == [], f'esperado [], obtido {r}'
print('PASS: lista vazia para key inexistente')
r2 = query_ontology_entities(user_id=7, entity_type='cliente', limit=5)
print(f'PASS: union OK, {len(r2)} resultados')
"
```

**O que observar:**

SQL executada internamente (confirmar via log ou EXPLAIN):
```sql
SELECT entity_type, entity_name, entity_key, user_id
FROM agent_memory_entities
WHERE user_id = ANY(:user_ids)     -- ex: ANY(ARRAY[7,0])
  [AND entity_type = :entity_type]
  [AND entity_name ILIKE :name_like]
  [AND entity_key = :entity_key]
ORDER BY mention_count DESC, last_seen_at DESC
LIMIT :limit;
```

Log de registro (em PROD com SDK): `"[AGENT_CLIENT] MCP 'ontology' registrada (1 operacao: query_ontology)"` (flag ON) ou `"[AGENT_CLIENT] MCP 'ontology' SKIP (AGENT_ONTOLOGY=false)."` (flag OFF).

**Critério de PASS:** 12/12 testes passam. `ontology_server` não-None com flag ON; None com flag OFF. `query_ontology_entities` com key inexistente → `[]` sem raise. Entidade canônica (`user_id=0`) aparece em busca por `user_id=7` (union semântico). Entidade de `user_id=7` NÃO aparece em busca por `user_id=0` (isolamento). Dict retornado com exatamente as chaves: `entity_type`, `entity_name`, `entity_key`, `user_id`.

**Flag-OFF (zero efeito):** `ontology_server == None`; `client.py` não registra MCP 'ontology' (condicional `if USE_AGENT_ONTOLOGY` linha 1958); a função `query_ontology_entities` continua disponível programaticamente — apenas a tool MCP fica invisível ao agente.

**Status de verificação local:** ✅ `12 passed in 21.15s`. Flag ON/OFF confirmados. O registro efetivo via `_register_mcp` + tool sendo chamada em turno real requerem SDK ao vivo.

---

### D3 — Proveniência bi-temporal (`AGENT_ONTOLOGY`)

**Como exercitar:**
```bash
python -m pytest tests/agente/services/test_kg_bitemporal.py -v
```

Smoke manual da integração completa (flag ON):
```bash
AGENT_ONTOLOGY=true python -c "
import os; os.environ['AGENT_ONTOLOGY'] = 'true'
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    from app.agente.services.knowledge_graph_service import _upsert_relation
    with db.engine.begin() as conn:
        rows = conn.execute(text('SELECT id FROM agent_memory_entities LIMIT 2')).fetchall()
    if len(rows) < 2:
        print('SKIP: banco local sem entidades suficientes')
    else:
        src, tgt = rows[0][0], rows[1][0]
        with db.engine.begin() as conn:
            _upsert_relation(conn, src, tgt, relation_type='co_occurs', weight=1.0,
                             source_session_id='smoke-test-sess-d3')
            row = conn.execute(text('''
                SELECT source_session_id, valid_from, valid_to
                FROM agent_memory_entity_relations
                WHERE source_entity_id = :s AND target_entity_id = :t
                  AND relation_type = 'co_occurs'
                ORDER BY created_at DESC LIMIT 1
            '''), {'s': src, 't': tgt}).fetchone()
            print('source_session_id:', row[0], 'valid_from:', row[1], 'valid_to:', row[2])
            conn.execute(text('''DELETE FROM agent_memory_entity_relations
                WHERE source_entity_id = :s AND target_entity_id = :t
                  AND relation_type = 'co_occurs' AND source_session_id = 'smoke-test-sess-d3'
            '''), {'s': src, 't': tgt})
"
```

**O que observar:**
```sql
-- Relações com proveniência preenchida
SELECT r.source_session_id, r.source_step_uid, r.valid_from, r.valid_to,
       r.relation_type, r.weight, r.created_at
FROM agent_memory_entity_relations r
WHERE r.source_session_id IS NOT NULL
ORDER BY r.created_at DESC LIMIT 20;

-- Links com proveniência
SELECT l.source_session_id, l.source_step_uid, l.created_at, l.relation_type
FROM agent_memory_entity_links l
WHERE l.source_session_id IS NOT NULL
ORDER BY l.created_at DESC LIMIT 20;

-- % de relações com proveniência (0% com flag OFF, >0% após turno com flag ON)
SELECT
  CASE WHEN source_session_id IS NOT NULL THEN 'com_proveniencia' ELSE 'sem_proveniencia' END,
  COUNT(*)
FROM agent_memory_entity_relations GROUP BY 1;
```

**Critério de PASS:** 8/8 testes passam. `source_session_id` gravado corretamente. `source_session_id` = NULL quando omitido (backward-compat). `valid_from` não NULL; `valid_to` NULL (MVP). ON CONFLICT não sobrescreve a primeira `source_session_id` (política "1ª origem vence"). Migration idempotente (2ª execução → `returncode=0`).

**Flag-OFF (zero efeito):** Com `AGENT_ONTOLOGY=false`, `memory_mcp_tool.py` não chama `get_current_session_id()` (bloco `if USE_AGENT_ONTOLOGY` linhas 1970-1977 não executa); `source_session_id` = NULL em todas as relações criadas:
```sql
SELECT COUNT(*) FROM agent_memory_entity_relations WHERE source_session_id IS NOT NULL;
-- Esperado: 0
```

**Status de verificação local:** ✅ `8 passed in 14.65s`. Colunas confirmadas nas migrations. Guard em `memory_mcp_tool.py` verificado no código. `COALESCE(existing, excluded)` no ON CONFLICT confirma política "1ª origem vence".

---

### B1 — PlanState durável (`AGENT_PLANNER`)

**Como exercitar:**
```bash
# Suite completa (18 testes — PlanState puro + flag toggle + zero-write flag-OFF)
python -m pytest tests/agente/sdk/test_plan_state.py -v
```

Smoke do pipeline completo (flag ON):
```bash
AGENT_PLANNER=true python -c "
import os; os.environ['AGENT_PLANNER'] = 'true'
from app.agente.sdk.plan_state import PlanState

sse_events = [
    {'action': 'created', 'task_id': '1', 'subject': 'consultar NF 12345'},
    {'action': 'updated', 'task_id': '1', 'status': 'completed'},
]
ps = PlanState()
for ev in sse_events:
    ps.apply_task_event(ev)
plan_dict = ps.to_dict()
assert plan_dict['steps']['1']['subject'] == 'consultar NF 12345'
assert plan_dict['steps']['1']['status'] == 'completed'
ps2 = PlanState.from_dict(plan_dict)
assert ps2.to_dict() == plan_dict
print('PASS:', plan_dict)
"
```

**O que observar (pós-deploy com flag ON + turno real com TaskCreate/TaskUpdate):**
```sql
-- Campo data['plan'] gravado em agent_sessions
SELECT session_id, data->'plan' AS plan_json
FROM agent_sessions
WHERE data ? 'plan' AND data->'plan' IS NOT NULL AND data->'plan' != 'null'::jsonb
ORDER BY updated_at DESC LIMIT 5;

-- Para sessão específica
SELECT data->'plan'->'steps' AS plan_steps
FROM agent_sessions WHERE session_id = '<session_id_aqui>';
-- Esperado: {"steps": {"1": {"subject": "consultar NF 12345", "description": "", "status": "completed"}}}
```

Log a monitorar: `[PLAN] data['plan'] gravado: N steps` (chat.py linha ~1917).

**Critério de PASS:** 18/18 testes passam. Smoke retorna `plan_dict` correto e roundtrip idêntico. Com flag ON + turno real: `data['plan']` contém JSON com `'steps'` não-vazio. Com flag OFF: `data['plan']` ausente/NULL após turno.

**Flag-OFF (zero efeito):** Bloco `if USE_AGENT_PLANNER:` em linhas 854, 1686, 1911 de `chat.py` não executa:
```sql
SELECT count(*) FROM agent_sessions WHERE data ? 'plan';
-- Esperado: 0
```

**Status de verificação local:** ✅ `18 passed in 0.23s`. Smoke do PlanState puro verificado. Gravação real em `agent_sessions.data['plan']` requer turno completo com SDK emitindo TaskCreate/TaskUpdate (classe B_shadow efetiva para validação pós-deploy).

---

### B2-arith+adv — `verify_arithmetic` + `verify_plan_adversarial` (`AGENT_VERIFY`)

**Como exercitar:**
```bash
# Suite completa (22 testes, zero API real — todos via monkeypatch)
python -m pytest tests/agente/sdk/test_verifiers.py \
                 tests/agente/sdk/test_verify_domain.py \
                 tests/agente/workers/test_plan_verifier.py -v
```

Smoke `verify_arithmetic`:
```bash
python -c "
from unittest.mock import patch
from app.agente.sdk import verifiers

with patch.object(verifiers, '_call_sonnet_verifier', return_value='Total diz 3 itens mas tabela tem 2'):
    r = verifiers.verify_arithmetic('Temos 3 pedidos: VCD001, VCD002. Total: 3.')
    print('COM_ERRO:', r)  # esperado: ok=False, issues nao vazio

with patch.object(verifiers, '_call_sonnet_verifier', return_value='OK'):
    r = verifiers.verify_arithmetic('Temos 2 pedidos. Total: 2.')
    print('SEM_ERRO:', r)  # esperado: ok=True, issues=[]
"
```

**O que observar:**
```sql
-- Veredito 'verify' gravado em agent_step
SELECT step_uid,
       outcome_signal->'verify'->>'refuted'  AS refuted,
       outcome_signal->'verify'->>'reason'   AS reason
FROM agent_step
WHERE outcome_signal ? 'verify'
ORDER BY created_at DESC LIMIT 20;
```

Log: `[plan_verifier] concluido: step_uid=<uid> refuted=True/False`.

**Critério de PASS:** 22/22 testes passam. `verify_arithmetic` retorna `{'ok': False, 'issues': [...]}` quando LLM mockado detecta erro; `{'ok': True, 'issues': []}` para entrada None ou ''. `verify_plan_adversarial` persiste `outcome_signal['verify']` no banco. `db.session.commit()` chamado (CRITICAL-1 — provado por spy passthrough). Step inexistente → no-op.

**Flag-OFF (zero efeito):** `AGENT_VERIFY` não tem efeito de runtime no commit atual — as funções são shadow-only sem caller ativo:
```bash
grep -rn "USE_AGENT_VERIFY" app/ --include="*.py" | grep -v "__pycache__" | grep "if "
# Deve retornar vazio
```
```sql
SELECT count(*) FROM agent_step WHERE outcome_signal ? 'verify';
-- Deve retornar 0 com flag OFF
```

**Status de verificação local:** ✅ `22 passed in 6.54s`. `USE_AGENT_VERIFY` existe apenas em `feature_flags.py` e comentários — nenhum `if USE_AGENT_VERIFY:` em código de produção. Funções são shadow-only; flag é forward declaration para Onda 3.

---

### B3 — replan + budget + escalate (`AGENT_PLANNER`)

**Como exercitar:**
```bash
# Suite completa (22 testes)
python -m pytest tests/agente/sdk/test_plan_replan.py -v
```

Smoke PlanState puro (sem DB, sem flag):
```bash
python -c "
from app.agente.sdk.plan_state import PlanState

ps = PlanState()
ps.apply_task_event({'tool': 'TaskCreate', 'taskId': '1', 'subject': 'consultar X'})

ps.mark_step_failed('1')
assert ps.to_dict()['steps']['1']['failures'] == 1
assert ps.should_escalate(max_retries=2) is False
assert '1' in ps.steps_to_retry(max_retries=2)

ps.mark_step_failed('1'); ps.mark_step_failed('1')
assert ps.should_escalate(max_retries=2) is True
assert '1' not in ps.steps_to_retry(max_retries=2)

ps2 = PlanState.from_dict(ps.to_dict())
assert ps2.should_escalate(max_retries=2) is True
print('PASS: PlanState B3 replan/escalate ok')
"
```

**O que observar:**
```sql
-- Métricas com escalonamento gravado
SELECT agent_id, agent_type, escalated_to_human, source, recorded_at
FROM agent_invocation_metrics
WHERE escalated_to_human = true
ORDER BY recorded_at DESC LIMIT 10;

-- Confirmar coluna existe
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'agent_invocation_metrics'
  AND column_name IN ('escalated_to_human', 'agent_id');
```

**Critério de PASS:** Parte A (PlanState): `mark_step_failed` 1x → `failures=1`, `status='failed'`; 3x com `max_retries=2` → `should_escalate()=True`; `steps_to_retry()` exclui step com `failures > max_retries`; roundtrip preserva `failures`. Parte B (`marcar_escalonamento`): retorna `True` e grava `escalated_to_human=true`; idempotente; inexistente → `False` sem exceção.

**Flag-OFF (zero efeito):** Bloco `if USE_AGENT_PLANNER:` em linhas 854, 1686, 1911 de `chat.py` não executa. As classes são módulos puros — a flag controla apenas o wiring no loop SSE.

**Status de verificação local:** ✅ `22 passed in 12.11s`. Cobertura: `TestMarkStepFailed` (4), `TestShouldEscalate` (6), `TestStepsToRetry` (4), `TestToFromDictComFailures` (4), `TestMarcarEscalonamento` (4).

---

### B-TRIAGE — `triage_meta` (`AGENT_PLANNER`)

**Como exercitar:**
```bash
# Suite completa (13 testes, LLM e ontologia totalmente mockados)
python -m pytest tests/agente/sdk/test_plan_triage.py -v
```

Smoke com monkeypatch:
```bash
python -c "
import json
from unittest.mock import patch
from app.agente.sdk import plan_triage

STEPS = json.dumps({'steps': [
  {'subject': 'Consultar pedidos em aberto do cliente Atacadao', 'entities': ['ATACADAO']},
  {'subject': 'Filtrar por data da semana atual', 'entities': []},
]})
ENTITY = {'entity_type': 'cliente', 'entity_name': 'ATACADAO', 'entity_key': '75315333', 'user_id': 0}

with patch.object(plan_triage, '_call_llm_triage', return_value=STEPS), \
     patch.object(plan_triage, 'query_ontology_entities', return_value=[ENTITY]):
    result = plan_triage.triage_meta('Ver pedidos do Atacadao em aberto', user_id=42)

print(result)
assert len(result['steps']) == 2 and len(result['grounded_entities']) == 1
print('PASS')
"
```

**O que observar:** Retorno direto de `triage_meta` — dict com chaves `'steps'` (list) e `'grounded_entities'` (list). Degradação graciosa: meta vazia retorna `{'steps': [], 'grounded_entities': []}` SEM chamar LLM ou ontologia. **Nenhuma query SQL** — função é READ-ONLY.

**Critério de PASS:** 13/13 testes passam. `result['steps']` len ≥ 1; cada step com `subject` não-vazio. Meta vazia → `{'steps': [], 'grounded_entities': []}` sem chamada LLM. Exceções nunca propagadas.

**Flag-OFF (zero efeito):** `triage_meta` não tem caller ativo em `chat.py` (grep confirma zero ocorrências). `AGENT_PLANNER=true` ativa PlanState (B1) mas NÃO dispara `triage_meta` automaticamente — o wiring futuro ainda precisa ser codificado.

**Status de verificação local:** ✅ `13 passed in 0.28s`. Feature é shadow puro — testes validam lógica interna (decomposição + ancoragem + degradação), não fluxo end-to-end ativo.

---

### B2-domain — `verify_domain` (`AGENT_VERIFY`)

**Como exercitar:**
```bash
# Suite dedicada (9 testes)
python -m pytest tests/agente/sdk/test_verify_domain.py -v
```

Smoke dos 4 contratos principais:
```bash
python -c "
from unittest.mock import patch
import app.agente.tools.ontology_query_tool as oqt
from app.agente.sdk import verifiers

# Entidade conhecida → ok=True, issues=[]
with patch.object(oqt, 'query_ontology_entities', return_value=[
    {'entity_type':'cliente','entity_name':'ATACADAO','entity_key':'75315333','user_id':0}]):
    r = verifiers.verify_domain({'action':'consultar','entities':['Atacadao']}, user_id=42)
print('CONHECIDO:', r)  # esperado: ok=True, issues=[]

# Entidade desconhecida → ok=False
with patch.object(oqt, 'query_ontology_entities', return_value=[]):
    r = verifiers.verify_domain({'action':'consultar','entities':['CLIENTE_FANTASMA']}, user_id=42)
print('DESCONHECIDO:', r)  # esperado: ok=False, issues=['entidade desconhecida...CLIENTE_FANTASMA']

# Step sem campo entities → ok=True (sem chamar ontologia)
r = verifiers.verify_domain({'action':'dummy'}, user_id=42)
print('SEM ENTITIES:', r)  # esperado: ok=True, issues=[]

# Erro em query → best-effort ok=True
with patch.object(oqt, 'query_ontology_entities', side_effect=RuntimeError('DB timeout')):
    r = verifiers.verify_domain({'action':'x','entities':['X']}, user_id=42)
print('BEST-EFFORT:', r)  # esperado: ok=True, issues=[]
"
```

**O que observar:** Retorno: `{'ok': bool, 'issues': list[str]}`. Log WARNING: `'[verify_domain] entidade desconhecida na ontologia: <NOME>'`. Sem query SQL — busca via `query_ontology_entities`.

**Critério de PASS:** 9/9 testes passam. Entidade conhecida → `ok=True`. Entidade desconhecida → `ok=False` com nome em `issues`. Step sem `entities` → `ok=True` sem chamar ontologia. Erro em query → `ok=True` sem propagação.

**Flag-OFF (zero efeito):** `AGENT_VERIFY` não lê `USE_AGENT_VERIFY` no corpo da função (shadow puro). A flag gatará o enqueue no loop principal (Onda 3, não implementado):
```bash
grep -rn 'verify_domain' app/agente/ --include='*.py' | grep -v 'def verify_domain\|#\|verifiers.py'
# Resultado esperado: nenhuma linha (sem caller ativo)
```

**Status de verificação local:** ✅ `9 passed in 0.23s`. Smoke manual dos 5 contratos confirmado. Flag apenas em comentários/`feature_flags.py` — nenhum `if` no código de produção.

---

### A3 — Eval Runner (`AGENT_EVAL_GATE`)

**Como exercitar:**
```bash
# Suite completa (27 testes, zero API real)
python -m pytest tests/agente/services/test_eval_gate.py -v
```

Smoke shadow (exatamente o que o D8 scheduler executa):
```bash
python -c "
import sys, pathlib; sys.path.insert(0, '.')
from app.agente.services.eval_gate_service import run_evals, eval_gate
evals_dir = pathlib.Path('.') / '.claude' / 'evals' / 'subagents'
result = run_evals(
    agent_name='analista-carteira',
    dataset_path=str(evals_dir / 'analista-carteira' / 'dataset.yaml'),
    # invoke_fn ausente = shadow
    judge_fn=lambda p: 'pass',  # mock para não chamar API real
)
print('score:', result['score'], 'total:', result['total'], 'passed:', result['passed'])
for c in result['cases']: assert c['status'] == 'error', c
gate = eval_gate(baseline_score=0.0, candidate_score=result['score'], mode='report_only')
print('blocked:', gate['blocked'], 'regression:', gate['regression'])
assert gate['blocked'] == False
print('PASS shadow + invariant')
"
```

Smoke com `invoke_fn` mockado:
```bash
python -c "
import sys, pathlib; sys.path.insert(0, '.')
from app.agente.services.eval_gate_service import run_evals, eval_gate
evals_dir = pathlib.Path('.') / '.claude' / 'evals' / 'subagents'
r = run_evals('analista-carteira', str(evals_dir/'analista-carteira'/'dataset.yaml'),
    invoke_fn=lambda x: 'resposta mock', judge_fn=lambda p: 'pass')
assert r['score'] == 1.0
gate = eval_gate(0.9, 0.5, mode='report_only')
assert gate['blocked'] == False and gate['regression'] == True
print('PASS all-pass + regressao detectada mas NAO bloqueada')
"
```

**O que observar (em PROD com flag ON após cron D8 às 11h UTC):**

Logs Render (grep `[EVAL_GATE]`):
```
[EVAL_GATE] analista-carteira: score=0.000 passed=0/5
[EVAL_GATE] auditor-financeiro: score=0.000 passed=0/3
```
Score = 0.0 é esperado enquanto `invoke_fn` não for wired ao agente real.

Timer: `[TIMER] Step 28 (Eval Gate): <1.0s` (shadow é apenas YAML parse + Python puro).

**Critério de PASS:** 27/27 testes passam incluindo `test_report_only_nunca_bloqueia_com_regressao` e `test_invoke_fn_default_levanta_not_implemented`. Shadow: todos os casos com `status='error'`, `score=0.0`, `blocked=False`. Invoke mockado: `score=1.0`; regressão detectada mas `blocked=False` em `report_only`. Log D8 com flag ON: linhas `[EVAL_GATE]` aparecem UMA vez/dia. Step 28 não conta no `total_modulos_sync`.

**Flag-OFF (zero efeito):** `EVAL_GATE_ENABLED=False` (linha 109 do scheduler); bloco completo pulado; `_ultimo_eval_gate` não atualizado. Log de start: `"Eval Gate (A3): 28o modulo, diario as 11:00 report-only (enabled=False)"`.

**Status de verificação local:** ✅ `27 passed in 0.37s`. Smokes shadow e all-pass+regressão confirmados. Caminho do scheduler não exercitado diretamente (requer `app_context` Flask + DB); código inspecionado (linhas 2046-2107) e confirma: guarded por `EVAL_GATE_ENABLED`, one-per-day via `_ultimo_eval_gate`, exceções capturadas internamente.

---

### A4 — Promoção automática de diretriz (`AGENT_DIRECTIVE_PROMOTION`)

**Como exercitar:**
```bash
# Suite completa (23 casos, zero DB real)
python -m pytest tests/agente/services/test_directive_promotion.py -v
```

Smoke inline cobrindo 5 cenários:
```bash
python -c "
from unittest.mock import patch, MagicMock
from app.agente.services.directive_promotion_service import (
    propose_directive_from_plan, evaluate_and_promote, _persist_directive
)
from app.agente.config.feature_flags import AGENT_DIRECTIVE_PROMOTION

# Cenário 1: plano completo -> candidata
plan = {'steps': {
    '1': {'subject': 'verificar pedido X', 'status': 'completed'},
    '2': {'subject': 'consultar estoque Y', 'status': 'completed'},
}}
c = propose_directive_from_plan(plan, 'smoke-01')
assert c['status'] == 'candidata'

# Cenário 2: sem FALHA_ODOO + sem regressão -> would_promote (sem escrita em banco)
with patch('app.agente.services.directive_promotion_service._query_falha_odoo', return_value=[]):
    r = evaluate_and_promote(c, baseline_score=0.7, candidate_score=0.8)
assert r['decision'] == 'would_promote' and r['gate']['blocked'] is False

# Cenário 3: anti-gaming R9 — FALHA_ODOO domina mesmo com score perfeito
op = MagicMock(); op.status = 'FALHA_ODOO'
with patch('app.agente.services.directive_promotion_service._query_falha_odoo', return_value=[op]):
    r2 = evaluate_and_promote(c, baseline_score=0.0, candidate_score=1.0)
assert r2['decision'] == 'rejected' and r2['reason'] == 'falha_odoo_ambiental'

# Cenário 4: _persist_directive é stub (NotImplementedError)
try:
    _persist_directive(c)
    assert False, 'deveria ter levantado NotImplementedError'
except NotImplementedError:
    pass

assert AGENT_DIRECTIVE_PROMOTION is False
print('OK todos os cenarios passaram')
"
```

**O que observar:** Retorno de `evaluate_and_promote` (caminho feliz): `{'decision': 'would_promote', 'gate': {'regression': False, 'blocked': False, 'delta': float}, ...}`. Anti-gaming R9: `{'decision': 'rejected', 'reason': 'falha_odoo_ambiental'}` (sem chave `'gate'`). **Zero writes em `agent_memories`** — `_persist_directive` é stub `NotImplementedError` e nunca é chamado.

**Critério de PASS:** 23/23 testes passam. `propose_directive_from_plan` retorna `status='candidata'` com `titulo` não-vazio. `evaluate_and_promote` com FALHA_ODOO → `decision='rejected'` mesmo com `candidate_score=1.0` (R9). `_persist_directive` levanta `NotImplementedError`. `AGENT_DIRECTIVE_PROMOTION is False`.

**Flag-OFF (zero efeito):** Sem caller ativo:
```bash
grep -rn "evaluate_and_promote\|propose_directive_from_plan" app/ --include="*.py"
# Resultado: apenas directive_promotion_service.py e feature_flags.py (comentário)
```

**Status de verificação local:** ✅ `23 passed in 0.29s`. Smoke de 5 cenários confirmado. Feature é shadow puro — não escreve em banco em nenhum cenário testável hoje.

---

### F4/F5 — Skill Hints Advisory (`AGENT_SKILL_RAG`)

**Como exercitar:**
```bash
# Suite completa (22 testes, 0 dependência de DB/SDK/PROD)
python -m pytest tests/agente/sdk/test_context_enrichment.py -v
```

Smoke direto com flag ON:
```bash
python -c "
import os, importlib
from unittest.mock import MagicMock, patch

os.environ['AGENT_SKILL_RAG'] = 'true'
ff = importlib.import_module('app.agente.config.feature_flags')
importlib.reload(ff)
assert ff.USE_AGENT_SKILL_RAG is True

def make_skill(name, desc):
    s = MagicMock(); s.name = name; s.description = desc
    s.available_to_principal = True; return s

skills = [
    make_skill('gerindo-expedicao', 'Gerencia pedidos de expedição separação embarque despacho'),
    make_skill('cotando-frete', 'Cotação de frete transportadoras rotas custo'),
    make_skill('rastreando-odoo', 'Rastreia NFs POs SOs no Odoo ERP'),
]
mock_reg = MagicMock(); mock_reg.skills = skills

with patch('app.agente.sdk.context_enrichment.capability_registry') as mc:
    mc.build_registry.return_value = mock_reg
    from app.agente.sdk.context_enrichment import build_skill_hints_block
    result = build_skill_hints_block('quero ver separação de pedidos')

print(result)
assert '<skill_hints' in result and 'advisory' in result and 'gerindo-expedicao' in result
print('PASS')
"
```

**O que observar (em PROD com flag ON):**

Log `[CONTEXT_BUDGET]` nos logs do Render (INFO level):
```
[CONTEXT_BUDGET] user_id=<N> | session_ctx_chars=<N> | skill_hints_chars=<N > 0> | ...
```
`skill_hints_chars > 0` confirma que o bloco foi injetado no `additionalContext`. Com flag OFF: `skill_hints_chars=0` em TODAS as linhas.

Conteúdo do bloco gerado:
```xml
<skill_hints priority="advisory">
Skills mais relevantes para esta query: gerindo-expedicao, cotando-frete
</skill_hints>
```

**Critério de PASS:** 22/22 testes passam. `build_skill_hints_block` retorna string com `<skill_hints priority="advisory">` e skill com maior overlap de tokens. `available_to_principal=False` → skill excluída do bloco. Exceção interna → retorna `None/[]` sem propagar (best-effort).

**Flag-OFF (zero efeito):** Guard `if USE_AGENT_SKILL_RAG and prompt:` na linha 1276 de `hooks.py` não entra; `skill_hints_context=''`; `full_context` não muda; `skill_hints_chars=0` nos logs.

**Status de verificação local:** ✅ `22 passed in 0.26s`. Smoke flag ON/OFF confirmados. O hook `UserPromptSubmit` completo requer SDK real (não disponível localmente); o guard da linha 1276 foi verificado via simulação direta do trecho de código.

---

### D5 — World Model Injection (`AGENT_WORLD_MODEL_INJECT`)

**Como exercitar:**
```bash
# Suite completa (22 testes — cobre build_world_model_block, flags, tolerância)
python -m pytest tests/agente/sdk/test_context_enrichment.py -v
```

Smoke com ontologia mockada:
```bash
python -c "
import os, importlib
from unittest.mock import patch
os.environ['AGENT_WORLD_MODEL_INJECT'] = 'true'
import app.agente.sdk.context_enrichment as ce
mock_entities = [
    {'entity_type': 'cliente', 'entity_name': 'ATACADAO DISTRIBUIDORA', 'entity_key': '75315333', 'user_id': 1},
    {'entity_type': 'transportadora', 'entity_name': 'BRASPRESS', 'entity_key': None, 'user_id': 1},
]
with patch.object(ce, 'query_ontology_entities', return_value=mock_entities):
    result = ce.build_world_model_block(user_id=1, query='frete do Atacadao via transportadora')
    assert '<world_model' in result and 'advisory' in result and 'ATACADAO' in result
    print('PASS')
    print(result)
"
```

**O que observar:**

Retorno esperado:
```xml
<world_model priority="advisory">
Entidades canônicas relevantes:
  [cliente] ATACADAO DISTRIBUIDORA (75315333)
  [transportadora] BRASPRESS
</world_model>
```

Log Render (flag ON + ontologia populada):
```
[CONTEXT_BUDGET] ... | world_model_chars=<N > 0> | ...
```

Roteamento de domínio (`_resolve_entity_types_for_query`):
- `'frete para Manaus via Braspress'` → `['transportadora', 'cliente']`
- `'pedido de separacao da carteira'` → `['cliente', 'produto', 'transportadora']`
- Query sem keyword → `[]` (busca genérica 3 tipos)

**Critério de PASS:** 22/22 testes passam. `build_world_model_block` retorna string com `<world_model priority="advisory">` e entidades mockadas. Ontologia vazia → retorna `None` (bloco NÃO injetado). Qualquer exceção → best-effort silencioso. `world_model_chars > 0` nos logs com flag ON + ontologia populada.

**Flag-OFF (zero efeito):** Guard `if USE_AGENT_WORLD_MODEL_INJECT:` no hook não entra; `world_model_context=''`; `world_model_chars=0` nos logs. Verificado com `call_count==0` no smoke.

**Status de verificação local:** ✅ `22 passed in 0.20s`. Smokes flag ON/OFF confirmados. Roteamento de domínio verificado. Injeção real no `additionalContext` requer deploy com flag ON + `agent_memory_entities` populados via D2/D4.

---

## Apêndice — Cheatsheet SQL de Inspeção

Agregação das queries mais úteis para monitorar o estado das features em PROD:

```sql
-- 1. agent_step: visão geral das últimas 24h
SELECT count(*), channel, model
FROM agent_step
WHERE created_at > now() - interval '24 hours'
GROUP BY channel, model ORDER BY count DESC;

-- 2. agent_step: últimos 10 steps com todos os campos de outcome
SELECT id, step_uid, session_id, user_id, channel, model,
       input_tokens, output_tokens, tools_used,
       outcome_signal, outcome_effective_count, created_at
FROM agent_step ORDER BY created_at DESC LIMIT 10;

-- 3. agent_step: outcome_signal['judge'] (E2/step_judge)
SELECT step_uid,
       outcome_signal -> 'judge' ->> 'score'              AS score,
       outcome_signal -> 'judge' ->> 'label'              AS label,
       outcome_signal -> 'judge' ->> 'componente_culpado' AS culpado
FROM agent_step WHERE outcome_signal ? 'judge'
ORDER BY created_at DESC LIMIT 20;

-- 4. agent_step: outcome_signal['verify'] (B2-arith+adv)
SELECT step_uid,
       outcome_signal -> 'verify' ->> 'refuted' AS refuted,
       outcome_signal -> 'verify' ->> 'reason'  AS reason
FROM agent_step WHERE outcome_signal ? 'verify'
ORDER BY created_at DESC LIMIT 20;

-- 5. agent_step: outcome_signal['frustration_score'] (E1)
SELECT step_uid, outcome_signal ->> 'frustration_score' AS score,
       outcome_signal ->> 'feedback' AS feedback
FROM agent_step WHERE outcome_signal IS NOT NULL
ORDER BY created_at DESC LIMIT 20;

-- 6. agent_memory_entities: nós da ontologia por tipo (D2)
SELECT entity_type, COUNT(*) AS n
FROM agent_memory_entities WHERE user_id = 0
GROUP BY entity_type ORDER BY entity_type;

-- 7. agent_memory_entities: nós pessoais + canônicos de um user
SELECT entity_type, entity_name, entity_key, mention_count, user_id
FROM agent_memory_entities
WHERE user_id = ANY(ARRAY[<user_id>, 0])
ORDER BY entity_type, mention_count DESC LIMIT 30;

-- 8. agent_memory_entity_relations: relações com proveniência (D3)
SELECT r.source_session_id, r.source_step_uid,
       r.valid_from, r.valid_to, r.relation_type, r.weight, r.created_at
FROM agent_memory_entity_relations r
WHERE r.source_session_id IS NOT NULL
ORDER BY r.created_at DESC LIMIT 20;

-- 9. agent_memory_entity_relations: % com proveniência (D3 - monitorar pós-AGENT_ONTOLOGY=true)
SELECT
  CASE WHEN source_session_id IS NOT NULL THEN 'com_proveniencia' ELSE 'sem_proveniencia' END,
  COUNT(*)
FROM agent_memory_entity_relations GROUP BY 1;

-- 10. agent_sessions: PlanState gravado (B1)
SELECT session_id, data->'plan'->'steps' AS plan_steps
FROM agent_sessions
WHERE data ? 'plan' AND data->'plan' IS NOT NULL AND data->'plan' != 'null'::jsonb
ORDER BY updated_at DESC LIMIT 10;

-- 11. agent_invocation_metrics: escalonamentos (B3)
SELECT agent_id, agent_type, escalated_to_human, source, recorded_at
FROM agent_invocation_metrics
WHERE escalated_to_human = true
ORDER BY recorded_at DESC LIMIT 10;

-- 12. Confirmar flag-OFF global: nenhum dado de features ativas
SELECT
  (SELECT count(*) FROM agent_step WHERE outcome_signal IS NOT NULL)       AS steps_com_outcome,
  (SELECT count(*) FROM agent_memory_entities WHERE user_id = 0)           AS nos_canonicos,
  (SELECT count(*) FROM agent_sessions WHERE data ? 'plan')                AS sessoes_com_plan,
  (SELECT count(*) FROM agent_step WHERE outcome_signal ? 'judge')         AS steps_com_judge,
  (SELECT count(*) FROM agent_step WHERE outcome_signal ? 'verify')        AS steps_com_verify;
-- Com todas as flags OFF: steps_com_outcome=0, nos_canonicos=0, sessoes_com_plan=0, etc.
```

---

## Nota Final

### Falhas pré-existentes (baseline da main)

Existem **2 testes pendentes em `test_pending_questions.py`** que são falhas pré-existentes na `main` — não introduzidas pela evolução do agente. Antes de ativar qualquer feature da Onda 2, triá-las:

```bash
python -m pytest tests/agente/routes/test_pending_questions.py -v
# Identificar se as falhas são baseline da main ou regressões introduzidas
```

Tratar como P0 antes de escalar para GATE-1 e além.

### Tudo está flag-OFF — validar não muda PROD

Todas as 15 features têm `default=false` em `feature_flags.py`. Rodar qualquer receita deste runbook (pytest, smoke python-c) **não altera o comportamento de PROD**. Para confirmar a qualquer momento:

```bash
python -c "
import app.agente.config.feature_flags as ff
flags = {k:v for k,v in vars(ff).items() if k.startswith('USE_') or k.startswith('AGENT_')}
for k,v in sorted(flags.items()): print(f'{k}={v}')
"
# Todas as flags devem ser False no ambiente sem env vars configuradas
```

A ativação progressiva pelos GATEs acima garante rollout seguro com observabilidade em cada etapa.
