-- ============================================================
-- Script SQL para RENDER: Remover UniqueConstraint de RecursosProducao
-- Permite múltiplas linhas de produção por produto
-- Data: 2025-01-26
-- ============================================================

-- Passo 1: Verificar constraints existentes
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'recursos_producao'
AND constraint_type = 'UNIQUE';

-- Passo 2: Remover constraint UNIQUE (ajuste o nome se necessário)
-- O nome pode variar, geralmente é 'recursos_producao_cod_produto_linha_producao_key'
ALTER TABLE recursos_producao
DROP CONSTRAINT IF EXISTS recursos_producao_cod_produto_linha_producao_key;

-- Caso o nome seja diferente, use este padrão genérico:
-- ALTER TABLE recursos_producao DROP CONSTRAINT <nome_da_constraint>;

-- Passo 3: Criar índice composto (não único) para performance
CREATE INDEX IF NOT EXISTS idx_recursos_produto_linha
ON recursos_producao(cod_produto, linha_producao);

-- Passo 4: Verificar resultado
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'recursos_producao';

-- ✅ Migração concluída!
-- RecursosProducao agora permite múltiplas linhas por produto
