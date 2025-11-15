-- ============================================================================
-- Script SQL: Criar Tabela lancamento_frete_odoo_auditoria
-- ============================================================================
-- OBJETIVO: Criar tabela de auditoria para lançamentos de frete no Odoo
-- AUTOR: Sistema de Fretes
-- DATA: 14/11/2025
-- USO: Copiar e colar no Shell do Render (PostgreSQL)
-- ============================================================================

-- 1. Remover tabela antiga (se existir)
DROP TABLE IF EXISTS lancamento_frete_odoo_auditoria CASCADE;

-- 2. Criar tabela
CREATE TABLE lancamento_frete_odoo_auditoria (
    id SERIAL PRIMARY KEY,

    -- Identificação do lançamento
    frete_id INTEGER REFERENCES fretes(id),
    cte_id INTEGER REFERENCES conhecimento_transporte(id),
    chave_cte VARCHAR(44) NOT NULL,

    -- IDs do Odoo gerados
    dfe_id INTEGER,
    purchase_order_id INTEGER,
    invoice_id INTEGER,

    -- Etapa do processo (1-16)
    etapa INTEGER NOT NULL,
    etapa_descricao VARCHAR(255) NOT NULL,

    -- Modelo e ação Odoo
    modelo_odoo VARCHAR(100) NOT NULL,
    metodo_odoo VARCHAR(100),
    acao VARCHAR(50) NOT NULL,

    -- Dados ANTES e DEPOIS (JSON)
    dados_antes TEXT,
    dados_depois TEXT,

    -- Campos alterados
    campos_alterados TEXT,

    -- Status da etapa
    status VARCHAR(20) NOT NULL DEFAULT 'SUCESSO',
    mensagem TEXT,
    erro_detalhado TEXT,

    -- Contexto adicional
    contexto_odoo TEXT,

    -- Tempo de execução
    tempo_execucao_ms INTEGER,

    -- Auditoria
    executado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    executado_por VARCHAR(100) NOT NULL,
    ip_usuario VARCHAR(50)
);

-- 3. Criar índices
CREATE INDEX idx_auditoria_frete_id ON lancamento_frete_odoo_auditoria(frete_id);
CREATE INDEX idx_auditoria_cte_id ON lancamento_frete_odoo_auditoria(cte_id);
CREATE INDEX idx_auditoria_chave_cte ON lancamento_frete_odoo_auditoria(chave_cte);
CREATE INDEX idx_auditoria_etapa ON lancamento_frete_odoo_auditoria(etapa);
CREATE INDEX idx_auditoria_executado_em ON lancamento_frete_odoo_auditoria(executado_em);
CREATE INDEX idx_auditoria_status ON lancamento_frete_odoo_auditoria(status);

-- 4. Verificar criação
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'lancamento_frete_odoo_auditoria') as total_colunas
FROM information_schema.tables
WHERE table_name = 'lancamento_frete_odoo_auditoria';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================
