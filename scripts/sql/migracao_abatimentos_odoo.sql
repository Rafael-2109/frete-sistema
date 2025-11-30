-- ============================================================================
-- MIGRAÇÃO: Sistema de Dupla Conferência - Abatimentos + Odoo
--
-- Este script:
-- 1. Cria tabela mapeamento_tipo_odoo
-- 2. Adiciona campos em contas_a_receber_abatimento
-- 3. Adiciona campos em contas_a_receber_reconciliacao
-- 4. Cria novos tipos de abatimento
-- 5. Cria mapeamentos iniciais
--
-- Para executar no Render Shell:
-- psql $DATABASE_URL -f scripts/sql/migracao_abatimentos_odoo.sql
--
-- Data: 2025-11-28
-- ============================================================================

-- ============================================================================
-- 1. CRIAR TABELA mapeamento_tipo_odoo
-- ============================================================================

CREATE TABLE IF NOT EXISTS mapeamento_tipo_odoo (
    id SERIAL PRIMARY KEY,
    tipo_sistema_id INTEGER NOT NULL REFERENCES contas_a_receber_tipos(id),
    tipo_odoo VARCHAR(50) NOT NULL,
    prioridade INTEGER DEFAULT 100,
    tolerancia_valor FLOAT DEFAULT 0.02,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por VARCHAR(100),
    CONSTRAINT uq_mapeamento_tipo_sistema_odoo UNIQUE (tipo_sistema_id, tipo_odoo)
);

CREATE INDEX IF NOT EXISTS idx_mapeamento_tipo_odoo ON mapeamento_tipo_odoo(tipo_odoo);
CREATE INDEX IF NOT EXISTS idx_mapeamento_tipo_sistema ON mapeamento_tipo_odoo(tipo_sistema_id);

-- ============================================================================
-- 2. ADICIONAR CAMPOS EM contas_a_receber_abatimento
-- ============================================================================

-- Campo para vincular ao Odoo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contas_a_receber_abatimento' AND column_name = 'reconciliacao_odoo_id'
    ) THEN
        ALTER TABLE contas_a_receber_abatimento
        ADD COLUMN reconciliacao_odoo_id INTEGER REFERENCES contas_a_receber_reconciliacao(id);
    END IF;
END $$;

-- Status de vinculação
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contas_a_receber_abatimento' AND column_name = 'status_vinculacao'
    ) THEN
        ALTER TABLE contas_a_receber_abatimento
        ADD COLUMN status_vinculacao VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL;
    END IF;
END $$;

-- Data da última tentativa de vinculação
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contas_a_receber_abatimento' AND column_name = 'ultima_tentativa_vinculacao'
    ) THEN
        ALTER TABLE contas_a_receber_abatimento
        ADD COLUMN ultima_tentativa_vinculacao TIMESTAMP;
    END IF;
END $$;

-- Índices
CREATE INDEX IF NOT EXISTS idx_abatimento_status_vinculacao ON contas_a_receber_abatimento(status_vinculacao);
CREATE INDEX IF NOT EXISTS idx_abatimento_reconciliacao ON contas_a_receber_abatimento(reconciliacao_odoo_id);

-- ============================================================================
-- 3. ADICIONAR CAMPOS EM contas_a_receber_reconciliacao
-- ============================================================================

-- Código do diário (para classificação)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contas_a_receber_reconciliacao' AND column_name = 'journal_code'
    ) THEN
        ALTER TABLE contas_a_receber_reconciliacao
        ADD COLUMN journal_code VARCHAR(20);
    END IF;
END $$;

-- ID do pagamento no Odoo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contas_a_receber_reconciliacao' AND column_name = 'payment_odoo_id'
    ) THEN
        ALTER TABLE contas_a_receber_reconciliacao
        ADD COLUMN payment_odoo_id INTEGER;
    END IF;
END $$;

-- Índice para tipo_baixa
CREATE INDEX IF NOT EXISTS idx_reconciliacao_tipo_baixa ON contas_a_receber_reconciliacao(tipo_baixa);

-- ============================================================================
-- 4. CRIAR NOVOS TIPOS DE ABATIMENTO
-- ============================================================================

-- DESCONTO ST
INSERT INTO contas_a_receber_tipos (tipo, tabela, campo, considera_a_receber, explicacao, ativo, criado_por, criado_em)
SELECT 'DESCONTO ST', 'contas_a_receber_abatimento', 'tipo', TRUE,
       'Abatimento referente a Substituição Tributária', TRUE, 'Sistema - Migração', NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos
    WHERE tipo = 'DESCONTO ST' AND tabela = 'contas_a_receber_abatimento' AND campo = 'tipo'
);

-- CONTRATO
INSERT INTO contas_a_receber_tipos (tipo, tabela, campo, considera_a_receber, explicacao, ativo, criado_por, criado_em)
SELECT 'CONTRATO', 'contas_a_receber_abatimento', 'tipo', TRUE,
       'Desconto por acordo/contrato comercial', TRUE, 'Sistema - Migração', NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos
    WHERE tipo = 'CONTRATO' AND tabela = 'contas_a_receber_abatimento' AND campo = 'tipo'
);

-- AJUSTE FINANCEIRO
INSERT INTO contas_a_receber_tipos (tipo, tabela, campo, considera_a_receber, explicacao, ativo, criado_por, criado_em)
SELECT 'AJUSTE FINANCEIRO', 'contas_a_receber_abatimento', 'tipo', TRUE,
       'Ajuste financeiro (juros, multa, outros)', TRUE, 'Sistema - Migração', NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos
    WHERE tipo = 'AJUSTE FINANCEIRO' AND tabela = 'contas_a_receber_abatimento' AND campo = 'tipo'
);

