-- Migration: Criar tabelas cotacao + pedidos CarVia
-- Data: 2026-03-20
-- Uso: Executar no Render Shell (SQL idempotente)

-- 1. Cotacoes
CREATE TABLE IF NOT EXISTS carvia_cotacoes (
    id SERIAL PRIMARY KEY,
    numero_cotacao VARCHAR(20) NOT NULL,
    cliente_id INTEGER NOT NULL REFERENCES carvia_clientes(id),
    endereco_origem_id INTEGER NOT NULL REFERENCES carvia_cliente_enderecos(id),
    endereco_destino_id INTEGER NOT NULL REFERENCES carvia_cliente_enderecos(id),
    tipo_material VARCHAR(20) NOT NULL,
    peso NUMERIC(15,3),
    valor_mercadoria NUMERIC(15,2),
    dimensao_c NUMERIC(10,4),
    dimensao_l NUMERIC(10,4),
    dimensao_a NUMERIC(10,4),
    peso_cubado NUMERIC(15,3),
    volumes INTEGER,
    valor_tabela NUMERIC(15,2),
    percentual_desconto NUMERIC(5,2) DEFAULT 0,
    valor_descontado NUMERIC(15,2),
    valor_final_aprovado NUMERIC(15,2),
    tabela_carvia_id INTEGER REFERENCES carvia_tabelas_frete(id),
    dentro_tabela BOOLEAN,
    detalhes_calculo JSONB,
    data_cotacao TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_expedicao DATE,
    data_agenda DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
    aprovado_por VARCHAR(100),
    aprovado_em TIMESTAMP WITHOUT TIME ZONE,
    observacoes TEXT,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_carvia_cotacao_status CHECK (
        status IN ('RASCUNHO','PENDENTE_ADMIN','ENVIADO','APROVADO','RECUSADO','CANCELADO')
    ),
    CONSTRAINT ck_carvia_cotacao_tipo_material CHECK (
        tipo_material IN ('CARGA_GERAL', 'MOTO')
    )
);

CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_numero ON carvia_cotacoes(numero_cotacao);
CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_cliente ON carvia_cotacoes(cliente_id);
CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_status ON carvia_cotacoes(status);

-- 2. Motos da cotacao
CREATE TABLE IF NOT EXISTS carvia_cotacao_motos (
    id SERIAL PRIMARY KEY,
    cotacao_id INTEGER NOT NULL REFERENCES carvia_cotacoes(id) ON DELETE CASCADE,
    modelo_moto_id INTEGER NOT NULL REFERENCES carvia_modelos_moto(id),
    categoria_moto_id INTEGER NOT NULL REFERENCES carvia_categorias_moto(id),
    quantidade INTEGER NOT NULL,
    peso_cubado_unitario NUMERIC(10,3),
    peso_cubado_total NUMERIC(15,3)
);

CREATE INDEX IF NOT EXISTS ix_carvia_cotmoto_cotacao ON carvia_cotacao_motos(cotacao_id);

-- 3. Pedidos
CREATE TABLE IF NOT EXISTS carvia_pedidos (
    id SERIAL PRIMARY KEY,
    numero_pedido VARCHAR(20) NOT NULL,
    cotacao_id INTEGER NOT NULL REFERENCES carvia_cotacoes(id),
    filial VARCHAR(5) NOT NULL,
    tipo_separacao VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    observacoes TEXT,
    criado_por VARCHAR(100) NOT NULL,
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_carvia_pedido_status CHECK (
        status IN ('PENDENTE','SEPARADO','FATURADO','EMBARCADO','CANCELADO')
    ),
    CONSTRAINT ck_carvia_pedido_filial CHECK (filial IN ('SP', 'RJ')),
    CONSTRAINT ck_carvia_pedido_tipo_sep CHECK (
        tipo_separacao IN ('ESTOQUE', 'CROSSDOCK')
    )
);

CREATE INDEX IF NOT EXISTS ix_carvia_pedido_numero ON carvia_pedidos(numero_pedido);
CREATE INDEX IF NOT EXISTS ix_carvia_pedido_cotacao ON carvia_pedidos(cotacao_id);
CREATE INDEX IF NOT EXISTS ix_carvia_pedido_status ON carvia_pedidos(status);

-- 4. Itens de pedido
CREATE TABLE IF NOT EXISTS carvia_pedido_itens (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES carvia_pedidos(id) ON DELETE CASCADE,
    modelo_moto_id INTEGER REFERENCES carvia_modelos_moto(id),
    descricao VARCHAR(255),
    cor VARCHAR(50),
    quantidade INTEGER NOT NULL,
    valor_unitario NUMERIC(15,2),
    valor_total NUMERIC(15,2),
    numero_nf VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS ix_carvia_peditem_pedido ON carvia_pedido_itens(pedido_id);
