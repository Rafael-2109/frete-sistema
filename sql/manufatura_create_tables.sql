-- =====================================================
-- Script de criação das tabelas do módulo Manufatura
-- Data: 2025-01-10
-- =====================================================

-- 1. TABELAS NOVAS DO MÓDULO MANUFATURA

-- 1.1 Grupo Empresarial
CREATE TABLE IF NOT EXISTS grupo_empresarial (
    id SERIAL PRIMARY KEY,
    nome_grupo VARCHAR(100) NOT NULL UNIQUE,
    tipo_grupo VARCHAR(20) NOT NULL CHECK (tipo_grupo IN ('prefixo_cnpj', 'raz_social')),
    info_grupo TEXT[] NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_grupo_nome ON grupo_empresarial(nome_grupo);
CREATE INDEX IF NOT EXISTS idx_grupo_tipo ON grupo_empresarial(tipo_grupo);

-- 1.2 Histórico de Pedidos
CREATE TABLE IF NOT EXISTS historico_pedidos (
    id SERIAL PRIMARY KEY,
    num_pedido VARCHAR(50) NOT NULL,
    data_pedido DATE NOT NULL,
    cnpj_cliente VARCHAR(20) NOT NULL,
    raz_social_red VARCHAR(255),
    nome_grupo VARCHAR(100),
    vendedor VARCHAR(100),
    equipe_vendas VARCHAR(100),
    incoterm VARCHAR(20),
    nome_cidade VARCHAR(100),
    cod_uf VARCHAR(2),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_produto_pedido NUMERIC(15,3) NOT NULL,
    preco_produto_pedido NUMERIC(15,4),
    valor_produto_pedido NUMERIC(15,2),
    icms_produto_pedido NUMERIC(15,2),
    pis_produto_pedido NUMERIC(15,2),
    cofins_produto_pedido NUMERIC(15,2),
    importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(num_pedido, cod_produto)
);
CREATE INDEX IF NOT EXISTS idx_hist_pedido ON historico_pedidos(num_pedido);
CREATE INDEX IF NOT EXISTS idx_hist_produto ON historico_pedidos(cod_produto);
CREATE INDEX IF NOT EXISTS idx_hist_grupo ON historico_pedidos(nome_grupo);
CREATE INDEX IF NOT EXISTS idx_hist_data ON historico_pedidos(data_pedido);

-- 1.3 Previsão de Demanda
CREATE TABLE IF NOT EXISTS previsao_demanda (
    id SERIAL PRIMARY KEY,
    data_mes INTEGER NOT NULL CHECK (data_mes BETWEEN 1 AND 12),
    data_ano INTEGER NOT NULL CHECK (data_ano >= 2024),
    nome_grupo VARCHAR(100),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_demanda_prevista NUMERIC(15,3) NOT NULL,
    qtd_demanda_realizada NUMERIC(15,3) DEFAULT 0,
    disparo_producao VARCHAR(3) CHECK (disparo_producao IN ('MTO', 'MTS')),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    UNIQUE(data_mes, data_ano, cod_produto, nome_grupo)
);
CREATE INDEX IF NOT EXISTS idx_prev_periodo ON previsao_demanda(data_ano, data_mes);
CREATE INDEX IF NOT EXISTS idx_prev_produto ON previsao_demanda(cod_produto);

-- 1.4 Plano Mestre de Produção
CREATE TABLE IF NOT EXISTS plano_mestre_producao (
    id SERIAL PRIMARY KEY,
    data_mes INTEGER NOT NULL CHECK (data_mes BETWEEN 1 AND 12),
    data_ano INTEGER NOT NULL CHECK (data_ano >= 2024),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_demanda_prevista NUMERIC(15,3),
    disparo_producao VARCHAR(3) CHECK (disparo_producao IN ('MTO', 'MTS')),
    qtd_producao_programada NUMERIC(15,3) DEFAULT 0,
    qtd_producao_realizada NUMERIC(15,3) DEFAULT 0,
    qtd_estoque NUMERIC(15,3) DEFAULT 0,
    qtd_estoque_seguranca NUMERIC(15,3) DEFAULT 0,
    qtd_reposicao_sugerida NUMERIC(15,3) GENERATED ALWAYS AS 
        (qtd_demanda_prevista + qtd_estoque_seguranca - qtd_producao_programada - qtd_producao_realizada) STORED,
    qtd_lote_ideal NUMERIC(15,3),
    qtd_lote_minimo NUMERIC(15,3),
    status_geracao VARCHAR(20) DEFAULT 'rascunho' CHECK (status_geracao IN ('rascunho', 'aprovado', 'executando', 'concluido')),
    criado_por VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(data_mes, data_ano, cod_produto)
);
CREATE INDEX IF NOT EXISTS idx_pmp_periodo ON plano_mestre_producao(data_ano, data_mes);
CREATE INDEX IF NOT EXISTS idx_pmp_status ON plano_mestre_producao(status_geracao);

-- 1.5 Recursos de Produção
CREATE TABLE IF NOT EXISTS recursos_producao (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    linha_producao VARCHAR(50) NOT NULL,
    qtd_unidade_por_caixa NUMERIC(10,2),
    capacidade_unidade_minuto NUMERIC(10,3) NOT NULL,
    qtd_lote_ideal NUMERIC(15,3),
    qtd_lote_minimo NUMERIC(15,3),
    eficiencia_media NUMERIC(5,2) DEFAULT 85.00,
    tempo_setup INTEGER DEFAULT 30,
    disponivel BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cod_produto, linha_producao)
);
CREATE INDEX IF NOT EXISTS idx_rec_produto ON recursos_producao(cod_produto);
CREATE INDEX IF NOT EXISTS idx_rec_linha ON recursos_producao(linha_producao);

