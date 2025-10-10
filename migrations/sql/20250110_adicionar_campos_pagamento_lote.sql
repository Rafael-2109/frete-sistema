-- ============================================================================
-- MIGRAÇÃO: Adicionar campos para controle de pagamento em lote
-- Data: 10/01/2025
-- Ambiente: Render PostgreSQL
-- ============================================================================

-- ====================
-- 1. TABELA MOTO
-- ====================

-- Adicionar empresa_pagadora_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'moto' AND column_name = 'empresa_pagadora_id'
    ) THEN
        ALTER TABLE moto ADD COLUMN empresa_pagadora_id INTEGER;
        ALTER TABLE moto ADD CONSTRAINT fk_moto_empresa_pagadora
            FOREIGN KEY (empresa_pagadora_id) REFERENCES empresa_venda_moto(id);
        CREATE INDEX idx_moto_empresa_pagadora ON moto(empresa_pagadora_id);
    END IF;
END $$;

-- Adicionar lote_pagamento_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'moto' AND column_name = 'lote_pagamento_id'
    ) THEN
        ALTER TABLE moto ADD COLUMN lote_pagamento_id INTEGER;
        CREATE INDEX idx_moto_lote_pagamento ON moto(lote_pagamento_id);
    END IF;
END $$;

-- ====================
-- 2. TABELA COMISSAO_VENDEDOR
-- ====================

-- Adicionar empresa_pagadora_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comissao_vendedor' AND column_name = 'empresa_pagadora_id'
    ) THEN
        ALTER TABLE comissao_vendedor ADD COLUMN empresa_pagadora_id INTEGER;
        ALTER TABLE comissao_vendedor ADD CONSTRAINT fk_comissao_empresa_pagadora
            FOREIGN KEY (empresa_pagadora_id) REFERENCES empresa_venda_moto(id);
        CREATE INDEX idx_comissao_empresa_pagadora ON comissao_vendedor(empresa_pagadora_id);
    END IF;
END $$;

-- Adicionar lote_pagamento_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'comissao_vendedor' AND column_name = 'lote_pagamento_id'
    ) THEN
        ALTER TABLE comissao_vendedor ADD COLUMN lote_pagamento_id INTEGER;
        CREATE INDEX idx_comissao_lote_pagamento ON comissao_vendedor(lote_pagamento_id);
    END IF;
END $$;

-- ====================
-- 3. TABELA PEDIDO_VENDA_MOTO_ITEM
-- ====================

-- Adicionar empresa_pagadora_montagem_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pedido_venda_moto_item' AND column_name = 'empresa_pagadora_montagem_id'
    ) THEN
        ALTER TABLE pedido_venda_moto_item ADD COLUMN empresa_pagadora_montagem_id INTEGER;
        ALTER TABLE pedido_venda_moto_item ADD CONSTRAINT fk_item_empresa_pagadora_montagem
            FOREIGN KEY (empresa_pagadora_montagem_id) REFERENCES empresa_venda_moto(id);
        CREATE INDEX idx_item_empresa_pagadora_montagem ON pedido_venda_moto_item(empresa_pagadora_montagem_id);
    END IF;
END $$;

-- Adicionar lote_pagamento_montagem_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pedido_venda_moto_item' AND column_name = 'lote_pagamento_montagem_id'
    ) THEN
        ALTER TABLE pedido_venda_moto_item ADD COLUMN lote_pagamento_montagem_id INTEGER;
        CREATE INDEX idx_item_lote_pagamento_montagem ON pedido_venda_moto_item(lote_pagamento_montagem_id);
    END IF;
END $$;

-- ============================================================================
-- FIM DA MIGRAÇÃO
-- ============================================================================
