-- =====================================================
-- FIX: Remover UNIQUE constraint de nome_grupo
-- Data: 24/10/2025
-- Problema: nome_grupo está com UNIQUE mas deveria permitir duplicatas
--           (um grupo pode ter vários prefixos)
-- =====================================================

-- 1. Verificar constraints existentes
SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'grupo_empresarial'::regclass;

-- 2. Verificar índices existentes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'grupo_empresarial';

-- 3. Remover constraint UNIQUE de nome_grupo (se existir)
-- Nome pode variar: ix_grupo_empresarial_nome_grupo ou grupo_empresarial_nome_grupo_key
DO $$
BEGIN
    -- Tentar dropar possíveis nomes de constraint
    BEGIN
        ALTER TABLE grupo_empresarial DROP CONSTRAINT IF EXISTS ix_grupo_empresarial_nome_grupo;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Constraint ix_grupo_empresarial_nome_grupo não existe';
    END;

    BEGIN
        ALTER TABLE grupo_empresarial DROP CONSTRAINT IF EXISTS grupo_empresarial_nome_grupo_key;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Constraint grupo_empresarial_nome_grupo_key não existe';
    END;

    BEGIN
        -- Dropar índice UNIQUE se existir
        DROP INDEX IF EXISTS ix_grupo_empresarial_nome_grupo;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Index ix_grupo_empresarial_nome_grupo não existe';
    END;
END$$;

-- 4. Recriar índice NORMAL (sem UNIQUE) para performance
CREATE INDEX IF NOT EXISTS idx_grupo_empresarial_nome ON grupo_empresarial(nome_grupo);

-- 5. Garantir que prefixo_cnpj continue UNIQUE
DO $$
BEGIN
    -- Adicionar constraint se não existir
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uk_prefixo_cnpj'
        AND conrelid = 'grupo_empresarial'::regclass
    ) THEN
        ALTER TABLE grupo_empresarial ADD CONSTRAINT uk_prefixo_cnpj UNIQUE (prefixo_cnpj);
    END IF;
END$$;

-- 6. Verificar resultado final
SELECT
    'Constraints atuais:' as tipo,
    conname as nome,
    pg_get_constraintdef(oid) as definicao
FROM pg_constraint
WHERE conrelid = 'grupo_empresarial'::regclass

UNION ALL

SELECT
    'Índices atuais:' as tipo,
    indexname as nome,
    indexdef as definicao
FROM pg_indexes
WHERE tablename = 'grupo_empresarial';

-- 7. Comentário final
COMMENT ON TABLE grupo_empresarial IS 'Grupos empresariais - 1 linha por prefixo CNPJ (permite mesmo nome_grupo com prefixos diferentes)';
