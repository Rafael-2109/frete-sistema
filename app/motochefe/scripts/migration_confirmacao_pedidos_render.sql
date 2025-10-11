-- ============================================================================
-- MIGRATION: Sistema de Confirmação de Pedidos
-- Data: 2025-01-11
-- Autor: Claude AI
-- ============================================================================
-- Adiciona sistema de aprovação em duas etapas para inserção e cancelamento
-- de pedidos no módulo MotoChefe
-- ============================================================================

-- PASSO 1: Adicionar campo 'status' em pedido_venda_moto
-- ============================================================================

-- Adicionar coluna status (default APROVADO para manter compatibilidade)
ALTER TABLE pedido_venda_moto
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'APROVADO';

-- Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_pedido_status ON pedido_venda_moto(status);

-- Comentário
COMMENT ON COLUMN pedido_venda_moto.status IS 'Status de aprovação: PENDENTE, APROVADO, REJEITADO, CANCELADO';


-- PASSO 2: Criar tabela pedido_venda_auditoria
-- ============================================================================

CREATE TABLE IF NOT EXISTS pedido_venda_auditoria (
    id SERIAL PRIMARY KEY,

    -- Relacionamento
    pedido_id INTEGER NOT NULL REFERENCES pedido_venda_moto(id),

    -- Ação
    acao VARCHAR(20) NOT NULL,  -- INSERCAO, CANCELAMENTO

    -- Solicitação
    observacao TEXT,
    solicitado_por VARCHAR(100) NOT NULL,
    solicitado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Confirmação/Rejeição
    confirmado BOOLEAN NOT NULL DEFAULT FALSE,
    rejeitado BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_rejeicao TEXT,
    confirmado_por VARCHAR(100),
    confirmado_em TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_auditoria_pedido ON pedido_venda_auditoria(pedido_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON pedido_venda_auditoria(acao);
CREATE INDEX IF NOT EXISTS idx_auditoria_confirmado ON pedido_venda_auditoria(confirmado);
CREATE INDEX IF NOT EXISTS idx_auditoria_rejeitado ON pedido_venda_auditoria(rejeitado);
CREATE INDEX IF NOT EXISTS idx_auditoria_pendente ON pedido_venda_auditoria(confirmado, rejeitado);
CREATE INDEX IF NOT EXISTS idx_auditoria_acao_status ON pedido_venda_auditoria(acao, confirmado, rejeitado);

-- Comentários
COMMENT ON TABLE pedido_venda_auditoria IS 'Auditoria de ações sobre pedidos (inserção e cancelamento)';
COMMENT ON COLUMN pedido_venda_auditoria.acao IS 'Tipo de ação: INSERCAO ou CANCELAMENTO';
COMMENT ON COLUMN pedido_venda_auditoria.confirmado IS 'TRUE se ação foi aprovada';
COMMENT ON COLUMN pedido_venda_auditoria.rejeitado IS 'TRUE se ação foi rejeitada';


-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

-- Verificar se campo status foi adicionado
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'pedido_venda_moto'
AND column_name = 'status';

-- Verificar se tabela de auditoria foi criada
SELECT table_name
FROM information_schema.tables
WHERE table_name = 'pedido_venda_auditoria';

-- Verificar índices criados
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('pedido_venda_moto', 'pedido_venda_auditoria')
AND indexname LIKE '%status%' OR indexname LIKE '%auditoria%'
ORDER BY tablename, indexname;

-- ============================================================================
-- MIGRATION CONCLUÍDA
-- ============================================================================