-- 1.6 Ordem de Produção
CREATE TABLE IF NOT EXISTS ordem_producao (
    id SERIAL PRIMARY KEY,
    numero_ordem VARCHAR(20) UNIQUE NOT NULL,
    origem_ordem VARCHAR(10) CHECK (origem_ordem IN ('PMP', 'MTO', 'Manual')),
    status VARCHAR(20) DEFAULT 'Planejada' CHECK (status IN ('Planejada', 'Liberada', 'Em Produção', 'Concluída', 'Cancelada')),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    materiais_necessarios JSONB,
    qtd_planejada NUMERIC(15,3) NOT NULL,
    qtd_produzida NUMERIC(15,3) DEFAULT 0,
    data_inicio_prevista DATE NOT NULL,
    data_fim_prevista DATE NOT NULL,
    data_inicio_real DATE,
    data_fim_real DATE,
    linha_producao VARCHAR(50),
    turno VARCHAR(20),
    lote_producao VARCHAR(50),
    custo_previsto NUMERIC(15,2),
    custo_real NUMERIC(15,2),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    atualizado_em TIMESTAMP,
    CHECK (data_fim_prevista >= data_inicio_prevista)
);
CREATE INDEX IF NOT EXISTS idx_op_numero ON ordem_producao(numero_ordem);
CREATE INDEX IF NOT EXISTS idx_op_status ON ordem_producao(status);
CREATE INDEX IF NOT EXISTS idx_op_produto ON ordem_producao(cod_produto);
CREATE INDEX IF NOT EXISTS idx_op_data_inicio ON ordem_producao(data_inicio_prevista);
CREATE INDEX IF NOT EXISTS idx_op_linha ON ordem_producao(linha_producao);

-- 1.7 Requisição de Compras
CREATE TABLE IF NOT EXISTS requisicao_compras (
    id SERIAL PRIMARY KEY,
    num_requisicao VARCHAR(30) UNIQUE NOT NULL,
    data_requisicao_criacao DATE NOT NULL,
    usuario_requisicao_criacao VARCHAR(100),
    lead_time_requisicao INTEGER,
    lead_time_previsto INTEGER,
    data_requisicao_solicitada DATE,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_produto_requisicao NUMERIC(15,3) NOT NULL,
    qtd_produto_sem_requisicao NUMERIC(15,3) DEFAULT 0,
    necessidade BOOLEAN DEFAULT FALSE,
    data_necessidade DATE,
    status VARCHAR(20) DEFAULT 'Pendente' CHECK (status IN ('Pendente', 'Requisitada', 'Em Cotação', 'Pedido Colocado', 'Cancelada')),
    importado_odoo BOOLEAN DEFAULT FALSE,
    odoo_id VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_req_numero ON requisicao_compras(num_requisicao);
CREATE INDEX IF NOT EXISTS idx_req_produto ON requisicao_compras(cod_produto);
CREATE INDEX IF NOT EXISTS idx_req_status ON requisicao_compras(status);

-- 1.8 Pedido de Compras
CREATE TABLE IF NOT EXISTS pedido_compras (
    id SERIAL PRIMARY KEY,
    num_pedido VARCHAR(30) UNIQUE NOT NULL,
    num_requisicao VARCHAR(30),
    cnpj_fornecedor VARCHAR(20),
    raz_social VARCHAR(255),
    numero_nf VARCHAR(20),
    data_pedido_criacao DATE,
    usuario_pedido_criacao VARCHAR(100),
    lead_time_pedido INTEGER,
    lead_time_previsto INTEGER,
    data_pedido_previsao DATE,
    data_pedido_entrega DATE,
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    qtd_produto_pedido NUMERIC(15,3) NOT NULL,
    preco_produto_pedido NUMERIC(15,4),
    icms_produto_pedido NUMERIC(15,2),
    pis_produto_pedido NUMERIC(15,2),
    cofins_produto_pedido NUMERIC(15,2),
    confirmacao_pedido BOOLEAN DEFAULT FALSE,
    confirmado_por VARCHAR(100),
    confirmado_em TIMESTAMP,
    importado_odoo BOOLEAN DEFAULT FALSE,
    odoo_id VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (num_requisicao) REFERENCES requisicao_compras(num_requisicao)
);
CREATE INDEX IF NOT EXISTS idx_ped_numero ON pedido_compras(num_pedido);
CREATE INDEX IF NOT EXISTS idx_ped_requisicao ON pedido_compras(num_requisicao);
CREATE INDEX IF NOT EXISTS idx_ped_fornecedor ON pedido_compras(cnpj_fornecedor);
CREATE INDEX IF NOT EXISTS idx_ped_produto ON pedido_compras(cod_produto);

-- 1.9 Lead Time Fornecedor
CREATE TABLE IF NOT EXISTS lead_time_fornecedor (
    id SERIAL PRIMARY KEY,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    nome_fornecedor VARCHAR(255),
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),
    lead_time_previsto INTEGER NOT NULL,
    lead_time_historico NUMERIC(5,1),
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cnpj_fornecedor, cod_produto)
);
CREATE INDEX IF NOT EXISTS idx_ltf_fornecedor ON lead_time_fornecedor(cnpj_fornecedor);
CREATE INDEX IF NOT EXISTS idx_ltf_produto ON lead_time_fornecedor(cod_produto);

