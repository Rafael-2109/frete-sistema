-- Criar tabela cadastro_cliente para clientes não-Odoo
CREATE TABLE IF NOT EXISTS cadastro_cliente (
    id SERIAL PRIMARY KEY,
    
    -- Chave principal - CNPJ/CPF
    cnpj_cpf VARCHAR(20) NOT NULL UNIQUE,
    
    -- Dados básicos do cliente
    raz_social VARCHAR(255) NOT NULL,
    raz_social_red VARCHAR(100),
    
    -- Localização
    municipio VARCHAR(100) NOT NULL,
    estado VARCHAR(2) NOT NULL,
    
    -- Dados comerciais
    vendedor VARCHAR(100),
    equipe_vendas VARCHAR(100),
    
    -- Endereço de entrega padrão
    cnpj_endereco_ent VARCHAR(20),
    empresa_endereco_ent VARCHAR(255),
    cep_endereco_ent VARCHAR(10),
    nome_cidade VARCHAR(100),
    cod_uf VARCHAR(2),
    bairro_endereco_ent VARCHAR(100),
    rua_endereco_ent VARCHAR(255),
    endereco_ent VARCHAR(20),
    telefone_endereco_ent VARCHAR(50),
    
    -- Flags de controle
    endereco_mesmo_cliente BOOLEAN DEFAULT TRUE,
    cliente_ativo BOOLEAN DEFAULT TRUE,
    
    -- Auditoria
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_por VARCHAR(100)
);

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_cnpj_cpf ON cadastro_cliente(cnpj_cpf);
CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_vendedor ON cadastro_cliente(vendedor);
CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_equipe ON cadastro_cliente(equipe_vendas);
CREATE INDEX IF NOT EXISTS idx_cadastro_cliente_municipio ON cadastro_cliente(municipio, estado);

-- Adicionar comentários na tabela
COMMENT ON TABLE cadastro_cliente IS 'Cadastro de clientes não-Odoo para importação de pedidos';
COMMENT ON COLUMN cadastro_cliente.cnpj_cpf IS 'CNPJ/CPF do cliente (chave única)';
COMMENT ON COLUMN cadastro_cliente.raz_social IS 'Razão social do cliente';
COMMENT ON COLUMN cadastro_cliente.raz_social_red IS 'Nome fantasia do cliente';
COMMENT ON COLUMN cadastro_cliente.endereco_mesmo_cliente IS 'Se o endereço de entrega é o mesmo do cliente';