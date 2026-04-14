-- Migration: adiciona origem em entregas_monitoradas (NACOM | CARVIA)
--
-- Contexto: NFs do subsistema CarVia (frete subcontratado) passam a coexistir
-- com NFs Nacom em EntregaMonitorada. O discriminador `origem` evita colisao
-- de numero_nf entre os dois dominios (emitentes CarVia tem numeracao propria).
--
-- Default 'NACOM' preserva todos os registros existentes. O codigo CarVia
-- inserira novos registros com origem='CARVIA'.
--
-- Idempotente: IF NOT EXISTS.

ALTER TABLE entregas_monitoradas
    ADD COLUMN IF NOT EXISTS origem VARCHAR(10) NOT NULL DEFAULT 'NACOM';

CREATE INDEX IF NOT EXISTS idx_em_origem
    ON entregas_monitoradas(origem);
