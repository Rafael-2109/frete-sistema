-- Migration: Criar tabela grupo_empresarial com 1 prefixo por linha
-- Data: 24/08/2025
-- Objetivo: Estrutura normalizada - 1 linha por prefixo CNPJ

-- psql $DATABASE_URL < migrations/manufatura_grupo_empresarial_ajuste.sql

-- 1. Dropar tabela antiga se existir (cuidado em produção!)
DROP TABLE IF EXISTS grupo_empresarial CASCADE;

-- 2. Criar nova estrutura
CREATE TABLE grupo_empresarial (
    id SERIAL PRIMARY KEY,
    nome_grupo VARCHAR(100) NOT NULL,
    prefixo_cnpj VARCHAR(8) NOT NULL,
    descricao VARCHAR(255),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT uk_prefixo_cnpj UNIQUE (prefixo_cnpj)
);

-- 3. Criar índices para performance
CREATE INDEX idx_grupo_empresarial_nome ON grupo_empresarial(nome_grupo);
CREATE INDEX idx_grupo_empresarial_prefixo ON grupo_empresarial(prefixo_cnpj);
CREATE INDEX idx_grupo_prefixo_composto ON grupo_empresarial(nome_grupo, prefixo_cnpj);

-- 4. Comentários para documentação
COMMENT ON TABLE grupo_empresarial IS 'Grupos empresariais - 1 linha por prefixo CNPJ';
COMMENT ON COLUMN grupo_empresarial.nome_grupo IS 'Nome do grupo (ex: Atacadão, Carrefour)';
COMMENT ON COLUMN grupo_empresarial.prefixo_cnpj IS 'Prefixo CNPJ - 8 primeiros dígitos';
COMMENT ON COLUMN grupo_empresarial.descricao IS 'Descrição do grupo empresarial';

-- 5. Inserir dados de exemplo (OPCIONAL - remover em produção)
/*
INSERT INTO grupo_empresarial (nome_grupo, prefixo_cnpj, descricao, criado_por) VALUES
('Atacadão', '75315333', 'Rede Atacadão', 'Sistema'),
('Atacadão', '10776574', 'Rede Atacadão', 'Sistema'),
('Carrefour', '45543915', 'Grupo Carrefour', 'Sistema'),
('Carrefour', '09808432', 'Grupo Carrefour', 'Sistema');
*/