-- ================================================================
-- SCRIPT SQL: Adicionar campos Odoo em DespesaExtra
-- ================================================================
-- Executar no Shell do Render (PostgreSQL)
-- Data: 2025-01-22
-- ================================================================

-- ================================================================
-- ETAPA 1: Adicionar campo STATUS
-- ================================================================
ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE';

CREATE INDEX IF NOT EXISTS idx_despesas_extras_status
ON despesas_extras(status);

-- ================================================================
-- ETAPA 2: Adicionar campo despesa_cte_id (FK)
-- ================================================================
ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS despesa_cte_id INTEGER;

-- Verificar se constraint já existe antes de criar
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_despesa_extra_cte'
        AND table_name = 'despesas_extras'
    ) THEN
        ALTER TABLE despesas_extras
        ADD CONSTRAINT fk_despesa_extra_cte
        FOREIGN KEY (despesa_cte_id)
        REFERENCES conhecimento_transporte(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_despesas_extras_cte_id
ON despesas_extras(despesa_cte_id);

-- ================================================================
-- ETAPA 3: Adicionar campo chave_cte
-- ================================================================
ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS chave_cte VARCHAR(44);

CREATE INDEX IF NOT EXISTS idx_despesas_extras_chave_cte
ON despesas_extras(chave_cte);

-- ================================================================
-- ETAPA 4: Adicionar campos Odoo (dfe_id, po_id, invoice_id)
-- ================================================================
ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS odoo_dfe_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_despesas_extras_odoo_dfe_id
ON despesas_extras(odoo_dfe_id);

ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS odoo_purchase_order_id INTEGER;

ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS odoo_invoice_id INTEGER;

-- ================================================================
-- ETAPA 5: Adicionar campos de auditoria Odoo
-- ================================================================
ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS lancado_odoo_em TIMESTAMP;

ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS lancado_odoo_por VARCHAR(100);

-- ================================================================
-- ETAPA 6: Adicionar campos de comprovante (NFS/Recibo)
-- ================================================================
ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS comprovante_path VARCHAR(500);

ALTER TABLE despesas_extras
ADD COLUMN IF NOT EXISTS comprovante_nome_arquivo VARCHAR(255);

-- ================================================================
-- ETAPA 7: Adicionar campo despesa_extra_id na auditoria
-- ================================================================
ALTER TABLE lancamento_frete_odoo_auditoria
ADD COLUMN IF NOT EXISTS despesa_extra_id INTEGER;

-- Verificar se constraint já existe antes de criar
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_auditoria_despesa_extra'
        AND table_name = 'lancamento_frete_odoo_auditoria'
    ) THEN
        ALTER TABLE lancamento_frete_odoo_auditoria
        ADD CONSTRAINT fk_auditoria_despesa_extra
        FOREIGN KEY (despesa_extra_id)
        REFERENCES despesas_extras(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_auditoria_despesa_extra_id
ON lancamento_frete_odoo_auditoria(despesa_extra_id);

-- ================================================================
-- ETAPA 8: Migrar dados - Definir status inicial
-- ================================================================

-- Verificar quantidades antes da migração
SELECT
    COUNT(*) as total,
    COUNT(fatura_frete_id) as com_fatura,
    COUNT(*) - COUNT(fatura_frete_id) as sem_fatura
FROM despesas_extras;

-- Atualizar despesas COM fatura_frete_id para LANCADO
UPDATE despesas_extras
SET status = 'LANCADO'
WHERE fatura_frete_id IS NOT NULL
AND status = 'PENDENTE';

-- Verificar resultado
SELECT status, COUNT(*) as quantidade
FROM despesas_extras
GROUP BY status
ORDER BY status;

-- ================================================================
-- VALIDAÇÃO FINAL
-- ================================================================
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'despesas_extras'
ORDER BY ordinal_position;
