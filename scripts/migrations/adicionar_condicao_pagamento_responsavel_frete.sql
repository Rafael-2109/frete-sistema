-- Migration: Adicionar campos de condicao de pagamento e responsavel do frete
-- Executar via Render Shell (SQL idempotente)
-- Tabelas afetadas: carvia_cotacoes, carvia_operacoes, carvia_fretes

-- carvia_cotacoes
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(20);
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS prazo_dias INTEGER;
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS responsavel_frete VARCHAR(30);
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS percentual_remetente NUMERIC(5,2);
ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS percentual_destinatario NUMERIC(5,2);

-- carvia_operacoes
ALTER TABLE carvia_operacoes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(20);
ALTER TABLE carvia_operacoes ADD COLUMN IF NOT EXISTS prazo_dias INTEGER;
ALTER TABLE carvia_operacoes ADD COLUMN IF NOT EXISTS responsavel_frete VARCHAR(30);
ALTER TABLE carvia_operacoes ADD COLUMN IF NOT EXISTS percentual_remetente NUMERIC(5,2);
ALTER TABLE carvia_operacoes ADD COLUMN IF NOT EXISTS percentual_destinatario NUMERIC(5,2);

-- carvia_fretes
ALTER TABLE carvia_fretes ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(20);
ALTER TABLE carvia_fretes ADD COLUMN IF NOT EXISTS prazo_dias INTEGER;
ALTER TABLE carvia_fretes ADD COLUMN IF NOT EXISTS responsavel_frete VARCHAR(30);
ALTER TABLE carvia_fretes ADD COLUMN IF NOT EXISTS percentual_remetente NUMERIC(5,2);
ALTER TABLE carvia_fretes ADD COLUMN IF NOT EXISTS percentual_destinatario NUMERIC(5,2);
