-- Migration: DROP campos de conferencia em carvia_subcontratos
-- DEVE ser executada APOS todas as migrations do plano e deploy do codigo.
-- Data: 2026-04-14

ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_pago;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_pago_em;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_pago_por;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS valor_considerado;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS status_conferencia;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS conferido_por;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS conferido_em;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS detalhes_conferencia;
ALTER TABLE carvia_subcontratos DROP COLUMN IF EXISTS requer_aprovacao;

-- Drop tambem subcontrato_id em carvia_conta_corrente_transportadoras
-- (foi deprecado ao adicionar frete_id na Phase 5)
ALTER TABLE carvia_conta_corrente_transportadoras DROP COLUMN IF EXISTS subcontrato_id;
ALTER TABLE carvia_conta_corrente_transportadoras DROP COLUMN IF EXISTS compensacao_subcontrato_id;
