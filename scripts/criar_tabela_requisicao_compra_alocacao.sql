-- =====================================================
-- Script SQL: Criar tabela requisicao_compra_alocacao
-- =====================================================
--
-- Tabela intermediária N:N entre RequisicaoCompras e PedidoCompras
-- Mapeia purchase.request.allocation do Odoo
--
-- Autor: Sistema de Fretes
-- Data: 01/11/2025
-- =====================================================

-- Dropar tabela se existir (CUIDADO EM PRODUÇÃO!)
-- DROP TABLE IF EXISTS requisicao_compra_alocacao CASCADE;

-- Criar tabela
CREATE TABLE requisicao_compra_alocacao (
    -- PK
    id SERIAL PRIMARY KEY,

    -- FKs para relacionamentos
    requisicao_compra_id INTEGER NOT NULL,
    pedido_compra_id INTEGER,

    -- IDs do Odoo (para sincronização)
    odoo_allocation_id VARCHAR(50) UNIQUE,
    purchase_request_line_odoo_id VARCHAR(50) NOT NULL,
    purchase_order_line_odoo_id VARCHAR(50),

    -- Produto (desnormalizado para queries rápidas)
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),

    -- Quantidades
    qtd_alocada NUMERIC(15, 3) NOT NULL,
    qtd_requisitada NUMERIC(15, 3) NOT NULL,
    qtd_aberta NUMERIC(15, 3) DEFAULT 0,

    -- Status
    purchase_state VARCHAR(20),
    stock_move_odoo_id VARCHAR(50),

    -- Controle
    importado_odoo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Datas Odoo
    create_date_odoo TIMESTAMP,
    write_date_odoo TIMESTAMP,

    -- FK Constraints
    CONSTRAINT fk_requisicao_compra
        FOREIGN KEY (requisicao_compra_id)
        REFERENCES requisicao_compras(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_pedido_compra
        FOREIGN KEY (pedido_compra_id)
        REFERENCES pedido_compras(id)
        ON DELETE SET NULL,

    -- Unique Constraints
    CONSTRAINT uq_allocation_request_order
        UNIQUE (purchase_request_line_odoo_id, purchase_order_line_odoo_id)
);

-- Criar índices
CREATE INDEX idx_alocacao_requisicao_compra_id ON requisicao_compra_alocacao (requisicao_compra_id);
CREATE INDEX idx_alocacao_pedido_compra_id ON requisicao_compra_alocacao (pedido_compra_id);
CREATE INDEX idx_alocacao_odoo_allocation_id ON requisicao_compra_alocacao (odoo_allocation_id);
CREATE INDEX idx_alocacao_purchase_request_line ON requisicao_compra_alocacao (purchase_request_line_odoo_id);
CREATE INDEX idx_alocacao_purchase_order_line ON requisicao_compra_alocacao (purchase_order_line_odoo_id);
CREATE INDEX idx_alocacao_cod_produto ON requisicao_compra_alocacao (cod_produto);
CREATE INDEX idx_alocacao_requisicao_pedido ON requisicao_compra_alocacao (requisicao_compra_id, pedido_compra_id);
CREATE INDEX idx_alocacao_produto_estado ON requisicao_compra_alocacao (cod_produto, purchase_state);
CREATE INDEX idx_alocacao_odoo_ids ON requisicao_compra_alocacao (purchase_request_line_odoo_id, purchase_order_line_odoo_id);

-- Comentários na tabela
COMMENT ON TABLE requisicao_compra_alocacao IS 'Tabela intermediária N:N entre Requisições de Compra e Pedidos de Compra (mapeia purchase.request.allocation do Odoo)';

-- Comentários em campos importantes
COMMENT ON COLUMN requisicao_compra_alocacao.odoo_allocation_id IS 'ID da alocação no Odoo (purchase.request.allocation.id)';
COMMENT ON COLUMN requisicao_compra_alocacao.purchase_request_line_odoo_id IS 'ID da linha de requisição no Odoo (purchase.request.line.id)';
COMMENT ON COLUMN requisicao_compra_alocacao.purchase_order_line_odoo_id IS 'ID da linha de pedido de compra no Odoo (purchase.order.line.id)';
COMMENT ON COLUMN requisicao_compra_alocacao.qtd_alocada IS 'Quantidade alocada do pedido para a requisição (allocated_product_qty)';
COMMENT ON COLUMN requisicao_compra_alocacao.qtd_requisitada IS 'Quantidade requisitada original (requested_product_uom_qty)';
COMMENT ON COLUMN requisicao_compra_alocacao.qtd_aberta IS 'Quantidade ainda em aberto (open_product_qty)';
COMMENT ON COLUMN requisicao_compra_alocacao.purchase_state IS 'Estado do pedido de compra (draft, sent, purchase, done, cancel)';

-- Verificar criação
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'requisicao_compra_alocacao'
ORDER BY ordinal_position;
