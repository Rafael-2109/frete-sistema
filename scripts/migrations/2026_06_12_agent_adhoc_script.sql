CREATE TABLE IF NOT EXISTS agent_adhoc_script (
    id               SERIAL PRIMARY KEY,
    session_id       VARCHAR(64) NOT NULL,
    user_id          INTEGER NOT NULL REFERENCES usuarios(id),
    problema         VARCHAR(120),
    command_masked   TEXT NOT NULL,
    contexto_user_msg TEXT,
    skill_relacionada VARCHAR(80),
    tipo_gap         VARCHAR(20) NOT NULL DEFAULT 'desconhecido',
    motivo_fallback  VARCHAR(200),
    retries_sessao   SMALLINT DEFAULT 0,
    embedding        vector(1024),
    cluster_id       INTEGER,
    criado_em        TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_adhoc_session ON agent_adhoc_script (session_id);
CREATE INDEX IF NOT EXISTS ix_adhoc_user ON agent_adhoc_script (user_id);
CREATE INDEX IF NOT EXISTS ix_adhoc_cluster ON agent_adhoc_script (cluster_id);
CREATE INDEX IF NOT EXISTS ix_adhoc_criado ON agent_adhoc_script (criado_em);
CREATE INDEX IF NOT EXISTS ix_adhoc_embedding ON agent_adhoc_script
    USING hnsw (embedding vector_cosine_ops);
