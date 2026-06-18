-- Migration: UNIQUE(carvia_nf_id) em carvia_coleta_nfs — fix do redesign (stream 3)
-- Data: 2026-06-18
-- Descricao:
--   Uma CarviaNf real pertence a NO MAXIMO 1 linha de coleta (papel de pao). Sem esta
--   constraint, a mesma NF podia ser vinculada a N coletas -> o status do Portal do Cliente
--   (portal_status_service usa .first()) ficava ambiguo. NULL = rascunho (varios permitidos).
-- Idempotente (DO block checando pg_constraint). Constraint UNIQUE permite multiplos NULL no PG.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_carvia_coleta_nf'
    ) THEN
        ALTER TABLE carvia_coleta_nfs
            ADD CONSTRAINT uq_carvia_coleta_nf UNIQUE (carvia_nf_id);
    END IF;
END $$;
