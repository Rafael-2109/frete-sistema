-- Migration: agente_artifacts (Artifacts no Agente Web)
-- Data: 2026-05-12
-- Ref: app/agente/services/artifact_service.py, app/agente/models.py (AgenteArtifact)
--
-- Tabela para persistir artifacts (bundle.html auto-contido) gerados pelo
-- agente via skill `gerando-artifact`. Build assincrono via worker RQ.
-- Bundle final fica no S3; tabela guarda metadados + estado de build.
--
-- Idempotente via IF NOT EXISTS.
-- Foreign keys: SEM FK explicita (mesmo padrao de agent_session_costs).
--   - user_id: sessoes podem ser deletadas, queremos preservar historico
--   - session_id: TEXT (UUID nosso), nao referencia agent_sessions com FK

CREATE TABLE IF NOT EXISTS agente_artifacts (
  id                  BIGSERIAL PRIMARY KEY,
  uuid                TEXT NOT NULL UNIQUE,
  user_id             INTEGER NOT NULL,
  session_id          TEXT NULL,
  titulo              TEXT NOT NULL,
  status              TEXT NOT NULL DEFAULT 'queued',
  s3_key              TEXT NULL,
  bundle_size_bytes   BIGINT NULL,
  error_message       TEXT NULL,
  spec_json           JSONB NULL,
  created_at          TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
  expires_at          TIMESTAMP NOT NULL,
  build_started_at    TIMESTAMP NULL,
  build_completed_at  TIMESTAMP NULL
);

-- Lookup principal: por uuid (vem do token assinado na URL)
-- Ja coberto pelo UNIQUE constraint acima.

-- Listar artifacts do usuario (mais recentes primeiro)
CREATE INDEX IF NOT EXISTS agente_artifacts_user_created_idx
  ON agente_artifacts (user_id, created_at DESC);

-- Worker polling: artifacts pendentes de build
CREATE INDEX IF NOT EXISTS agente_artifacts_status_pending_idx
  ON agente_artifacts (status)
  WHERE status IN ('queued', 'building');

-- Cleanup job: artifacts expirados
CREATE INDEX IF NOT EXISTS agente_artifacts_expires_idx
  ON agente_artifacts (expires_at)
  WHERE status != 'expired';

-- Filtro por sessao (debug + auditoria)
CREATE INDEX IF NOT EXISTS agente_artifacts_session_idx
  ON agente_artifacts (session_id)
  WHERE session_id IS NOT NULL;

-- Check constraint: status valido
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'agente_artifacts_status_check'
  ) THEN
    ALTER TABLE agente_artifacts
      ADD CONSTRAINT agente_artifacts_status_check
      CHECK (status IN ('queued', 'building', 'ready', 'error', 'expired'));
  END IF;
END $$;

COMMENT ON TABLE agente_artifacts IS
  'Artifacts (bundle.html auto-contido) gerados pelo agente via skill '
  'gerando-artifact. Build async via RQ (queue artifacts). Bundle no S3 '
  '(prefix agente/artifacts/). Sem FK para users/agent_sessions — preserva '
  'historico apos cascade delete. uuid e referenciado externamente via token '
  'assinado (itsdangerous, TTL via expires_at).';

COMMENT ON COLUMN agente_artifacts.uuid IS
  'UUID4 stable do artifact. Vai dentro do token assinado da URL publica.';

COMMENT ON COLUMN agente_artifacts.status IS
  'queued -> building -> ready|error. expired setado por job de cleanup.';

COMMENT ON COLUMN agente_artifacts.s3_key IS
  'Path S3 do bundle.html. Formato: agente/artifacts/{user_id}/{uuid}.html. '
  'NULL ate status=ready.';

COMMENT ON COLUMN agente_artifacts.spec_json IS
  'Spec do artifact: { titulo, descricao, componentes[{path, content}], '
  'dependencies[] }. Usado pelo worker para reconstruir projeto e buildar.';

COMMENT ON COLUMN agente_artifacts.expires_at IS
  'TTL padrao 7 dias. Apos expirar, cleanup job seta status=expired e '
  'delete do S3.';
