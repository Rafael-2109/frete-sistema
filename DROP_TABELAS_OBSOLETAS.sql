-- Script para remover tabelas obsoletas do sistema de estoque
-- Data: 03/09/2025
-- Motivo: Padronização do sistema para usar apenas ServicoEstoqueSimples
--
-- ATENÇÃO: Execute este script apenas após garantir que o sistema está funcionando
-- corretamente sem estas tabelas. Faça backup antes de executar!
--
-- Para executar:
-- psql -U seu_usuario -d seu_banco -f DROP_TABELAS_OBSOLETAS.sql

-- Verificar se as tabelas existem antes de dropar
DO $$ 
BEGIN
    -- Drop tabela movimentacao_prevista se existir
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'movimentacao_prevista') THEN
        DROP TABLE movimentacao_prevista CASCADE;
        RAISE NOTICE 'Tabela movimentacao_prevista removida com sucesso';
    ELSE
        RAISE NOTICE 'Tabela movimentacao_prevista não existe';
    END IF;

    -- Drop tabela estoque_tempo_real se existir
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'estoque_tempo_real') THEN
        DROP TABLE estoque_tempo_real CASCADE;
        RAISE NOTICE 'Tabela estoque_tempo_real removida com sucesso';
    ELSE
        RAISE NOTICE 'Tabela estoque_tempo_real não existe';
    END IF;

    -- Drop triggers relacionados se existirem
    DROP TRIGGER IF EXISTS trg_atualizar_estoque_tempo_real ON movimentacao_estoque;
    DROP TRIGGER IF EXISTS trg_atualizar_movimentacao_prevista ON separacao;
    DROP TRIGGER IF EXISTS trg_atualizar_movimentacao_prevista_producao ON programacao_producao;
    
    RAISE NOTICE 'Limpeza de tabelas obsoletas concluída';
END $$;

-- Verificar tabelas restantes relacionadas ao estoque
SELECT 'Tabelas de estoque ativas:' as info;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%estoque%' OR table_name LIKE '%movimentacao%')
ORDER BY table_name;