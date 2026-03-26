-- Migration: Adicionar campos de alerta saida sem NF em carvia_cotacoes
-- Idempotente para Render Shell

DO $$
BEGIN
    -- alerta_saida_sem_nf
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'alerta_saida_sem_nf'
    ) THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN alerta_saida_sem_nf BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Coluna alerta_saida_sem_nf adicionada';
    END IF;

    -- alerta_saida_sem_nf_em
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'alerta_saida_sem_nf_em'
    ) THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN alerta_saida_sem_nf_em TIMESTAMP;
        RAISE NOTICE 'Coluna alerta_saida_sem_nf_em adicionada';
    END IF;

    -- alerta_saida_embarque_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'alerta_saida_embarque_id'
    ) THEN
        ALTER TABLE carvia_cotacoes ADD COLUMN alerta_saida_embarque_id INTEGER;
        RAISE NOTICE 'Coluna alerta_saida_embarque_id adicionada';
    END IF;
END $$;

-- Indice parcial
CREATE INDEX IF NOT EXISTS ix_carvia_cotacoes_alerta_saida
ON carvia_cotacoes (id) WHERE alerta_saida_sem_nf = TRUE;
