 -- 1. Criar tabela_rede_precos
 CREATE TABLE IF NOT EXISTS tabela_rede_precos (
     id SERIAL PRIMARY KEY,
     rede VARCHAR(50) NOT NULL,
     regiao VARCHAR(50) NOT NULL,
     cod_produto VARCHAR(50) NOT NULL,
     preco NUMERIC(15, 2) NOT NULL,
     ativo BOOLEAN DEFAULT TRUE NOT NULL,
     vigencia_inicio DATE,
     vigencia_fim DATE,
     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
     atualizado_em TIMESTAMP,
     criado_por VARCHAR(100),
     atualizado_por VARCHAR(100),
     CONSTRAINT uq_tabela_rede_produto UNIQUE (rede, regiao, cod_produto)
 );
 CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_rede ON tabela_rede_precos (rede);
 CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_regiao ON tabela_rede_precos (regiao);
 CREATE INDEX IF NOT EXISTS idx_tabela_rede_precos_produto ON tabela_rede_precos (cod_produto);
 CREATE INDEX IF NOT EXISTS idx_tabela_rede_regiao ON tabela_rede_precos (rede, regiao);
 CREATE INDEX IF NOT EXISTS idx_tabela_rede_produto ON tabela_rede_precos (rede, cod_produto);

 -- 2. Criar regiao_tabela_rede
 CREATE TABLE IF NOT EXISTS regiao_tabela_rede (
     id SERIAL PRIMARY KEY,
     rede VARCHAR(50) NOT NULL,
     uf VARCHAR(2) NOT NULL,
     regiao VARCHAR(50) NOT NULL,
     ativo BOOLEAN DEFAULT TRUE NOT NULL,
     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
     criado_por VARCHAR(100),
     CONSTRAINT uq_regiao_rede_uf UNIQUE (rede, uf)
 );
 CREATE INDEX IF NOT EXISTS idx_regiao_tabela_rede_rede ON regiao_tabela_rede (rede);
 CREATE INDEX IF NOT EXISTS idx_regiao_tabela_rede_uf ON regiao_tabela_rede (uf);
 CREATE INDEX IF NOT EXISTS idx_regiao_rede_uf ON regiao_tabela_rede (rede, uf);

 -- 3. Criar registro_pedido_odoo
 CREATE TABLE IF NOT EXISTS registro_pedido_odoo (
     id SERIAL PRIMARY KEY,
     rede VARCHAR(50) NOT NULL,
     tipo_documento VARCHAR(50) NOT NULL,
     numero_documento VARCHAR(100),
     arquivo_pdf_s3 VARCHAR(500),
     cnpj_cliente VARCHAR(20) NOT NULL,
     nome_cliente VARCHAR(255),
     uf_cliente VARCHAR(2),
     cep_cliente VARCHAR(10),
     endereco_cliente VARCHAR(500),
     odoo_order_id INTEGER,
     odoo_order_name VARCHAR(50),
     status_odoo VARCHAR(50) DEFAULT 'PENDENTE' NOT NULL,
     mensagem_erro TEXT,
     dados_documento JSONB,
     divergente BOOLEAN DEFAULT FALSE NOT NULL,
     divergencias JSONB,
     justificativa_aprovacao TEXT,
     inserido_por VARCHAR(100) NOT NULL,
     aprovado_por VARCHAR(100),
     criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
     processado_em TIMESTAMP
 );
 CREATE INDEX IF NOT EXISTS idx_registro_pedido_odoo_rede ON registro_pedido_odoo (rede);
 CREATE INDEX IF NOT EXISTS idx_registro_pedido_odoo_cnpj ON registro_pedido_odoo (cnpj_cliente);
 CREATE INDEX IF NOT EXISTS idx_registro_rede_cnpj ON registro_pedido_odoo (rede, cnpj_cliente);
 CREATE INDEX IF NOT EXISTS idx_registro_odoo_order ON registro_pedido_odoo (odoo_order_id);
 CREATE INDEX IF NOT EXISTS idx_registro_status ON registro_pedido_odoo (status_odoo);
 CREATE INDEX IF NOT EXISTS idx_registro_criado_em ON registro_pedido_odoo (criado_em);
 ==============================================================================