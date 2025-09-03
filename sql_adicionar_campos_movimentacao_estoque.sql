-- ========================================
-- ADICIONAR CAMPOS ESTRUTURADOS EM MovimentacaoEstoque
-- Data: 01/09/2025
-- Objetivo: Substituir campo observacao texto livre por campos estruturados
-- ========================================

-- IMPORTANTE: Este script adiciona colunas sem remover a coluna observacao existente
-- para manter compatibilidade durante a transição

-- 1. Adicionar novos campos estruturados
ALTER TABLE movimentacao_estoque 
ADD COLUMN IF NOT EXISTS separacao_lote_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS numero_nf VARCHAR(20),
ADD COLUMN IF NOT EXISTS num_pedido VARCHAR(50),
ADD COLUMN IF NOT EXISTS tipo_origem VARCHAR(20),
ADD COLUMN IF NOT EXISTS status_nf VARCHAR(20),
ADD COLUMN IF NOT EXISTS codigo_embarque INTEGER;

-- 2. Adicionar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_movimentacao_lote 
ON movimentacao_estoque(separacao_lote_id);

CREATE INDEX IF NOT EXISTS idx_movimentacao_nf 
ON movimentacao_estoque(numero_nf);

CREATE INDEX IF NOT EXISTS idx_movimentacao_pedido 
ON movimentacao_estoque(num_pedido);

CREATE INDEX IF NOT EXISTS idx_movimentacao_tipo_origem 
ON movimentacao_estoque(tipo_origem);

CREATE INDEX IF NOT EXISTS idx_movimentacao_status_nf 
ON movimentacao_estoque(status_nf);

-- 3. Adicionar foreign key para embarque (se tabela existir)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'embarques') THEN
        ALTER TABLE movimentacao_estoque 
        ADD CONSTRAINT fk_movimentacao_embarque 
        FOREIGN KEY (codigo_embarque) 
        REFERENCES embarques(id)
        ON DELETE SET NULL;
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 4. Comentários nas colunas para documentação
COMMENT ON COLUMN movimentacao_estoque.separacao_lote_id IS 'ID do lote de separação relacionado';
COMMENT ON COLUMN movimentacao_estoque.numero_nf IS 'Número da nota fiscal';
COMMENT ON COLUMN movimentacao_estoque.num_pedido IS 'Número do pedido de origem';
COMMENT ON COLUMN movimentacao_estoque.tipo_origem IS 'Origem da movimentação: ODOO, TAGPLUS, MANUAL, LEGADO';
COMMENT ON COLUMN movimentacao_estoque.status_nf IS 'Status da NF: FATURADO, CANCELADO';
COMMENT ON COLUMN movimentacao_estoque.codigo_embarque IS 'ID do embarque relacionado';

-- 5. Adicionar novos campos em Separacao para sincronização
ALTER TABLE separacao
ADD COLUMN IF NOT EXISTS data_sincronizacao TIMESTAMP,
ADD COLUMN IF NOT EXISTS zerado_por_sync BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS data_zeragem TIMESTAMP;

-- Adicionar índice para sincronizado_nf se não existir
CREATE INDEX IF NOT EXISTS idx_separacao_sincronizado_nf 
ON separacao(sincronizado_nf);

-- 6. Migração de dados históricos (OPCIONAL - executar separadamente se necessário)
-- Extrai dados da observacao para os novos campos

-- Atualizar movimentações com lote no texto
UPDATE movimentacao_estoque 
SET 
    numero_nf = CASE 
        WHEN observacao LIKE '%NF %' THEN 
            SUBSTRING(observacao FROM 'NF ([0-9]+)')
        ELSE NULL 
    END,
    separacao_lote_id = CASE 
        WHEN observacao LIKE '%lote separação %' THEN 
            SUBSTRING(observacao FROM 'lote separação ([A-Za-z0-9-]+)')
        ELSE NULL 
    END,
    tipo_origem = CASE
        WHEN observacao LIKE '%TAGPLUS%' THEN 'TAGPLUS'
        WHEN observacao LIKE '%automática%' THEN 'ODOO'
        ELSE 'LEGADO'
    END,
    status_nf = 'FATURADO'
WHERE 
    numero_nf IS NULL 
    AND observacao IS NOT NULL
    AND observacao != '';

-- Marcar movimentações "Sem Separação" 
UPDATE movimentacao_estoque 
SET 
    tipo_origem = 'LEGADO',
    status_nf = 'FATURADO'
WHERE 
    observacao LIKE '%Sem Separação%'
    AND tipo_origem IS NULL;

-- 7. Estatísticas pós-migração
DO $$
DECLARE
    total_registros INTEGER;
    registros_com_nf INTEGER;
    registros_com_lote INTEGER;
    registros_legado INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_registros FROM movimentacao_estoque;
    SELECT COUNT(*) INTO registros_com_nf FROM movimentacao_estoque WHERE numero_nf IS NOT NULL;
    SELECT COUNT(*) INTO registros_com_lote FROM movimentacao_estoque WHERE separacao_lote_id IS NOT NULL;
    SELECT COUNT(*) INTO registros_legado FROM movimentacao_estoque WHERE tipo_origem = 'LEGADO';
    
    RAISE NOTICE '======================================';
    RAISE NOTICE 'MIGRAÇÃO CONCLUÍDA COM SUCESSO';
    RAISE NOTICE '======================================';
    RAISE NOTICE 'Total de registros: %', total_registros;
    RAISE NOTICE 'Registros com NF: %', registros_com_nf;
    RAISE NOTICE 'Registros com lote: %', registros_com_lote;
    RAISE NOTICE 'Registros legado: %', registros_legado;
    RAISE NOTICE '======================================';
END $$;