-- ============================================================
-- Migration: Adicionar campo status + auditoria em carvia_nfs
-- Executar no Render Shell (psql) — idempotente
-- ============================================================

BEGIN;

-- 1. Campo status (ATIVA / CANCELADA)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_nfs' AND column_name = 'status'
    ) THEN
        ALTER TABLE carvia_nfs
            ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ATIVA';
        RAISE NOTICE 'Coluna status adicionada a carvia_nfs';
    ELSE
        RAISE NOTICE 'Coluna status ja existe em carvia_nfs';
    END IF;
END $$;

-- 2. Campo cancelado_em (timestamp de cancelamento)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_nfs' AND column_name = 'cancelado_em'
    ) THEN
        ALTER TABLE carvia_nfs ADD COLUMN cancelado_em TIMESTAMP;
        RAISE NOTICE 'Coluna cancelado_em adicionada a carvia_nfs';
    ELSE
        RAISE NOTICE 'Coluna cancelado_em ja existe em carvia_nfs';
    END IF;
END $$;

-- 3. Campo cancelado_por (usuario que cancelou)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_nfs' AND column_name = 'cancelado_por'
    ) THEN
        ALTER TABLE carvia_nfs ADD COLUMN cancelado_por VARCHAR(100);
        RAISE NOTICE 'Coluna cancelado_por adicionada a carvia_nfs';
    ELSE
        RAISE NOTICE 'Coluna cancelado_por ja existe em carvia_nfs';
    END IF;
END $$;

-- 4. Campo motivo_cancelamento (texto livre)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_nfs' AND column_name = 'motivo_cancelamento'
    ) THEN
        ALTER TABLE carvia_nfs ADD COLUMN motivo_cancelamento TEXT;
        RAISE NOTICE 'Coluna motivo_cancelamento adicionada a carvia_nfs';
    ELSE
        RAISE NOTICE 'Coluna motivo_cancelamento ja existe em carvia_nfs';
    END IF;
END $$;

-- 5. Indice no campo status
CREATE INDEX IF NOT EXISTS ix_carvia_nfs_status ON carvia_nfs (status);

-- Verificacao
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'carvia_nfs'
  AND column_name IN ('status', 'cancelado_em', 'cancelado_por', 'motivo_cancelamento')
ORDER BY ordinal_position;

COMMIT;
