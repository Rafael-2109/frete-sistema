-- Script de criação das tabelas do módulo BI
-- Execute este script para criar as tabelas do Data Warehouse

-- Tabela principal de fretes agregados
CREATE TABLE IF NOT EXISTS bi_frete_agregado (
    id SERIAL PRIMARY KEY,
    data_referencia DATE NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    semana_ano INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    
    -- Dimensões de transportadora
    transportadora_id INTEGER REFERENCES transportadoras(id),
    transportadora_nome VARCHAR(120),
    transportadora_cnpj VARCHAR(20),
    transportadora_uf VARCHAR(2),
    transportadora_optante BOOLEAN DEFAULT FALSE,
    
    -- Dimensões de cliente
    cliente_cnpj VARCHAR(20),
    cliente_nome VARCHAR(255),
    cliente_cidade VARCHAR(100),
    cliente_uf VARCHAR(2),
    cliente_regiao VARCHAR(20),
    
    -- Dimensões de rota
    origem_uf VARCHAR(2) DEFAULT 'SP',
    destino_uf VARCHAR(2),
    destino_cidade VARCHAR(100),
    destino_regiao VARCHAR(20),
    distancia_km NUMERIC(10,2),
    
    -- Dimensões de carga
    tipo_carga VARCHAR(20),
    modalidade VARCHAR(50),
    tipo_veiculo VARCHAR(50),
    
    -- Métricas de volume
    qtd_embarques INTEGER DEFAULT 0,
    qtd_nfs INTEGER DEFAULT 0,
    qtd_ctes INTEGER DEFAULT 0,
    peso_total_kg NUMERIC(15,3) DEFAULT 0,
    valor_total_nf NUMERIC(15,2) DEFAULT 0,
    qtd_pallets NUMERIC(15,3) DEFAULT 0,
    
    -- Métricas de valores
    valor_cotado_total NUMERIC(15,2) DEFAULT 0,
    valor_cte_total NUMERIC(15,2) DEFAULT 0,
    valor_considerado_total NUMERIC(15,2) DEFAULT 0,
    valor_pago_total NUMERIC(15,2) DEFAULT 0,
    
    -- Métricas de despesas extras
    qtd_despesas_extras INTEGER DEFAULT 0,
    valor_despesas_extras NUMERIC(15,2) DEFAULT 0,
    valor_reentrega NUMERIC(15,2) DEFAULT 0,
    valor_tde NUMERIC(15,2) DEFAULT 0,
    valor_devolucao NUMERIC(15,2) DEFAULT 0,
    valor_complemento NUMERIC(15,2) DEFAULT 0,
    valor_outras_despesas NUMERIC(15,2) DEFAULT 0,
    
    -- Métricas de divergência
    divergencia_cotado_cte NUMERIC(15,2) DEFAULT 0,
    divergencia_considerado_pago NUMERIC(15,2) DEFAULT 0,
    qtd_aprovacoes INTEGER DEFAULT 0,
    qtd_rejeicoes INTEGER DEFAULT 0,
    qtd_em_tratativa INTEGER DEFAULT 0,
    
    -- Métricas de prazo
    lead_time_medio NUMERIC(10,2),
    prazo_pagamento_medio NUMERIC(10,2),
    
    -- KPIs calculados
    custo_por_kg NUMERIC(10,4),
    custo_por_real_faturado NUMERIC(10,4),
    custo_por_km NUMERIC(10,4),
    percentual_despesa_extra NUMERIC(10,2),
    percentual_divergencia NUMERIC(10,2),
    
    -- Controle ETL
    processado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versao_etl VARCHAR(10),
    
    CONSTRAINT idx_bi_periodo_transp_idx UNIQUE (data_referencia, transportadora_id, cliente_cnpj, destino_uf, destino_cidade)
);

