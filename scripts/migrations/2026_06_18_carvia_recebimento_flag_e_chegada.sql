-- Migration: flag de acesso 'Recebimento CarVia' + previsao de chegada da Coleta
-- Data: 2026-06-18
-- Descricao:
--   (1) usuarios.acesso_recebimento_carvia (BOOL) — libera SO o recebimento por chassi das
--       Coletas CarVia para operadores sem o sistema CarVia completo (sem ver valores).
--   (2) carvia_coletas.data_prevista_chegada (DATE) — previsao de chegada na matriz/CD,
--       ao lado da previsao de coleta (data_prevista).
-- Idempotente (ADD COLUMN IF NOT EXISTS). Metadata-only no PG11+.

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS acesso_recebimento_carvia BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE carvia_coletas
    ADD COLUMN IF NOT EXISTS data_prevista_chegada DATE;
