CREATE TABLE IF NOT EXISTS agent_skill_effectiveness (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES usuarios(id),
    session_id      VARCHAR(64) NOT NULL,
    skill_name      VARCHAR(80) NOT NULL,
    anchor_msg_id   VARCHAR(64) NOT NULL,
    stage_reached   SMALLINT DEFAULT 0,
    resolveu        BOOLEAN,
    ramo            VARCHAR(20),
    confidence      DOUBLE PRECISION,
    action_ref      VARCHAR(120),
    error_signature VARCHAR(64),
    evidencia_json  JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_skill_eff_session_anchor
    ON agent_skill_effectiveness (session_id, anchor_msg_id);
CREATE INDEX IF NOT EXISTS ix_agent_skill_effectiveness_user_id
    ON agent_skill_effectiveness (user_id);
CREATE INDEX IF NOT EXISTS ix_agent_skill_effectiveness_session_id
    ON agent_skill_effectiveness (session_id);
CREATE INDEX IF NOT EXISTS ix_skill_eff_skill_resolveu
    ON agent_skill_effectiveness (skill_name, resolveu);
