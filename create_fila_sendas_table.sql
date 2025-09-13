-- Script SQL para criar tabela de fila de agendamento Sendas
-- Executar diretamente no PostgreSQL

CREATE TABLE IF NOT EXISTS fila_agendamento_sendas (
    id SERIAL PRIMARY KEY,
    
    -- Rastreabilidade da origem
    tipo_origem VARCHAR(20) NOT NULL,  -- 'separacao' ou 'nf'
    documento_origem VARCHAR(50) NOT NULL,  -- separacao_lote_id ou numero_nf
    
    -- Dados essenciais para a planilha Sendas
    cnpj VARCHAR(20) NOT NULL,
    num_pedido VARCHAR(50) NOT NULL,
    pedido_cliente VARCHAR(100),  -- Campo essencial para Sendas
    
    -- Produto e quantidade
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    quantidade NUMERIC(15, 3) NOT NULL,
    
    -- Datas
    data_expedicao DATE NOT NULL,
    data_agendamento DATE NOT NULL,
    
    -- Protocolo provisório (mesmo padrão da programacao_lote)
    protocolo VARCHAR(100),
    
    -- Status simples
    status VARCHAR(20) DEFAULT 'pendente',
    -- valores: pendente, processado, erro
    
    -- Controle mínimo
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_fila_sendas_status ON fila_agendamento_sendas(status);
CREATE INDEX IF NOT EXISTS idx_fila_sendas_cnpj ON fila_agendamento_sendas(cnpj);
CREATE INDEX IF NOT EXISTS idx_fila_sendas_data_agendamento ON fila_agendamento_sendas(data_agendamento);
CREATE INDEX IF NOT EXISTS idx_fila_sendas_processo ON fila_agendamento_sendas(status, cnpj, data_agendamento);

-- Comentários na tabela
COMMENT ON TABLE fila_agendamento_sendas IS 'Fila simples para acumular agendamentos Sendas e processar em lote';
COMMENT ON COLUMN fila_agendamento_sendas.tipo_origem IS 'Origem do agendamento: separacao ou nf';
COMMENT ON COLUMN fila_agendamento_sendas.documento_origem IS 'ID do documento de origem: separacao_lote_id ou numero_nf';
COMMENT ON COLUMN fila_agendamento_sendas.pedido_cliente IS 'Pedido de compra do cliente - campo essencial para Sendas';
COMMENT ON COLUMN fila_agendamento_sendas.protocolo IS 'Protocolo provisório no formato AGEND_XXXX_YYYYMMDD';
COMMENT ON COLUMN fila_agendamento_sendas.status IS 'Status do item na fila: pendente, processado ou erro';