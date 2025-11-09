-- ==========================================================================================================
-- CRIAR TABELA historico_pedido_compras NO RENDER
-- ==========================================================================================================
--
-- IMPORTANTE: Execute este script no Shell do Render (PostgreSQL)
--
-- Acesso:
--   1. Dashboard Render → Database → Connect → External Connection
--   2. Copie e cole este SQL completo no Shell
--   3. Execute linha por linha ou bloco por bloco
--
-- FUNÇÃO:
--   - Cria tabela de histórico com SNAPSHOT COMPLETO de todos os campos de pedido_compras
--   - Registra TODAS as modificações vindas do Odoo (operações CRIAR e EDITAR)
--   - Permite comparar qualquer campo entre versões no modal
--
-- ESTRUTURA:
--   - Campos de controle: pedido_compra_id, operacao, alterado_em, alterado_por, write_date_odoo
--   - Snapshot completo: TODOS os 27 campos da tabela pedido_compras
--
-- Data: 2025-11-09
-- ==========================================================================================================

-- ==========================================================================================================
-- PASSO 1: VERIFICAR SE TABELA JÁ EXISTE
-- ==========================================================================================================

SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'historico_pedido_compras'
);

-- Se retornar 't' (true), a tabela já existe
-- Se retornar 'f' (false), pode prosseguir com criação


-- ==========================================================================================================
-- PASSO 2: REMOVER TABELA EXISTENTE (CUIDADO! Apenas se necessário recriar)
-- ==========================================================================================================

-- ⚠️  ATENÇÃO: Isso apaga TODOS os dados históricos!
-- Descomente apenas se tiver certeza:

-- DROP TABLE IF EXISTS historico_pedido_compras CASCADE;


-- ==========================================================================================================
-- PASSO 3: CRIAR TABELA historico_pedido_compras
-- ==========================================================================================================

CREATE TABLE historico_pedido_compras (
    id SERIAL PRIMARY KEY,

    -- ================================================
    -- CAMPOS DE CONTROLE DO HISTÓRICO
    -- ================================================
    pedido_compra_id INTEGER NOT NULL REFERENCES pedido_compras(id) ON DELETE CASCADE,
    operacao VARCHAR(20) NOT NULL,  -- 'CRIAR', 'EDITAR'
    alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alterado_por VARCHAR(100) NOT NULL,  -- 'Odoo' ou usuário
    write_date_odoo TIMESTAMP,

    -- ================================================
    -- SNAPSHOT COMPLETO - MESMOS CAMPOS DO PEDIDOCOMPRAS
    -- ================================================

    -- Campos principais
    num_pedido VARCHAR(30) NOT NULL,
    num_requisicao VARCHAR(30),
    cnpj_fornecedor VARCHAR(20),
    raz_social VARCHAR(255),
    numero_nf VARCHAR(20),

    -- Datas
    data_pedido_criacao DATE,
    usuario_pedido_criacao VARCHAR(100),
    lead_time_pedido INTEGER,
    lead_time_previsto INTEGER,
    data_pedido_previsao DATE,
    data_pedido_entrega DATE,

    -- Produto
    cod_produto VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(255),

    -- Quantidades e valores
    qtd_produto_pedido NUMERIC(15, 3) NOT NULL,
    qtd_recebida NUMERIC(15, 3) DEFAULT 0,
    preco_produto_pedido NUMERIC(15, 4),
    icms_produto_pedido NUMERIC(15, 2),
    pis_produto_pedido NUMERIC(15, 2),
    cofins_produto_pedido NUMERIC(15, 2),

    -- Confirmação
    confirmacao_pedido BOOLEAN DEFAULT FALSE,
    confirmado_por VARCHAR(100),
    confirmado_em TIMESTAMP,

    -- Status e tipo
    status_odoo VARCHAR(20),
    tipo_pedido VARCHAR(50),

    -- Vínculo com Odoo
    importado_odoo BOOLEAN DEFAULT FALSE,
    odoo_id VARCHAR(50),

    -- Datas originais
    criado_em TIMESTAMP,
    atualizado_em TIMESTAMP
);


-- ==========================================================================================================
-- PASSO 4: CRIAR ÍNDICES PARA PERFORMANCE
-- ==========================================================================================================

-- Índice principal: busca por pedido_compra_id
CREATE INDEX idx_hist_ped_pedido ON historico_pedido_compras(pedido_compra_id);

-- Índice composto: busca por pedido + ordenação por data
CREATE INDEX idx_hist_ped_pedido_data ON historico_pedido_compras(pedido_compra_id, alterado_em DESC);

-- Índice composto: busca por número de pedido + data
CREATE INDEX idx_hist_ped_num_data ON historico_pedido_compras(num_pedido, alterado_em DESC);

-- Índice: busca por produto
CREATE INDEX idx_hist_ped_produto ON historico_pedido_compras(cod_produto);

-- Índice: filtro por operação
CREATE INDEX idx_hist_ped_operacao ON historico_pedido_compras(operacao);

-- Índice: filtro por quem alterou
CREATE INDEX idx_hist_ped_alterado_por ON historico_pedido_compras(alterado_por);


-- ==========================================================================================================
-- PASSO 5: VERIFICAR CRIAÇÃO
-- ==========================================================================================================

-- Verificar colunas criadas
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'historico_pedido_compras'
ORDER BY ordinal_position;

-- Verificar índices criados
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'historico_pedido_compras'
ORDER BY indexname;

-- Contar registros (deve retornar 0 após criação)
SELECT COUNT(*) FROM historico_pedido_compras;


-- ==========================================================================================================
-- PASSO 6: GRANT DE PERMISSÕES (SE NECESSÁRIO)
-- ==========================================================================================================

-- Normalmente não é necessário no Render, mas caso precise:
-- GRANT ALL PRIVILEGES ON TABLE historico_pedido_compras TO seu_usuario;
-- GRANT USAGE, SELECT ON SEQUENCE historico_pedido_compras_id_seq TO seu_usuario;


-- ==========================================================================================================
-- ✅ CONCLUSÃO
-- ==========================================================================================================
--
-- Tabela historico_pedido_compras criada com sucesso!
--
-- PRÓXIMOS PASSOS:
--   1. Execute a sincronização de pedidos de compras (automática a cada 90 minutos)
--   2. A cada criação/edição, um snapshot completo será gravado
--   3. Você pode comparar versões no modal da interface
--
-- CAMPOS GRAVADOS: 27 campos completos (incluindo qtd_recebida e tipo_pedido)
--
-- OPERAÇÕES REGISTRADAS:
--   - CRIAR: Quando pedido é importado do Odoo pela primeira vez
--   - EDITAR: Quando qualquer campo é alterado no Odoo
--
-- ==========================================================================================================
