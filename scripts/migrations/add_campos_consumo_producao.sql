-- ============================================================
-- Script de migracao: Campos de vinculacao de consumo/producao
-- Tabela: movimentacao_estoque
-- Para rodar no Shell do Render
-- Data: 2025-12-09
-- ============================================================

-- 1. operacao_producao_id - PseudoID da operacao
-- Formato: PROD_YYYYMMDD_HHMMSS_XXXX
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS operacao_producao_id VARCHAR(50) NULL;

-- 2. tipo_origem_producao - Tipo de origem da movimentacao
-- Valores: RAIZ, CONSUMO_DIRETO, PRODUCAO_AUTO, CONSUMO_AUTO
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS tipo_origem_producao VARCHAR(20) NULL;

-- 3. cod_produto_raiz - Codigo do produto raiz da operacao
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS cod_produto_raiz VARCHAR(50) NULL;

-- 4. producao_pai_id - FK para producao que gerou este consumo
ALTER TABLE movimentacao_estoque
ADD COLUMN IF NOT EXISTS producao_pai_id INTEGER NULL;

-- Adicionar FK constraint (ignorar se ja existe)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_movimentacao_producao_pai'
        AND table_name = 'movimentacao_estoque'
    ) THEN
        ALTER TABLE movimentacao_estoque
        ADD CONSTRAINT fk_movimentacao_producao_pai
        FOREIGN KEY (producao_pai_id)
        REFERENCES movimentacao_estoque(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- Criar indices para performance
CREATE INDEX IF NOT EXISTS idx_movimentacao_operacao ON movimentacao_estoque(operacao_producao_id);
CREATE INDEX IF NOT EXISTS idx_movimentacao_produto_raiz ON movimentacao_estoque(cod_produto_raiz);
CREATE INDEX IF NOT EXISTS idx_movimentacao_producao_pai ON movimentacao_estoque(producao_pai_id);

-- Verificar resultado
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'movimentacao_estoque'
AND column_name IN ('operacao_producao_id', 'tipo_origem_producao', 'cod_produto_raiz', 'producao_pai_id')
ORDER BY column_name;
