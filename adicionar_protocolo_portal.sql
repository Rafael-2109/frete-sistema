-- =====================================================
-- ADICIONAR CAMPO protocolo NA TABELA portal_integracoes
-- =====================================================
-- Data: Novembro 2024
-- Motivo: Unificar campos protocolo_portal para protocolo
-- =====================================================

-- 1. Verificar se a tabela existe
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'portal_integracoes') THEN
        RAISE NOTICE 'Tabela portal_integracoes encontrada';
    ELSE
        RAISE EXCEPTION 'Tabela portal_integracoes NÃO existe! Criar tabela primeiro.';
    END IF;
END $$;

-- 2. Verificar se o campo protocolo já existe
DO $$ 
BEGIN 
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'portal_integracoes' 
        AND column_name = 'protocolo'
    ) THEN
        RAISE NOTICE 'Campo protocolo JÁ EXISTE na tabela portal_integracoes';
    ELSE
        -- 3. Adicionar campo protocolo se não existir
        ALTER TABLE portal_integracoes 
        ADD COLUMN protocolo VARCHAR(100);
        
        RAISE NOTICE 'Campo protocolo ADICIONADO com sucesso!';
    END IF;
END $$;

-- 4. Criar índice único no protocolo (permite múltiplos NULL)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE tablename = 'portal_integracoes'
        AND indexname = 'ix_portal_integracoes_protocolo'
    ) THEN
        CREATE UNIQUE INDEX ix_portal_integracoes_protocolo 
        ON portal_integracoes(protocolo) 
        WHERE protocolo IS NOT NULL;
        
        RAISE NOTICE 'Índice único criado no campo protocolo';
    ELSE
        RAISE NOTICE 'Índice já existe';
    END IF;
END $$;

-- 5. Se existir campo protocolo_portal, migrar dados
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'portal_integracoes' 
        AND column_name = 'protocolo_portal'
    ) THEN
        -- Copiar dados de protocolo_portal para protocolo
        UPDATE portal_integracoes 
        SET protocolo = protocolo_portal 
        WHERE protocolo_portal IS NOT NULL 
        AND protocolo IS NULL;
        
        RAISE NOTICE 'Dados migrados de protocolo_portal para protocolo';
        
        -- Opcional: remover campo antigo (comentado por segurança)
        -- ALTER TABLE portal_integracoes DROP COLUMN protocolo_portal;
        -- RAISE NOTICE 'Campo protocolo_portal REMOVIDO';
    END IF;
END $$;

-- 6. Verificar estrutura final da tabela
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'portal_integracoes'
AND column_name IN ('protocolo', 'protocolo_portal')
ORDER BY ordinal_position;

-- 7. Mostrar estatísticas do campo protocolo
SELECT 
    COUNT(*) as total_registros,
    COUNT(protocolo) as registros_com_protocolo,
    COUNT(*) - COUNT(protocolo) as registros_sem_protocolo
FROM portal_integracoes;

-- 8. Mostrar alguns registros de exemplo
SELECT 
    id,
    portal,
    lote_id,
    protocolo,
    status,
    criado_em
FROM portal_integracoes
ORDER BY criado_em DESC
LIMIT 10;

-- =====================================================
-- FIM DA MIGRAÇÃO
-- =====================================================
-- Para executar este script:
-- psql -U seu_usuario -d nome_do_banco -f adicionar_protocolo_portal.sql
-- 
-- Ou no psql:
-- \i adicionar_protocolo_portal.sql
-- =====================================================