-- Permitir operacao_id NULL em carvia_subcontratos (R10: subcontrato pode existir antes da operacao)
ALTER TABLE carvia_subcontratos ALTER COLUMN operacao_id DROP NOT NULL;
