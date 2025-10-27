-- =====================================================
-- FIX LOCAL: Remover UNIQUE de nome_grupo
-- =====================================================

-- 1. Verificar constraints atuais
SELECT 'CONSTRAINTS ATUAIS:' as info;
SELECT conname, pg_get_constraintdef(oid) as definicao
FROM pg_constraint
WHERE conrelid = 'grupo_empresarial'::regclass
ORDER BY conname;

-- 2. Verificar índices atuais
SELECT 'ÍNDICES ATUAIS:' as info;
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'grupo_empresarial'
ORDER BY indexname;

-- 3. Remover UNIQUE de nome_grupo (todos os nomes possíveis)
DROP INDEX IF EXISTS ix_grupo_empresarial_nome_grupo CASCADE;
DROP INDEX IF EXISTS idx_grupo_nome CASCADE;
DROP INDEX IF EXISTS idx_grupo_empresarial_nome_normal CASCADE;

-- 4. Recriar índice NORMAL (sem UNIQUE) em nome_grupo
CREATE INDEX IF NOT EXISTS idx_grupo_empresarial_nome ON grupo_empresarial(nome_grupo);

-- 5. Garantir UNIQUE em prefixo_cnpj
ALTER TABLE grupo_empresarial DROP CONSTRAINT IF EXISTS uk_prefixo_cnpj;
ALTER TABLE grupo_empresarial ADD CONSTRAINT uk_prefixo_cnpj UNIQUE (prefixo_cnpj);

-- 6. Verificar resultado final
SELECT 'CONSTRAINTS FINAIS:' as info;
SELECT conname, pg_get_constraintdef(oid) as definicao
FROM pg_constraint
WHERE conrelid = 'grupo_empresarial'::regclass
ORDER BY conname;

SELECT 'ÍNDICES FINAIS:' as info;
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'grupo_empresarial'
ORDER BY indexname;
