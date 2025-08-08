-- Migração: Criar tabela de alertas para separações COTADAS alteradas
-- Data: 2025-01-08
-- Descrição: Sistema de controle de alterações em separações com status COTADO

-- Criar tabela de alertas
CREATE TABLE IF NOT EXISTS alertas_separacao_cotada (
    id SERIAL PRIMARY KEY,
    separacao_lote_id VARCHAR(50) NOT NULL,
    num_pedido VARCHAR(50) NOT NULL,
    cod_produto VARCHAR(50) NOT NULL,
    
    -- Tipo de alteração
    tipo_alteracao VARCHAR(20) NOT NULL CHECK (tipo_alteracao IN ('REDUCAO', 'AUMENTO', 'REMOCAO', 'ADICAO')),
    qtd_anterior NUMERIC(15,3) DEFAULT 0,
    qtd_nova NUMERIC(15,3) DEFAULT 0,
    qtd_diferenca NUMERIC(15,3) DEFAULT 0,
    
    -- Controle de reimpressão
    reimpresso BOOLEAN DEFAULT FALSE NOT NULL,
    data_alerta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_reimpressao TIMESTAMP,
    reimpresso_por VARCHAR(100),
    
    -- Dados adicionais
    nome_produto VARCHAR(255),
    cliente VARCHAR(255),
    embarque_numero INTEGER,
    tipo_separacao VARCHAR(10) CHECK (tipo_separacao IN ('TOTAL', 'PARCIAL')),
    
    -- Observações
    observacao TEXT,
    
    -- Índices
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_alertas_separacao_lote ON alertas_separacao_cotada(separacao_lote_id);
CREATE INDEX IF NOT EXISTS idx_alertas_num_pedido ON alertas_separacao_cotada(num_pedido);
CREATE INDEX IF NOT EXISTS idx_alertas_reimpresso ON alertas_separacao_cotada(reimpresso);
CREATE INDEX IF NOT EXISTS idx_alertas_data_alerta ON alertas_separacao_cotada(data_alerta DESC);

-- Adicionar trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_alertas_separacao_updated_at 
    BEFORE UPDATE ON alertas_separacao_cotada 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Comentários nas colunas
COMMENT ON TABLE alertas_separacao_cotada IS 'Registro de alterações em separações COTADAS que requerem reimpressão';
COMMENT ON COLUMN alertas_separacao_cotada.tipo_alteracao IS 'Tipo de alteração: REDUCAO, AUMENTO, REMOCAO, ADICAO';
COMMENT ON COLUMN alertas_separacao_cotada.reimpresso IS 'Flag indicando se já foi reimpresso';
COMMENT ON COLUMN alertas_separacao_cotada.tipo_separacao IS 'TOTAL = espelho do pedido, PARCIAL = parte do pedido';