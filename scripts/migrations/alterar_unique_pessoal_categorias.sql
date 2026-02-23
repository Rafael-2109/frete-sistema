-- ==============================================
-- Alterar UNIQUE de pessoal_categorias:
-- DE: nome (sozinho)
-- PARA: (grupo, nome) composto
--
-- Permite mesmo nome em grupos diferentes
-- Ex: "Salario" em "Receitas" e "Salario" em "Funcionarios"
-- ==============================================

-- Remover constraint antiga (nome sozinho)
DO $$
BEGIN
    -- Tenta dropar o index unique antigo (pode ter nomes diferentes)
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'pessoal_categorias' AND indexdef LIKE '%UNIQUE%nome%' AND indexdef NOT LIKE '%grupo%') THEN
        -- Identificar nome exato do constraint
        PERFORM 1;
    END IF;
END $$;

-- Dropar constraint/index existente sobre nome sozinho
ALTER TABLE pessoal_categorias DROP CONSTRAINT IF EXISTS pessoal_categorias_nome_key;
DROP INDEX IF EXISTS pessoal_categorias_nome_key;

-- Criar novo unique composto (grupo + nome)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_pessoal_categorias_grupo_nome'
    ) THEN
        ALTER TABLE pessoal_categorias
            ADD CONSTRAINT uq_pessoal_categorias_grupo_nome UNIQUE (grupo, nome);
    END IF;
END $$;
