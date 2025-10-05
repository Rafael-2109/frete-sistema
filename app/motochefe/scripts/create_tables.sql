-- ============================================================
-- SISTEMA MOTOCHEFE - CRIAÇÃO DE TABELAS
-- Versão 1.0.0
-- Data: Outubro 2025
-- ============================================================
-- IMPORTANTE: Execute este SQL no PostgreSQL (Render)
-- ============================================================

-- ============================================================
-- TABELAS DE CADASTRO
-- ============================================================

-- Tabela: equipe_vendas_moto
CREATE TABLE IF NOT EXISTS equipe_vendas_moto (
    id SERIAL PRIMARY KEY,
    equipe_vendas VARCHAR(100) NOT NULL UNIQUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_equipe_vendas_moto_ativo ON equipe_vendas_moto(ativo) WHERE ativo = TRUE;

COMMENT ON TABLE equipe_vendas_moto IS 'Cadastro de equipes de vendas do sistema MotoChefe';

-- Tabela: vendedor_moto
CREATE TABLE IF NOT EXISTS vendedor_moto (
    id SERIAL PRIMARY KEY,
    vendedor VARCHAR(100) NOT NULL,
    equipe_vendas_id INTEGER REFERENCES equipe_vendas_moto(id),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_vendedor_moto_ativo ON vendedor_moto(ativo) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_vendedor_moto_equipe ON vendedor_moto(equipe_vendas_id);

COMMENT ON TABLE vendedor_moto IS 'Cadastro de vendedores de motos';

-- Tabela: transportadora_moto
CREATE TABLE IF NOT EXISTS transportadora_moto (
    id SERIAL PRIMARY KEY,
    transportadora VARCHAR(100) NOT NULL UNIQUE,
    cnpj VARCHAR(20),
    telefone VARCHAR(20),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_transportadora_moto_ativo ON transportadora_moto(ativo) WHERE ativo = TRUE;

COMMENT ON TABLE transportadora_moto IS 'Cadastro de transportadoras';

-- Tabela: cliente_moto
CREATE TABLE IF NOT EXISTS cliente_moto (
    id SERIAL PRIMARY KEY,
    cnpj_cliente VARCHAR(20) NOT NULL UNIQUE,
    cliente VARCHAR(100) NOT NULL,
    endereco_cliente VARCHAR(100),
    numero_cliente VARCHAR(20),
    complemento_cliente VARCHAR(100),
    bairro_cliente VARCHAR(100),
    cidade_cliente VARCHAR(100),
    estado_cliente VARCHAR(2),
    cep_cliente VARCHAR(10),
    telefone_cliente VARCHAR(20),
    email_cliente VARCHAR(100),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_cliente_moto_ativo ON cliente_moto(ativo) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_cliente_moto_cnpj ON cliente_moto(cnpj_cliente);

COMMENT ON TABLE cliente_moto IS 'Cadastro de clientes';

-- ============================================================
-- TABELAS DE PRODUTOS
-- ============================================================

-- Tabela: modelo_moto
CREATE TABLE IF NOT EXISTS modelo_moto (
    id SERIAL PRIMARY KEY,
    nome_modelo VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    potencia_motor VARCHAR(50) NOT NULL,
    autopropelido BOOLEAN NOT NULL DEFAULT FALSE,
    preco_tabela NUMERIC(15, 2) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_modelo_moto_ativo ON modelo_moto(ativo) WHERE ativo = TRUE;

COMMENT ON TABLE modelo_moto IS 'Catálogo de modelos de motos - PREÇO TABELA aqui';
COMMENT ON COLUMN modelo_moto.preco_tabela IS 'Preço oficial da tabela por modelo+potência';

-- Tabela: moto (CENTRAL - 1 chassi = 1 registro)
CREATE TABLE IF NOT EXISTS moto (
    numero_chassi VARCHAR(17) PRIMARY KEY,
    numero_motor VARCHAR(50) NOT NULL UNIQUE,
    modelo_id INTEGER NOT NULL REFERENCES modelo_moto(id),
    cor VARCHAR(50) NOT NULL,
    ano_fabricacao INTEGER,
    nf_entrada VARCHAR(20) NOT NULL,
    data_nf_entrada DATE NOT NULL,
    data_entrada DATE NOT NULL DEFAULT CURRENT_DATE,
    fornecedor VARCHAR(100) NOT NULL,
    custo_aquisicao NUMERIC(15, 2) NOT NULL,
    reservado BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'DISPONIVEL',
    pallet VARCHAR(20),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_moto_status ON moto(status);
CREATE INDEX IF NOT EXISTS idx_moto_reservado ON moto(reservado);
CREATE INDEX IF NOT EXISTS idx_moto_data_entrada ON moto(data_entrada);
CREATE INDEX IF NOT EXISTS idx_moto_modelo_id ON moto(modelo_id);

COMMENT ON TABLE moto IS 'Tabela CENTRAL - Cada chassi é único, controle FIFO por data_entrada';
COMMENT ON COLUMN moto.status IS 'Status: DISPONIVEL, RESERVADA, VENDIDA';

-- ============================================================
-- TABELAS DE VENDAS
-- ============================================================

-- Tabela: pedido_venda_moto
CREATE TABLE IF NOT EXISTS pedido_venda_moto (
    id SERIAL PRIMARY KEY,
    numero_pedido VARCHAR(50) NOT NULL UNIQUE,
    cliente_id INTEGER NOT NULL REFERENCES cliente_moto(id),
    vendedor_id INTEGER NOT NULL REFERENCES vendedor_moto(id),
    equipe_vendas_id INTEGER REFERENCES equipe_vendas_moto(id),
    data_pedido DATE NOT NULL DEFAULT CURRENT_DATE,
    data_expedicao DATE,
    faturado BOOLEAN NOT NULL DEFAULT FALSE,
    enviado BOOLEAN NOT NULL DEFAULT FALSE,
    numero_nf VARCHAR(20) UNIQUE,
    data_nf DATE,
    tipo_nf VARCHAR(50),
    valor_total_pedido NUMERIC(15, 2) NOT NULL,
    valor_frete_cliente NUMERIC(15, 2) DEFAULT 0,
    forma_pagamento VARCHAR(50),
    condicao_pagamento VARCHAR(100),
    transportadora_id INTEGER REFERENCES transportadora_moto(id),
    tipo_frete VARCHAR(20),
    responsavel_movimentacao VARCHAR(20),
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_pedido_venda_moto_faturado ON pedido_venda_moto(faturado);
CREATE INDEX IF NOT EXISTS idx_pedido_venda_moto_enviado ON pedido_venda_moto(enviado);
CREATE INDEX IF NOT EXISTS idx_pedido_venda_moto_nf ON pedido_venda_moto(numero_nf);

COMMENT ON TABLE pedido_venda_moto IS 'Pedido que vira Venda quando faturado=TRUE';
COMMENT ON COLUMN pedido_venda_moto.responsavel_movimentacao IS 'RJ ou NACOM';

-- Tabela: pedido_venda_moto_item
CREATE TABLE IF NOT EXISTS pedido_venda_moto_item (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedido_venda_moto(id),
    numero_chassi VARCHAR(17) NOT NULL REFERENCES moto(numero_chassi),
    preco_venda NUMERIC(15, 2) NOT NULL,
    montagem_contratada BOOLEAN NOT NULL DEFAULT FALSE,
    valor_montagem NUMERIC(15, 2) DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_pedido_item_pedido ON pedido_venda_moto_item(pedido_id);
CREATE INDEX IF NOT EXISTS idx_pedido_item_chassi ON pedido_venda_moto_item(numero_chassi);

COMMENT ON TABLE pedido_venda_moto_item IS 'Itens do pedido - Chassi alocado via FIFO';

-- ============================================================
-- TABELAS FINANCEIRAS
-- ============================================================

-- Tabela: titulo_financeiro
CREATE TABLE IF NOT EXISTS titulo_financeiro (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedido_venda_moto(id),
    numero_parcela INTEGER NOT NULL,
    total_parcelas INTEGER NOT NULL,
    valor_parcela NUMERIC(15, 2) NOT NULL,
    data_vencimento DATE NOT NULL,
    data_recebimento DATE,
    valor_recebido NUMERIC(15, 2) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTO',
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_titulo_pedido ON titulo_financeiro(pedido_id);
CREATE INDEX IF NOT EXISTS idx_titulo_status ON titulo_financeiro(status);

COMMENT ON TABLE titulo_financeiro IS 'Parcelas a receber (vendas parceladas)';
COMMENT ON COLUMN titulo_financeiro.status IS 'Status: ABERTO, PAGO, ATRASADO, CANCELADO';

-- Tabela: comissao_vendedor
CREATE TABLE IF NOT EXISTS comissao_vendedor (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedido_venda_moto(id),
    vendedor_id INTEGER NOT NULL REFERENCES vendedor_moto(id),
    valor_comissao_fixa NUMERIC(15, 2) NOT NULL,
    valor_excedente NUMERIC(15, 2) DEFAULT 0,
    valor_total_comissao NUMERIC(15, 2) NOT NULL,
    qtd_vendedores_equipe INTEGER DEFAULT 1,
    valor_rateado NUMERIC(15, 2) NOT NULL,
    data_vencimento DATE,
    data_pagamento DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comissao_pedido ON comissao_vendedor(pedido_id);
CREATE INDEX IF NOT EXISTS idx_comissao_vendedor ON comissao_vendedor(vendedor_id);
CREATE INDEX IF NOT EXISTS idx_comissao_status ON comissao_vendedor(status);

COMMENT ON TABLE comissao_vendedor IS 'Comissão = Fixa + Excedente, rateada pela equipe';
COMMENT ON COLUMN comissao_vendedor.status IS 'Status: PENDENTE, PAGO, CANCELADO';

-- ============================================================
-- TABELAS DE LOGÍSTICA
-- ============================================================

-- Tabela: embarque_moto
CREATE TABLE IF NOT EXISTS embarque_moto (
    id SERIAL PRIMARY KEY,
    numero_embarque VARCHAR(50) NOT NULL UNIQUE,
    transportadora_id INTEGER NOT NULL REFERENCES transportadora_moto(id),
    data_embarque DATE NOT NULL DEFAULT CURRENT_DATE,
    data_entrega_prevista DATE,
    data_entrega_real DATE,
    valor_frete_pago NUMERIC(15, 2) NOT NULL,
    tipo_veiculo VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'PLANEJADO',
    observacoes TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_embarque_status ON embarque_moto(status);

COMMENT ON TABLE embarque_moto IS '1 Embarque = N Pedidos';
COMMENT ON COLUMN embarque_moto.status IS 'Status: PLANEJADO, EM_TRANSITO, ENTREGUE, CANCELADO';

-- Tabela: embarque_pedido (N:N entre embarque e pedido)
CREATE TABLE IF NOT EXISTS embarque_pedido (
    id SERIAL PRIMARY KEY,
    embarque_id INTEGER NOT NULL REFERENCES embarque_moto(id),
    pedido_id INTEGER NOT NULL REFERENCES pedido_venda_moto(id),
    qtd_motos_pedido INTEGER NOT NULL,
    valor_frete_rateado NUMERIC(15, 2) NOT NULL DEFAULT 0,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_embarque_pedido UNIQUE (embarque_id, pedido_id)
);

CREATE INDEX IF NOT EXISTS idx_embarque_pedido_embarque ON embarque_pedido(embarque_id);
CREATE INDEX IF NOT EXISTS idx_embarque_pedido_pedido ON embarque_pedido(pedido_id);

COMMENT ON TABLE embarque_pedido IS 'Relação N:N - Rateio de frete por quantidade de motos';

-- ============================================================
-- TABELAS OPERACIONAIS
-- ============================================================

-- Tabela: custos_operacionais
CREATE TABLE IF NOT EXISTS custos_operacionais (
    id SERIAL PRIMARY KEY,
    custo_montagem NUMERIC(15, 2) NOT NULL,
    custo_movimentacao_rj NUMERIC(15, 2) NOT NULL,
    custo_movimentacao_nacom NUMERIC(15, 2) NOT NULL,
    valor_comissao_fixa NUMERIC(15, 2) NOT NULL,
    data_vigencia_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
    data_vigencia_fim DATE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_custos_ativo ON custos_operacionais(ativo) WHERE ativo = TRUE;

COMMENT ON TABLE custos_operacionais IS 'Custos fixos operacionais - 1 registro ativo por vez';

-- Tabela: despesa_mensal
CREATE TABLE IF NOT EXISTS despesa_mensal (
    id SERIAL PRIMARY KEY,
    tipo_despesa VARCHAR(50) NOT NULL,
    descricao VARCHAR(255),
    valor NUMERIC(15, 2) NOT NULL,
    mes_competencia INTEGER NOT NULL,
    ano_competencia INTEGER NOT NULL,
    data_vencimento DATE,
    data_pagamento DATE,
    valor_pago NUMERIC(15, 2) DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    atualizado_por VARCHAR(100),
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_despesa_competencia ON despesa_mensal(ano_competencia, mes_competencia);
CREATE INDEX IF NOT EXISTS idx_despesa_status ON despesa_mensal(status);

COMMENT ON TABLE despesa_mensal IS 'Despesas mensais (salário, aluguel, etc) para cálculo de margem';
COMMENT ON COLUMN despesa_mensal.status IS 'Status: PENDENTE, PAGO, ATRASADO, CANCELADO';

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================
-- IMPORTANTE: Configure os custos operacionais acessando /motochefe/custos
-- ============================================================

-- Verificar tabelas criadas
SELECT
    schemaname as schema,
    tablename as table_name,
    tableowner as owner
FROM pg_tables
WHERE tablename LIKE '%_moto'
   OR tablename IN ('custos_operacionais', 'despesa_mensal')
ORDER BY tablename;
