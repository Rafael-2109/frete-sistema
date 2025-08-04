-- Script COMPLETO para corrigir a tabela saldo_estoque_cache no Render
-- Adiciona as colunas criado_em e atualizado_em que estão faltando

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'saldo_estoque_cache') THEN
        RAISE NOTICE 'Tabela saldo_estoque_cache existe, adicionando colunas faltantes...';
        
        -- Adicionar criado_em se não existir
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'criado_em') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            RAISE NOTICE 'Coluna criado_em adicionada';
        ELSE
            RAISE NOTICE 'Coluna criado_em já existe';
        END IF;
        
        -- Adicionar atualizado_em se não existir
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'atualizado_em') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            RAISE NOTICE 'Coluna atualizado_em adicionada';
        ELSE
            RAISE NOTICE 'Coluna atualizado_em já existe';
        END IF;
        
        RAISE NOTICE 'Verificação e correção concluídas!';
    ELSE
        RAISE NOTICE 'Tabela não existe - criando com estrutura completa...';
        
        CREATE TABLE saldo_estoque_cache (
            id SERIAL PRIMARY KEY,
            cod_produto VARCHAR(50) NOT NULL,
            nome_produto VARCHAR(255),
            saldo_atual NUMERIC(15,3) DEFAULT 0,
            qtd_carteira NUMERIC(15,3) DEFAULT 0,
            qtd_pre_separacao NUMERIC(15,3) DEFAULT 0,
            qtd_separacao NUMERIC(15,3) DEFAULT 0,
            previsao_ruptura_7d DATE,
            status_ruptura VARCHAR(20),
            ultima_atualizacao_saldo TIMESTAMP,
            ultima_atualizacao_carteira TIMESTAMP,
            ultima_atualizacao_projecao TIMESTAMP,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX idx_saldo_estoque_cache_produto ON saldo_estoque_cache(cod_produto);
        CREATE INDEX idx_saldo_estoque_cache_ruptura ON saldo_estoque_cache(status_ruptura);
        
        RAISE NOTICE 'Tabela criada com sucesso!';
    END IF;
END $$;

-- Mostrar estrutura final
\d saldo_estoque_cache

-- Contar registros
SELECT COUNT(*) as total_registros FROM saldo_estoque_cache;