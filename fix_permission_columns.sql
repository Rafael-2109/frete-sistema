-- ============================================
-- SCRIPT DE CORREÇÃO DE COLUNAS DE PERMISSÕES
-- Para executar no Render Database Shell
-- ============================================

-- 1. Verificar estrutura atual da tabela permission_module
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'permission_module'
ORDER BY ordinal_position;

-- 2. Renomear colunas em permission_module (se existirem com nomes em inglês)
DO $$ 
BEGIN
    -- Renomear name para nome
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'name') THEN
        ALTER TABLE permission_module RENAME COLUMN name TO nome;
        RAISE NOTICE 'Coluna name renomeada para nome em permission_module';
    END IF;
    
    -- Renomear display_name para nome_exibicao
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'display_name') THEN
        ALTER TABLE permission_module RENAME COLUMN display_name TO nome_exibicao;
        RAISE NOTICE 'Coluna display_name renomeada para nome_exibicao em permission_module';
    END IF;
    
    -- Renomear description para descricao
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'description') THEN
        ALTER TABLE permission_module RENAME COLUMN description TO descricao;
        RAISE NOTICE 'Coluna description renomeada para descricao em permission_module';
    END IF;
    
    -- Renomear icon para icone
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'icon') THEN
        ALTER TABLE permission_module RENAME COLUMN icon TO icone;
        RAISE NOTICE 'Coluna icon renomeada para icone em permission_module';
    END IF;
    
    -- Renomear color para cor
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'color') THEN
        ALTER TABLE permission_module RENAME COLUMN color TO cor;
        RAISE NOTICE 'Coluna color renomeada para cor em permission_module';
    END IF;
    
    -- Renomear order para ordem
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'order') THEN
        ALTER TABLE permission_module RENAME COLUMN "order" TO ordem;
        RAISE NOTICE 'Coluna order renomeada para ordem em permission_module';
    END IF;
    
    -- Renomear active para ativo
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'active') THEN
        ALTER TABLE permission_module RENAME COLUMN active TO ativo;
        RAISE NOTICE 'Coluna active renomeada para ativo em permission_module';
    END IF;
    
    -- Renomear created_at para criado_em
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'created_at') THEN
        ALTER TABLE permission_module RENAME COLUMN created_at TO criado_em;
        RAISE NOTICE 'Coluna created_at renomeada para criado_em em permission_module';
    END IF;
    
    -- Renomear created_by para criado_por
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_module' AND column_name = 'created_by') THEN
        ALTER TABLE permission_module RENAME COLUMN created_by TO criado_por;
        RAISE NOTICE 'Coluna created_by renomeada para criado_por em permission_module';
    END IF;
END $$;

-- 3. Fazer o mesmo para permission_category
DO $$ 
BEGIN
    -- Renomear colunas em permission_category
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'name') THEN
        ALTER TABLE permission_category RENAME COLUMN name TO nome;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'display_name') THEN
        ALTER TABLE permission_category RENAME COLUMN display_name TO nome_exibicao;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'description') THEN
        ALTER TABLE permission_category RENAME COLUMN description TO descricao;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'icon') THEN
        ALTER TABLE permission_category RENAME COLUMN icon TO icone;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'color') THEN
        ALTER TABLE permission_category RENAME COLUMN color TO cor;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'order') THEN
        ALTER TABLE permission_category RENAME COLUMN "order" TO ordem;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'active') THEN
        ALTER TABLE permission_category RENAME COLUMN active TO ativo;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'created_at') THEN
        ALTER TABLE permission_category RENAME COLUMN created_at TO criado_em;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_category' AND column_name = 'created_by') THEN
        ALTER TABLE permission_category RENAME COLUMN created_by TO criado_por;
    END IF;
END $$;

-- 4. Fazer o mesmo para permission_submodule
DO $$ 
BEGIN
    -- Renomear colunas em permission_submodule
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'name') THEN
        ALTER TABLE permission_submodule RENAME COLUMN name TO nome;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'display_name') THEN
        ALTER TABLE permission_submodule RENAME COLUMN display_name TO nome_exibicao;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'description') THEN
        ALTER TABLE permission_submodule RENAME COLUMN description TO descricao;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'order') THEN
        ALTER TABLE permission_submodule RENAME COLUMN "order" TO ordem;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'active') THEN
        ALTER TABLE permission_submodule RENAME COLUMN active TO ativo;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'created_at') THEN
        ALTER TABLE permission_submodule RENAME COLUMN created_at TO criado_em;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'permission_submodule' AND column_name = 'created_by') THEN
        ALTER TABLE permission_submodule RENAME COLUMN created_by TO criado_por;
    END IF;