-- 1.10 Lista de Materiais (BOM)
CREATE TABLE IF NOT EXISTS lista_materiais (
    id SERIAL PRIMARY KEY,
    cod_produto_produzido VARCHAR(50) NOT NULL,
    nome_produto_produzido VARCHAR(255),
    cod_produto_componente VARCHAR(50) NOT NULL,
    nome_produto_componente VARCHAR(255),
    qtd_utilizada NUMERIC(15,6) NOT NULL,
    status VARCHAR(10) DEFAULT 'ativo' CHECK (status IN ('ativo', 'inativo')),
    versao VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    UNIQUE(cod_produto_produzido, cod_produto_componente, versao)
);
CREATE INDEX IF NOT EXISTS idx_lm_produzido ON lista_materiais(cod_produto_produzido);
CREATE INDEX IF NOT EXISTS idx_lm_componente ON lista_materiais(cod_produto_componente);
CREATE INDEX IF NOT EXISTS idx_lm_status ON lista_materiais(status);

-- 1.11 Log de Integração
CREATE TABLE IF NOT EXISTS log_integracao (
    id SERIAL PRIMARY KEY,
    tipo_integracao VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    mensagem TEXT,
    registros_processados INTEGER DEFAULT 0,
    registros_erro INTEGER DEFAULT 0,
    data_execucao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tempo_execucao FLOAT,
    detalhes JSONB
);

-- =====================================================
-- 2. ALTERAÇÕES EM TABELAS EXISTENTES
-- =====================================================

-- 2.1 Alterações em MovimentacaoEstoque
DO $$
BEGIN
    -- Adicionar colunas se não existirem
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'movimentacao_estoque' AND column_name = 'num_pedido') THEN
        ALTER TABLE movimentacao_estoque ADD COLUMN num_pedido VARCHAR(30);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'movimentacao_estoque' AND column_name = 'numero_nf') THEN
        ALTER TABLE movimentacao_estoque ADD COLUMN numero_nf VARCHAR(20);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'movimentacao_estoque' AND column_name = 'ordem_producao_id') THEN
        ALTER TABLE movimentacao_estoque ADD COLUMN ordem_producao_id INTEGER;
        ALTER TABLE movimentacao_estoque ADD CONSTRAINT fk_mov_ordem 
            FOREIGN KEY (ordem_producao_id) REFERENCES ordem_producao(id);
    END IF;
END $$;

-- Criar índices para MovimentacaoEstoque
CREATE INDEX IF NOT EXISTS idx_mov_pedido ON movimentacao_estoque(num_pedido);
CREATE INDEX IF NOT EXISTS idx_mov_nf ON movimentacao_estoque(numero_nf);
CREATE INDEX IF NOT EXISTS idx_mov_ordem ON movimentacao_estoque(ordem_producao_id);

