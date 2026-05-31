-- Migration 2026-05-28 — Audit Hook Determinístico Odoo
--
-- Objetivo: rastrear TODA chamada XML-RPC write no Odoo correlacionando com
-- sessao do agente web (session_id) e tool_use_id (correlacao 1:1 com tool call).
--
-- ADD COLUMN session_id (FK opcional para agent_sessions.session_id)
-- ADD COLUMN tool_use_id (id da tool call do SDK Anthropic — sem FK, free string)
-- ADD COLUMN agent_type   (main | gestor-estoque-odoo | worker_rq | scheduler | cli)
--
-- Também inclui ALTER COLUMN da v21 (G-AUDIT-2 — ainda não aplicada em PROD)
-- para garantir consistência model SQLAlchemy <-> banco.
--
-- Idempotente: todas operacoes usam IF NOT EXISTS / ALTER TYPE re-amplio.

-- 1. Ampliar colunas VARCHAR que estouravam (v21 incorporada)
ALTER TABLE operacao_odoo_auditoria ALTER COLUMN acao TYPE VARCHAR(60);
ALTER TABLE operacao_odoo_auditoria ALTER COLUMN status TYPE VARCHAR(30);
ALTER TABLE operacao_odoo_auditoria ALTER COLUMN pipeline_etapa TYPE VARCHAR(40);

-- 2. ADD COLUMN session_id / tool_use_id / agent_type
ALTER TABLE operacao_odoo_auditoria ADD COLUMN IF NOT EXISTS session_id VARCHAR(64);
ALTER TABLE operacao_odoo_auditoria ADD COLUMN IF NOT EXISTS tool_use_id VARCHAR(40);
ALTER TABLE operacao_odoo_auditoria ADD COLUMN IF NOT EXISTS agent_type VARCHAR(40);

-- 3. Indices para query por sessao e por tool_use
CREATE INDEX IF NOT EXISTS idx_oaa_session_id
  ON operacao_odoo_auditoria(session_id)
  WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_oaa_tool_use_id
  ON operacao_odoo_auditoria(tool_use_id)
  WHERE tool_use_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_oaa_agent_type
  ON operacao_odoo_auditoria(agent_type)
  WHERE agent_type IS NOT NULL;

-- 4. Comentarios para futuras referencias
COMMENT ON COLUMN operacao_odoo_auditoria.session_id IS
  'FK logica para agent_sessions.session_id (UUID nosso). NULL quando origem != agente web.';

COMMENT ON COLUMN operacao_odoo_auditoria.tool_use_id IS
  'tool_use_id do SDK Anthropic — correlaciona 1:1 com chamada de tool no transcript.';

COMMENT ON COLUMN operacao_odoo_auditoria.agent_type IS
  'main (Nacom) | agente_lojas | gestor-estoque-odoo | gestor-recebimento | worker_rq | scheduler | cli';
