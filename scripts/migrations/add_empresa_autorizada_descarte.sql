-- Migration: Adiciona campos de empresa autorizada ao descarte de devolucao
-- Executar no Shell do Render

ALTER TABLE descarte_devolucao
ADD COLUMN IF NOT EXISTS empresa_autorizada_nome VARCHAR(255),
ADD COLUMN IF NOT EXISTS empresa_autorizada_documento VARCHAR(20),
ADD COLUMN IF NOT EXISTS empresa_autorizada_tipo VARCHAR(20) DEFAULT 'TRANSPORTADOR';