-- ============================================================================
-- 5. CRIAR MAPEAMENTOS INICIAIS (Sistema -> Odoo)
-- ============================================================================

-- VERBA -> abatimento_acordo
INSERT INTO mapeamento_tipo_odoo (tipo_sistema_id, tipo_odoo, prioridade, tolerancia_valor, ativo, criado_por)
SELECT t.id, 'abatimento_acordo', 10, 0.02, TRUE, 'Sistema - Migração'
FROM contas_a_receber_tipos t
WHERE t.tipo = 'VERBA' AND t.tabela = 'contas_a_receber_abatimento' AND t.campo = 'tipo'
AND NOT EXISTS (
    SELECT 1 FROM mapeamento_tipo_odoo m
    WHERE m.tipo_sistema_id = t.id AND m.tipo_odoo = 'abatimento_acordo'
);

-- ACAO COMERCIAL -> abatimento_acordo
INSERT INTO mapeamento_tipo_odoo (tipo_sistema_id, tipo_odoo, prioridade, tolerancia_valor, ativo, criado_por)
SELECT t.id, 'abatimento_acordo', 20, 0.02, TRUE, 'Sistema - Migração'
FROM contas_a_receber_tipos t
WHERE t.tipo = 'ACAO COMERCIAL' AND t.tabela = 'contas_a_receber_abatimento' AND t.campo = 'tipo'
AND NOT EXISTS (
    SELECT 1 FROM mapeamento_tipo_odoo m
    WHERE m.tipo_sistema_id = t.id AND m.tipo_odoo = 'abatimento_acordo'
);

-- DEVOLUCAO -> devolucao
INSERT INTO mapeamento_tipo_odoo (tipo_sistema_id, tipo_odoo, prioridade, tolerancia_valor, ativo, criado_por)
SELECT t.id, 'devolucao', 10, 0.02, TRUE, 'Sistema - Migração'
FROM contas_a_receber_tipos t
WHERE t.tipo = 'DEVOLUCAO' AND t.tabela = 'contas_a_receber_abatimento' AND t.campo = 'tipo'
AND NOT EXISTS (
    SELECT 1 FROM mapeamento_tipo_odoo m
    WHERE m.tipo_sistema_id = t.id AND m.tipo_odoo = 'devolucao'
);

-- DESCONTO ST -> abatimento_st
INSERT INTO mapeamento_tipo_odoo (tipo_sistema_id, tipo_odoo, prioridade, tolerancia_valor, ativo, criado_por)
SELECT t.id, 'abatimento_st', 10, 0.02, TRUE, 'Sistema - Migração'
FROM contas_a_receber_tipos t
WHERE t.tipo = 'DESCONTO ST' AND t.tabela = 'contas_a_receber_abatimento' AND t.campo = 'tipo'
AND NOT EXISTS (
    SELECT 1 FROM mapeamento_tipo_odoo m
    WHERE m.tipo_sistema_id = t.id AND m.tipo_odoo = 'abatimento_st'
);

-- CONTRATO -> abatimento_acordo
INSERT INTO mapeamento_tipo_odoo (tipo_sistema_id, tipo_odoo, prioridade, tolerancia_valor, ativo, criado_por)
SELECT t.id, 'abatimento_acordo', 30, 0.02, TRUE, 'Sistema - Migração'
FROM contas_a_receber_tipos t
WHERE t.tipo = 'CONTRATO' AND t.tabela = 'contas_a_receber_abatimento' AND t.campo = 'tipo'
AND NOT EXISTS (
    SELECT 1 FROM mapeamento_tipo_odoo m
    WHERE m.tipo_sistema_id = t.id AND m.tipo_odoo = 'abatimento_acordo'
);

-- AJUSTE FINANCEIRO -> abatimento_outros
INSERT INTO mapeamento_tipo_odoo (tipo_sistema_id, tipo_odoo, prioridade, tolerancia_valor, ativo, criado_por)
SELECT t.id, 'abatimento_outros', 10, 0.02, TRUE, 'Sistema - Migração'
FROM contas_a_receber_tipos t
WHERE t.tipo = 'AJUSTE FINANCEIRO' AND t.tabela = 'contas_a_receber_abatimento' AND t.campo = 'tipo'
AND NOT EXISTS (
    SELECT 1 FROM mapeamento_tipo_odoo m
    WHERE m.tipo_sistema_id = t.id AND m.tipo_odoo = 'abatimento_outros'
);

-- ============================================================================
-- 6. VERIFICAÇÃO
-- ============================================================================

SELECT '=== VERIFICAÇÃO DA MIGRAÇÃO ===' AS info;

SELECT 'Mapeamentos criados:' AS info, COUNT(*) AS total FROM mapeamento_tipo_odoo;

SELECT 'Novos tipos de abatimento:' AS info, COUNT(*) AS total
FROM contas_a_receber_tipos
WHERE tipo IN ('DESCONTO ST', 'CONTRATO', 'AJUSTE FINANCEIRO');

SELECT 'Colunas em abatimento:' AS info;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'contas_a_receber_abatimento'
  AND column_name IN ('reconciliacao_odoo_id', 'status_vinculacao', 'ultima_tentativa_vinculacao');

SELECT 'Colunas em reconciliacao:' AS info;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'contas_a_receber_reconciliacao'
  AND column_name IN ('journal_code', 'payment_odoo_id');

SELECT '=== MIGRAÇÃO CONCLUÍDA ===' AS info;