-- 2.2 Alterações em CadastroPalletizacao
DO $$
BEGIN
    -- Adicionar colunas se não existirem
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cadastro_palletizacao' AND column_name = 'produto_comprado') THEN
        ALTER TABLE cadastro_palletizacao ADD COLUMN produto_comprado BOOLEAN DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cadastro_palletizacao' AND column_name = 'produto_produzido') THEN
        ALTER TABLE cadastro_palletizacao ADD COLUMN produto_produzido BOOLEAN DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cadastro_palletizacao' AND column_name = 'produto_vendido') THEN
        ALTER TABLE cadastro_palletizacao ADD COLUMN produto_vendido BOOLEAN DEFAULT TRUE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cadastro_palletizacao' AND column_name = 'lead_time_mto') THEN
        ALTER TABLE cadastro_palletizacao ADD COLUMN lead_time_mto INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cadastro_palletizacao' AND column_name = 'disparo_producao') THEN
        ALTER TABLE cadastro_palletizacao ADD COLUMN disparo_producao VARCHAR(3) 
            CHECK (disparo_producao IN ('MTO', 'MTS'));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'cadastro_palletizacao' AND column_name = 'custo_produto') THEN
        ALTER TABLE cadastro_palletizacao ADD COLUMN custo_produto NUMERIC(15,4);
    END IF;
END $$;

-- Criar índices para CadastroPalletizacao
CREATE INDEX IF NOT EXISTS idx_cp_comprado ON cadastro_palletizacao(produto_comprado);
CREATE INDEX IF NOT EXISTS idx_cp_produzido ON cadastro_palletizacao(produto_produzido);
CREATE INDEX IF NOT EXISTS idx_cp_vendido ON cadastro_palletizacao(produto_vendido);
CREATE INDEX IF NOT EXISTS idx_cp_disparo ON cadastro_palletizacao(disparo_producao);

-- 2.3 Alterações em CarteiraPrincipal
DO $$
BEGIN
    -- Adicionar colunas se não existirem
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'carteira_principal' AND column_name = 'ordem_producao_id') THEN
        ALTER TABLE carteira_principal ADD COLUMN ordem_producao_id INTEGER;
        ALTER TABLE carteira_principal ADD CONSTRAINT fk_cart_ordem 
            FOREIGN KEY (ordem_producao_id) REFERENCES ordem_producao(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'carteira_principal' AND column_name = 'disparo_producao') THEN
        ALTER TABLE carteira_principal ADD COLUMN disparo_producao VARCHAR(3);
    END IF;
END $$;

-- Criar índice para CarteiraPrincipal
CREATE INDEX IF NOT EXISTS idx_cart_ordem ON carteira_principal(ordem_producao_id);

-- =====================================================
-- 3. VIEWS ÚTEIS
-- =====================================================

-- View de demanda ativa (excluindo pedidos faturados)
CREATE OR REPLACE VIEW v_demanda_ativa AS
SELECT 
    s.cod_produto,
    s.nome_produto,
    EXTRACT(MONTH FROM s.expedicao) as mes,
    EXTRACT(YEAR FROM s.expedicao) as ano,
    SUM(s.qtd_saldo) as qtd_demanda
FROM separacao s
JOIN pedido p ON s.separacao_lote_id = p.separacao_lote_id
WHERE p.status != 'FATURADO'
GROUP BY s.cod_produto, s.nome_produto, mes, ano

UNION ALL

-- PreSeparacaoItem só se NÃO existe em Separacao
SELECT 
    psi.cod_produto,
    psi.nome_produto,
    EXTRACT(MONTH FROM psi.data_expedicao_editada) as mes,
    EXTRACT(YEAR FROM psi.data_expedicao_editada) as ano,
    SUM(psi.qtd_selecionada_usuario) as qtd_demanda
FROM pre_separacao_item psi
WHERE NOT EXISTS (
    SELECT 1 FROM separacao s
    WHERE s.separacao_lote_id = psi.separacao_lote_id
)
GROUP BY psi.cod_produto, psi.nome_produto, mes, ano;

-- View de estoque atual
CREATE OR REPLACE VIEW v_estoque_atual AS
SELECT 
    cod_produto,
    SUM(CASE 
        WHEN tipo_movimentacao IN ('ENTRADA_COMPRA', 'PRODUCAO', 'AJUSTE_POSITIVO') 
        THEN qtd_movimentacao
        WHEN tipo_movimentacao IN ('SAIDA_VENDA', 'CONSUMO_BOM', 'AJUSTE_NEGATIVO')
        THEN -qtd_movimentacao
        ELSE 0
    END) as estoque_atual
FROM movimentacao_estoque
GROUP BY cod_produto;

-- =====================================================
-- COMMIT FINAL
-- =====================================================
COMMIT;