-- Adicionar campo data_pedido na tabela saldo_standby
-- Execute este SQL diretamente no banco de dados PostgreSQL

-- Adicionar a coluna data_pedido
ALTER TABLE saldo_standby 
ADD COLUMN IF NOT EXISTS data_pedido DATE;

-- Comentário sobre o campo
COMMENT ON COLUMN saldo_standby.data_pedido IS 'Data do pedido original';

-- Verificar se a coluna foi criada
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'saldo_standby' 
AND column_name = 'data_pedido';