-- Índices para performance
CREATE INDEX idx_bi_periodo_transp ON bi_frete_agregado(data_referencia, transportadora_id);
CREATE INDEX idx_bi_periodo_regiao ON bi_frete_agregado(data_referencia, destino_regiao);
CREATE INDEX idx_bi_ano_mes ON bi_frete_agregado(ano, mes);
CREATE INDEX idx_bi_cliente_periodo ON bi_frete_agregado(cliente_cnpj, data_referencia);

-- Tabela de despesas detalhadas
CREATE TABLE IF NOT EXISTS bi_despesa_detalhada (
    id SERIAL PRIMARY KEY,
    data_referencia DATE NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    
    -- Classificação
    tipo_despesa VARCHAR(50) NOT NULL,
    setor_responsavel VARCHAR(20) NOT NULL,
    motivo_despesa VARCHAR(100) NOT NULL,
    
    -- Relacionamentos
    transportadora_id INTEGER REFERENCES transportadoras(id),
    transportadora_nome VARCHAR(120),
    cliente_cnpj VARCHAR(20),
    cliente_nome VARCHAR(255),
    destino_uf VARCHAR(2),
    destino_cidade VARCHAR(100),
    
    -- Métricas
    qtd_ocorrencias INTEGER DEFAULT 0,
    valor_total NUMERIC(15,2) DEFAULT 0,
    valor_medio NUMERIC(15,2) DEFAULT 0,
    valor_minimo NUMERIC(15,2),
    valor_maximo NUMERIC(15,2),
    
    -- Análise
    percentual_sobre_frete NUMERIC(10,2),
    recorrencia_mensal INTEGER,
    tendencia VARCHAR(20),
    
    processado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bi_despesa_periodo ON bi_despesa_detalhada(data_referencia, tipo_despesa);
CREATE INDEX idx_bi_despesa_setor ON bi_despesa_detalhada(setor_responsavel, data_referencia);

-- Tabela de performance por transportadora
CREATE TABLE IF NOT EXISTS bi_performance_transportadora (
    id SERIAL PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    tipo_periodo VARCHAR(20),
    
    -- Transportadora
    transportadora_id INTEGER REFERENCES transportadoras(id),
    transportadora_nome VARCHAR(120),
    transportadora_cnpj VARCHAR(20),
    
    -- Volume
    total_embarques INTEGER DEFAULT 0,
    total_nfs INTEGER DEFAULT 0,
    total_peso_kg NUMERIC(15,3) DEFAULT 0,
    total_valor_faturado NUMERIC(15,2) DEFAULT 0,
    
    -- Financeiro
    valor_total_frete NUMERIC(15,2) DEFAULT 0,
    valor_total_despesas NUMERIC(15,2) DEFAULT 0,
    custo_medio_por_kg NUMERIC(10,4),
    custo_medio_por_nf NUMERIC(10,2),
    margem_divergencia_media NUMERIC(10,2),
    
    -- Conta corrente
    saldo_conta_corrente NUMERIC(15,2) DEFAULT 0,
    qtd_creditos INTEGER DEFAULT 0,
    qtd_debitos INTEGER DEFAULT 0,
    
    -- Qualidade
    percentual_entregas_prazo NUMERIC(10,2),
    percentual_com_despesa_extra NUMERIC(10,2),
    qtd_reclamacoes INTEGER DEFAULT 0,
    score_qualidade NUMERIC(10,2),
    
    -- Rankings
    ranking_custo INTEGER,
    ranking_volume INTEGER,
    ranking_qualidade INTEGER,
    ranking_geral INTEGER,
    
    -- Comparativo
    variacao_periodo_anterior NUMERIC(10,2),
    tendencia VARCHAR(20),
    
    recomendacao TEXT,
    calculado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_bi_perf_transportadora_periodo UNIQUE (transportadora_id, periodo_inicio, periodo_fim, tipo_periodo)
);

CREATE INDEX idx_bi_perf_transp_periodo ON bi_performance_transportadora(transportadora_id, periodo_inicio, periodo_fim);

-- Tabela de análise regional
CREATE TABLE IF NOT EXISTS bi_analise_regional (
    id SERIAL PRIMARY KEY,
    data_referencia DATE NOT NULL,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    
    -- Região
    regiao VARCHAR(20) NOT NULL,
    uf VARCHAR(2) NOT NULL,
    cidade VARCHAR(100),
    codigo_ibge VARCHAR(10),
    
    -- Volume
    qtd_entregas INTEGER DEFAULT 0,
    peso_total_kg NUMERIC(15,3) DEFAULT 0,
    valor_total_faturado NUMERIC(15,2) DEFAULT 0,
    
    -- Custos
    custo_total_frete NUMERIC(15,2) DEFAULT 0,
    custo_medio_por_kg NUMERIC(10,4),
    custo_medio_por_entrega NUMERIC(10,2),
    
    -- Transportadoras
    qtd_transportadoras_ativas INTEGER DEFAULT 0,
    transportadora_principal_id INTEGER,
    transportadora_principal_nome VARCHAR(120),
    percentual_transportadora_principal NUMERIC(10,2),
    
    -- Performance
    lead_time_medio NUMERIC(10,2),
    percentual_no_prazo NUMERIC(10,2),
    percentual_com_problema NUMERIC(10,2),
    
    -- Comparativos
    variacao_mes_anterior NUMERIC(10,2),
    posicao_ranking_custo INTEGER,
    posicao_ranking_volume INTEGER,
    
    processado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_bi_regional_local_periodo UNIQUE (data_referencia, uf, cidade)
);

CREATE INDEX idx_bi_regional_periodo ON bi_analise_regional(data_referencia, regiao);
CREATE INDEX idx_bi_regional_uf ON bi_analise_regional(uf, data_referencia);

-- Tabela de indicadores mensais
CREATE TABLE IF NOT EXISTS bi_indicador_mensal (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    
    -- KPIs principais
    custo_total_frete NUMERIC(15,2) DEFAULT 0,
    custo_total_despesas NUMERIC(15,2) DEFAULT 0,
    economia_realizada NUMERIC(15,2) DEFAULT 0,
    
    -- Volumes
    total_embarques INTEGER DEFAULT 0,
    total_peso_kg NUMERIC(15,3) DEFAULT 0,
    total_valor_faturado NUMERIC(15,2) DEFAULT 0,
    
    -- Médias
    custo_medio_por_kg NUMERIC(10,4),
    custo_medio_por_embarque NUMERIC(10,2),
    ticket_medio_embarque NUMERIC(10,2),
    
    -- Performance
    percentual_no_prazo NUMERIC(10,2),
    percentual_com_divergencia NUMERIC(10,2),
    percentual_aprovado NUMERIC(10,2),
    
    -- Top performers
    top_transportadora_volume VARCHAR(120),
    top_transportadora_custo VARCHAR(120),
    top_regiao_volume VARCHAR(20),
    top_regiao_custo VARCHAR(20),
    
    -- Variações
    variacao_mes_anterior NUMERIC(10,2),
    variacao_ano_anterior NUMERIC(10,2),
    
    -- Meta
    meta_custo NUMERIC(15,2),
    percentual_atingimento_meta NUMERIC(10,2),
    
    calculado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_bi_indicador_periodo UNIQUE (ano, mes)
);

-- Função para calcular região baseada na UF
CREATE OR REPLACE FUNCTION get_regiao_by_uf(uf VARCHAR(2))
RETURNS VARCHAR(20) AS $$
BEGIN
    CASE uf
        WHEN 'AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO' THEN
            RETURN 'Norte';
        WHEN 'AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE' THEN
            RETURN 'Nordeste';
        WHEN 'DF', 'GO', 'MT', 'MS' THEN
            RETURN 'Centro-Oeste';
        WHEN 'ES', 'MG', 'RJ', 'SP' THEN
            RETURN 'Sudeste';
        WHEN 'PR', 'RS', 'SC' THEN
            RETURN 'Sul';
        ELSE
            RETURN 'Indefinido';
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO frete_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO frete_user;