END $$;

-- 5. Criar dados básicos se não existirem
DO $$
BEGIN
    -- Criar categoria operacional se não existir
    IF NOT EXISTS (SELECT 1 FROM permission_category WHERE nome = 'operacional') THEN
        INSERT INTO permission_category (nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
        VALUES ('operacional', 'Operacional', 'Módulos operacionais do sistema', 'briefcase', '#007bff', 1, true);
    END IF;
    
    -- Criar categoria financeiro se não existir
    IF NOT EXISTS (SELECT 1 FROM permission_category WHERE nome = 'financeiro') THEN
        INSERT INTO permission_category (nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
        VALUES ('financeiro', 'Financeiro', 'Módulos financeiros', 'dollar-sign', '#28a745', 2, true);
    END IF;
    
    -- Criar categoria administrativo se não existir
    IF NOT EXISTS (SELECT 1 FROM permission_category WHERE nome = 'administrativo') THEN
        INSERT INTO permission_category (nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
        VALUES ('administrativo', 'Administrativo', 'Módulos administrativos', 'settings', '#6c757d', 3, true);
    END IF;
END $$;

-- 6. Criar módulos básicos
DO $$
DECLARE
    cat_id INTEGER;
BEGIN
    -- Obter ID da categoria operacional
    SELECT id INTO cat_id FROM permission_category WHERE nome = 'operacional' LIMIT 1;
    
    IF cat_id IS NOT NULL THEN
        -- Criar módulo pedidos
        IF NOT EXISTS (SELECT 1 FROM permission_module WHERE nome = 'pedidos') THEN
            INSERT INTO permission_module (category_id, nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
            VALUES (cat_id, 'pedidos', 'Pedidos', 'Gestão de pedidos', 'shopping-cart', '#007bff', 1, true);
        END IF;
        
        -- Criar módulo separacao
        IF NOT EXISTS (SELECT 1 FROM permission_module WHERE nome = 'separacao') THEN
            INSERT INTO permission_module (category_id, nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
            VALUES (cat_id, 'separacao', 'Separação', 'Gestão de separação', 'package', '#17a2b8', 2, true);
        END IF;
        
        -- Criar módulo embarques
        IF NOT EXISTS (SELECT 1 FROM permission_module WHERE nome = 'embarques') THEN
            INSERT INTO permission_module (category_id, nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
            VALUES (cat_id, 'embarques', 'Embarques', 'Gestão de embarques', 'truck', '#28a745', 3, true);
        END IF;
        
        -- Criar módulo monitoramento
        IF NOT EXISTS (SELECT 1 FROM permission_module WHERE nome = 'monitoramento') THEN
            INSERT INTO permission_module (category_id, nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
            VALUES (cat_id, 'monitoramento', 'Monitoramento', 'Monitoramento de entregas', 'map-pin', '#ffc107', 4, true);
        END IF;
        
        -- Criar módulo portaria
        IF NOT EXISTS (SELECT 1 FROM permission_module WHERE nome = 'portaria') THEN
            INSERT INTO permission_module (category_id, nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
            VALUES (cat_id, 'portaria', 'Portaria', 'Controle de portaria', 'shield', '#dc3545', 5, true);
        END IF;
    END IF;
    
    -- Obter ID da categoria financeiro
    SELECT id INTO cat_id FROM permission_category WHERE nome = 'financeiro' LIMIT 1;
    
    IF cat_id IS NOT NULL THEN
        -- Criar módulo faturamento
        IF NOT EXISTS (SELECT 1 FROM permission_module WHERE nome = 'faturamento') THEN
            INSERT INTO permission_module (category_id, nome, nome_exibicao, descricao, icone, cor, ordem, ativo)
            VALUES (cat_id, 'faturamento', 'Faturamento', 'Gestão de faturamento', 'file-text', '#28a745', 1, true);
        END IF;
    END IF;
END $$;

-- 7. Verificar resultado final
SELECT 
    'permission_module' as tabela,
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'permission_module'
ORDER BY ordinal_position;

-- 8. Testar query problemática
SELECT id, nome, nome_exibicao 
FROM permission_module 
WHERE nome = 'pedidos' AND ativo = true
LIMIT 1;

-- Mensagem final
SELECT 'Script executado com sucesso! Reinicie a aplicação para aplicar as mudanças.' as mensagem;