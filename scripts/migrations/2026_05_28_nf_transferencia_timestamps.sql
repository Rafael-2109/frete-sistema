-- Migration 2026-05-28: adiciona timestamps (data+hora) em nf_transferencia_snapshot.
--
-- Complementa o campo `data_emissao` (Date) com:
--   - `data_emissao_hora` (DateTime) — timestamp completo da emissao da NF origem
--   - `picking_data_hora` (DateTime) — date_done do picking destino
--   - `invoice_destino_data_hora` (DateTime) — create_date do invoice destino
--
-- Idempotente: ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+).
-- Guard: bloco DO $$ verifica se a tabela pai existe ANTES do ALTER. Se
-- a migration `nf_transferencia_snapshot` falhou (build.sh 22c.1), este
-- script PULA silenciosamente em vez de levantar `relation does not exist`
-- (que IF NOT EXISTS em ADD COLUMN NAO suprime).

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'nf_transferencia_snapshot'
    ) THEN
        ALTER TABLE nf_transferencia_snapshot
            ADD COLUMN IF NOT EXISTS data_emissao_hora TIMESTAMP;
        ALTER TABLE nf_transferencia_snapshot
            ADD COLUMN IF NOT EXISTS picking_data_hora TIMESTAMP;
        ALTER TABLE nf_transferencia_snapshot
            ADD COLUMN IF NOT EXISTS invoice_destino_data_hora TIMESTAMP;
    ELSE
        RAISE NOTICE 'Tabela nf_transferencia_snapshot ausente; pulando ALTER (rodar migration nf_transferencia_snapshot primeiro)';
    END IF;
END $$;
