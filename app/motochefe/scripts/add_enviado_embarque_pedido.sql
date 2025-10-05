-- ============================================================
-- MIGRAÇÃO: Adicionar campo 'enviado' em EmbarquePedido
-- Data: 2025-01-04
-- Descrição: Campo boolean para controlar envio e trigger de rateio
-- ============================================================

-- Adicionar coluna 'enviado' na tabela embarque_pedido
ALTER TABLE embarque_pedido
ADD COLUMN enviado BOOLEAN NOT NULL DEFAULT FALSE;

-- Criar índice para performance em consultas
CREATE INDEX idx_embarque_pedido_enviado ON embarque_pedido(enviado);

-- Comentários para documentação
COMMENT ON COLUMN embarque_pedido.enviado IS 'Marca se pedido foi enviado. Trigger: calcula rateio e marca PedidoVendaMoto.enviado=True';

-- Verificar estrutura
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'embarque_pedido'
ORDER BY ordinal_position;

-- ============================================================
-- FIM DA MIGRAÇÃO
-- ============================================================
