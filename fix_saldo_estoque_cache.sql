-- Script para corrigir a tabela saldo_estoque_cache no Render
-- Adiciona a coluna saldo_atual que está faltando

-- 1. Verificar se a tabela existe
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'saldo_estoque_cache') THEN
        RAISE NOTICE 'Tabela saldo_estoque_cache existe';
        
        -- 2. Adicionar coluna saldo_atual se não existir
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'saldo_atual') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN saldo_atual NUMERIC(15,3) DEFAULT 0;
            RAISE NOTICE 'Coluna saldo_atual adicionada';
        ELSE
            RAISE NOTICE 'Coluna saldo_atual já existe';
        END IF;
        
        -- 3. Verificar e adicionar outras colunas que podem estar faltando
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'qtd_carteira') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN qtd_carteira NUMERIC(15,3) DEFAULT 0;
            RAISE NOTICE 'Coluna qtd_carteira adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'qtd_pre_separacao') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN qtd_pre_separacao NUMERIC(15,3) DEFAULT 0;
            RAISE NOTICE 'Coluna qtd_pre_separacao adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'qtd_separacao') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN qtd_separacao NUMERIC(15,3) DEFAULT 0;
            RAISE NOTICE 'Coluna qtd_separacao adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'previsao_ruptura_7d') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN previsao_ruptura_7d DATE;
            RAISE NOTICE 'Coluna previsao_ruptura_7d adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'status_ruptura') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN status_ruptura VARCHAR(20);
            RAISE NOTICE 'Coluna status_ruptura adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'ultima_atualizacao_saldo') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN ultima_atualizacao_saldo TIMESTAMP;
            RAISE NOTICE 'Coluna ultima_atualizacao_saldo adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'ultima_atualizacao_carteira') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN ultima_atualizacao_carteira TIMESTAMP;
            RAISE NOTICE 'Coluna ultima_atualizacao_carteira adicionada';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'saldo_estoque_cache' 
                      AND column_name = 'ultima_atualizacao_projecao') THEN
            ALTER TABLE saldo_estoque_cache 
            ADD COLUMN ultima_atualizacao_projecao TIMESTAMP;
            RAISE NOTICE 'Coluna ultima_atualizacao_projecao adicionada';
        END IF;
        
    ELSE
        -- Se a tabela não existe, criar ela completa
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
        
        RAISE NOTICE 'Tabela saldo_estoque_cache criada com sucesso';
    END IF;
END $$;

-- 4. Mostrar estrutura final da tabela
\d saldo_estoque_cache