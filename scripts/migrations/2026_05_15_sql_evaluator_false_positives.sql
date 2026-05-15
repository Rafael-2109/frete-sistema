-- Migration: sql_evaluator_false_positives (T7 — Auto few-shot)
-- Data: 2026-05-15
-- Ref: docs/skills/consultando-sql + Sprint 3 plano evaluator improvement
--
-- Tabela armazena pares (SQL_rejeitada, motivo) confirmados como falsos
-- positivos do Haiku evaluator. Em queries futuras, busca semantica por
-- cosine_similarity > 0.85 injeta contra-exemplos no prompt do evaluator.
--
-- DESIGN:
-- - status='pending_review' por padrao (NAO injeta automaticamente)
-- - Promocao para 'active' requer review humano (D8 dialogue ou admin manual)
-- - Soft delete: status='rejected', nao DELETE fisico
-- - Embedding gerado do par (sql_text + rejection_reason)
-- - Linkado ao agent_improvement_dialogue via improvement_key (sem FK fisica)
--
-- Indices:
-- - ivfflat embedding para busca cosine (lists=10 — tabela pequena <500 rows)
-- - parcial status='active' para filtro rapido
-- - improvement_key para correlacao com D8
--
-- Idempotente via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS sql_evaluator_false_positives (
    id                   SERIAL PRIMARY KEY,
    sql_text             TEXT NOT NULL,
    rejection_reason     TEXT NOT NULL,
    rejection_category   VARCHAR(50),
    texto_embedado       TEXT NOT NULL,
    embedding            vector(1024),
    model_used           VARCHAR(50),
    content_hash         VARCHAR(64) NOT NULL,
    improvement_key      VARCHAR(100),
    status               VARCHAR(20) NOT NULL DEFAULT 'pending_review',
    confirmed_by_user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    confirmed_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    reviewed_by_user_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    reviewed_at          TIMESTAMP,
    times_referenced     INTEGER NOT NULL DEFAULT 0,
    last_referenced_at   TIMESTAMP,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT sql_eval_falses_status_chk
        CHECK (status IN ('pending_review', 'active', 'rejected'))
);

-- Index unico em content_hash evita duplicacao do mesmo par (sql, reason)
CREATE UNIQUE INDEX IF NOT EXISTS idx_sql_eval_falses_content_hash
    ON sql_evaluator_false_positives (content_hash);

-- Index parcial: somente 'active' para busca rapida no hot path
CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_active_status
    ON sql_evaluator_false_positives (status)
    WHERE status = 'active';

-- Index para correlacao com D8 (lookups por improvement_key)
CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_imp_key
    ON sql_evaluator_false_positives (improvement_key)
    WHERE improvement_key IS NOT NULL;

-- Index para review queue (UI admin)
CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_pending
    ON sql_evaluator_false_positives (created_at DESC)
    WHERE status = 'pending_review';

-- IVFFlat para busca cosine — criar apos popular (lists=10 para <500 rows)
-- Quando tabela ultrapassar 1K rows, recriar com lists=sqrt(N)
CREATE INDEX IF NOT EXISTS idx_sql_eval_falses_embedding
    ON sql_evaluator_false_positives
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

COMMENT ON TABLE sql_evaluator_false_positives IS
    'T7 — Falsos positivos confirmados do Haiku evaluator. Status=active injetado como contra-exemplo no prompt. Status=pending_review aguarda revisao humana. Promocao via D8 dialogue ou admin manual.';

COMMENT ON COLUMN sql_evaluator_false_positives.content_hash IS
    'sha256(sql_text + rejection_reason) — evita duplicacao';

COMMENT ON COLUMN sql_evaluator_false_positives.improvement_key IS
    'Correlaciona com agent_improvement_dialogue.suggestion_key (sem FK fisica)';

COMMENT ON COLUMN sql_evaluator_false_positives.times_referenced IS
    'Quantas vezes foi injetado como contra-exemplo no Evaluator';
