-- ============================================================
-- MIGRAÇÃO: Adicionar campos de controle de pagamento
-- Data: 2025-01-04
-- Descrição: Campos para contas a pagar (motos e montagens)
-- ============================================================

-- 1. TABELA MOTO - Controle de Pagamento do Custo de Aquisição
ALTER TABLE moto
ADD COLUMN IF NOT EXISTS custo_pago NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS data_pagamento_custo DATE,
ADD COLUMN IF NOT EXISTS status_pagamento_custo VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL;

CREATE INDEX IF NOT EXISTS idx_moto_status_pagamento ON moto(status_pagamento_custo);

COMMENT ON COLUMN moto.custo_pago IS 'Valor efetivamente pago ao fornecedor';
COMMENT ON COLUMN moto.data_pagamento_custo IS 'Data do pagamento do custo de aquisição';
COMMENT ON COLUMN moto.status_pagamento_custo IS 'PENDENTE, PAGO, PARCIAL';


-- 2. TABELA PEDIDO_VENDA_MOTO_ITEM - Controle de Pagamento da Montagem
ALTER TABLE pedido_venda_moto_item
ADD COLUMN IF NOT EXISTS fornecedor_montagem VARCHAR(100),
ADD COLUMN IF NOT EXISTS montagem_paga BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS data_pagamento_montagem DATE;

CREATE INDEX IF NOT EXISTS idx_montagem_paga ON pedido_venda_moto_item(montagem_paga);

COMMENT ON COLUMN pedido_venda_moto_item.fornecedor_montagem IS 'Equipe terceirizada responsável pela montagem';
COMMENT ON COLUMN pedido_venda_moto_item.montagem_paga IS 'Indica se a montagem foi paga';
COMMENT ON COLUMN pedido_venda_moto_item.data_pagamento_montagem IS 'Data do pagamento da montagem';


-- ============================================================
-- VERIFICAÇÃO FINAL
-- ============================================================

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'moto'
AND column_name IN ('custo_pago', 'data_pagamento_custo', 'status_pagamento_custo')
ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto_item'
AND column_name IN ('fornecedor_montagem', 'montagem_paga', 'data_pagamento_montagem')
ORDER BY ordinal_position;

-- ============================================================
-- FIM DA MIGRAÇÃO
-- ============================================================
