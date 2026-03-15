-- Migration: Adicionar campos de conferencia em carvia_subcontratos
-- Executar via Render Shell (SQL idempotente)

ALTER TABLE carvia_subcontratos ADD COLUMN IF NOT EXISTS valor_considerado NUMERIC(15,2);
ALTER TABLE carvia_subcontratos ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';
ALTER TABLE carvia_subcontratos ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100);
ALTER TABLE carvia_subcontratos ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP;
ALTER TABLE carvia_subcontratos ADD COLUMN IF NOT EXISTS detalhes_conferencia JSONB;

CREATE INDEX IF NOT EXISTS idx_carvia_subcontratos_status_conferencia
ON carvia_subcontratos (status_conferencia);
