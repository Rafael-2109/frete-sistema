-- Migration: CarviaNf.divergencia_cnpj_cotacao
-- Data: 2026-05-11
-- Motivo:
--   Sinalizar NFs CarVia cujo cnpj_destinatario diverge do cnpj do endereco
--   destino da cotacao vinculada. Setado automaticamente em
--   EmbarqueCarViaService.expandir_provisorio (Fase B2). Limpo apos operador
--   decidir (Fase B4: atualizar cotacao OU descartar divergencia).
-- Uso: Render Shell (psql) — SQL idempotente.

BEGIN;

-- =====================================================================
-- 1. carvia_nfs.divergencia_cnpj_cotacao
-- =====================================================================
ALTER TABLE carvia_nfs
    ADD COLUMN IF NOT EXISTS divergencia_cnpj_cotacao BOOLEAN NOT NULL DEFAULT FALSE;

-- Index parcial: so guarda linhas com divergencia (poucas), util para
-- contagens rapidas em UI ("X NFs com divergencia pendente").
CREATE INDEX IF NOT EXISTS ix_carvia_nfs_divergencia_cnpj
    ON carvia_nfs (divergencia_cnpj_cotacao)
    WHERE divergencia_cnpj_cotacao = TRUE;

-- =====================================================================
-- Verificacao
-- =====================================================================
SELECT
    divergencia_cnpj_cotacao,
    COUNT(*) AS total
FROM carvia_nfs
GROUP BY divergencia_cnpj_cotacao
ORDER BY divergencia_cnpj_cotacao;

COMMIT;
