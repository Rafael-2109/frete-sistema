-- Migration: agent_eval_case (A3-R3 — calibração do judge de eval)
-- Data: 2026-06-01
-- Ref: app/agente/models.py (AgentEvalCase), app/agente/workers/eval_runner.py
--      (persist_eval_cases), eixos/A-flywheel.md:165 ("Calibração obrigatória:
--      spot-check humano de 5-10% das notas do judge").
--
-- Tabela para persistir 1 linha POR CASO avaliado num run (o veredito granular
-- do judge — mediana de N runs), habilitando spot-check humano de 5-10% e a
-- metrica de concordancia judge-vs-humano. Sem calibração, trocamos um proxy
-- cego (eco) por outro (judge nao-auditado) — exatamente o que A-flywheel.md:318
-- adverte.
--
-- human_verdict NULL = caso ainda NAO revisado por humano. Quando revisado:
-- 'agree' (judge acertou) ou 'disagree' (judge errou). A escrita do verdict
-- humano e' manual/futura (V1 = listagem + métrica de concordancia).
--
-- Sem FK para agent_eval_scores nem usuarios — preserva histórico cross-deploy
-- (mesma filosofia de agent_eval_scores / agent_invocation_metrics). reviewed_by
-- guarda usuarios.id do revisor SEM FK (não bloqueia delete de usuário).
--
-- Idempotente via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS agent_eval_case (
  id                  BIGSERIAL PRIMARY KEY,
  agent_name          TEXT NOT NULL,
  case_id             TEXT NOT NULL,                       -- ex 'ac-01'
  git_sha             TEXT NULL,
  case_score          DOUBLE PRECISION NOT NULL,           -- mediana do judge (0-1)
  status              TEXT NOT NULL,                        -- pass|fail|error
  n_runs              INTEGER NOT NULL DEFAULT 1,
  case_score_variance DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  invoke_failures     INTEGER NOT NULL DEFAULT 0,
  evidence            TEXT NULL,                            -- veredito textual do judge
  human_verdict       TEXT NULL,                            -- NULL=não revisado; 'agree'|'disagree'
  human_note          TEXT NULL,                            -- nota opcional do revisor
  reviewed_by         INTEGER NULL,                         -- usuarios.id do revisor (sem FK)
  reviewed_at         TIMESTAMP NULL,
  recorded_at         TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- Filtro principal: casos por agent_name (amostragem + concordancia por agente)
CREATE INDEX IF NOT EXISTS agent_eval_case_agent_name_idx
  ON agent_eval_case (agent_name);

-- Janela temporal global (relatorios, listagens recentes).
CREATE INDEX IF NOT EXISTS agent_eval_case_recorded_at_idx
  ON agent_eval_case (recorded_at DESC);

-- Amostragem de NAO-revisados (sample_unreviewed): índice PARCIAL no subconjunto
-- de casos sem veredito humano — o spot-check só busca human_verdict IS NULL.
CREATE INDEX IF NOT EXISTS agent_eval_case_unreviewed_idx
  ON agent_eval_case (agent_name)
  WHERE human_verdict IS NULL;

COMMENT ON TABLE agent_eval_case IS
  'A3-R3 (2026-06-01): calibracao do judge de eval. 1 linha por caso avaliado '
  'num run (case_score = mediana do judge de N runs). Habilita spot-check humano '
  'de 5-10% (sample_unreviewed) + metrica de concordancia judge-vs-humano '
  '(concordance_rate). human_verdict NULL=nao revisado; agree|disagree quando '
  'revisado. Sem FK — preserva historico cross-deploy. Gated por '
  'AGENT_EVAL_CALIBRATION (persist_eval_cases em eval_runner). Spec '
  'eixos/A-flywheel.md:165.';
