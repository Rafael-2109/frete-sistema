-- Migration: Memory System v2 — Taxonomia + Feedback Loop
-- Adiciona category, is_permanent, is_cold, usage tracking e conflict detection
-- Idempotente: usa IF NOT EXISTS / column_name checks

-- 1. category: classificacao da memoria (permanent, structural, operational, contextual, cold)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'category'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'operational';
        CREATE INDEX IF NOT EXISTS ix_agent_memories_category ON agent_memories (category);
    END IF;
END $$;

-- 2. is_permanent: memorias que NUNCA decaem ou sao consolidadas
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'is_permanent'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN is_permanent BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- 3. is_cold: memorias movidas para tier frio (sem injecao automatica)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'is_cold'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN is_cold BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- 4. usage_count: quantas vezes foi injetada no contexto
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'usage_count'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

-- 5. effective_count: quantas vezes o Agent usou conteudo desta memoria
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'effective_count'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN effective_count INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

-- 6. correction_count: quantas vezes usuario corrigiu apos injecao
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'correction_count'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN correction_count INTEGER NOT NULL DEFAULT 0;
    END IF;
END $$;

-- 7. has_potential_conflict: flag de contradicao detectada
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'agent_memories' AND column_name = 'has_potential_conflict'
    ) THEN
        ALTER TABLE agent_memories ADD COLUMN has_potential_conflict BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- 8. Backfill: classificar memorias existentes por path
-- corrections/ com keywords estruturais → structural
UPDATE agent_memories
SET category = 'structural', is_permanent = FALSE
WHERE category = 'operational'
  AND path LIKE '/memories/corrections/%'
  AND (
    lower(content) LIKE '%timeout%'
    OR lower(content) LIKE '%campo%'
    OR lower(content) LIKE '%fk%'
    OR lower(content) LIKE '%constraint%'
    OR lower(content) LIKE '%empresa%'
    OR lower(content) LIKE '%odoo%'
    OR lower(content) LIKE '%nao existe%'
    OR lower(content) LIKE '%não existe%'
  );

-- corrections/ com keywords de escopo/permanentes → permanent
UPDATE agent_memories
SET category = 'permanent', is_permanent = TRUE
WHERE category IN ('operational', 'structural')
  AND path LIKE '/memories/corrections/%'
  AND (
    lower(content) LIKE '%scope%'
    OR lower(content) LIKE '%escopo%'
    OR lower(content) LIKE '%permissao%'
    OR lower(content) LIKE '%permissão%'
    OR lower(content) LIKE '%regra%'
    OR lower(content) LIKE '%nunca%fazer%'
    OR lower(content) LIKE '%sempre%fazer%'
    OR lower(content) LIKE '%proibido%'
    OR lower(content) LIKE '%obrigatorio%'
    OR lower(content) LIKE '%obrigatório%'
  );

-- user.xml e preferences.xml → permanent
UPDATE agent_memories
SET category = 'permanent', is_permanent = TRUE
WHERE path IN ('/memories/user.xml', '/memories/preferences.xml');

-- context/ → contextual
UPDATE agent_memories
SET category = 'contextual'
WHERE category = 'operational'
  AND path LIKE '/memories/context/%';

-- Remaining corrections/ que nao foram classificados → structural (default para corrections)
UPDATE agent_memories
SET category = 'structural'
WHERE category = 'operational'
  AND path LIKE '/memories/corrections/%';

-- 9. Indice parcial para memorias nao-frias (otimiza retrieval)
CREATE INDEX IF NOT EXISTS ix_agent_memories_not_cold
    ON agent_memories (user_id, category)
    WHERE is_cold = FALSE;
