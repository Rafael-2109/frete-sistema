-- Migration: Adicionar campos de Recebimento CD via DFe (Fase 7)
-- Tabela: recebimento_lf
-- Data: 2026-02-13
--
-- Executar no Render Shell:
--   psql $DATABASE_URL -f adicionar_campos_recebimento_cd.sql

-- Novos campos para Fase 7 (Recebimento CD via DFe)
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_cd_dfe_id INTEGER;
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_cd_po_id INTEGER;
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_cd_po_name VARCHAR(50);
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_cd_invoice_id INTEGER;
ALTER TABLE recebimento_lf ADD COLUMN IF NOT EXISTS odoo_cd_invoice_name VARCHAR(50);

-- Atualizar total_etapas para registros pendentes (que ainda nao completaram transfer)
UPDATE recebimento_lf
SET total_etapas = 37
WHERE transfer_status IS NULL
   OR transfer_status IN ('pendente', 'erro')
   OR (transfer_status = 'processando' AND etapa_atual < 24);

-- Resetar etapa para 23 em registros que estavam nas antigas etapas 24-25
-- (esses registros usavam o fluxo antigo de picking direto e precisam recomecar)
UPDATE recebimento_lf
SET etapa_atual = 23
WHERE etapa_atual IN (24, 25)
  AND transfer_status NOT IN ('concluido', 'sem_transferencia');

-- Default para novos registros
ALTER TABLE recebimento_lf ALTER COLUMN total_etapas SET DEFAULT 37;
