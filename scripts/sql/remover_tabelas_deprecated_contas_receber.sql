-- ============================================================
-- SCRIPT SQL: Remover Tabelas Deprecated de Contas a Receber
-- ============================================================
--
-- Executar no Shell do Render (PostgreSQL)
--
-- TABELAS A REMOVER:
-- 1. contas_a_receber_pagamento
-- 2. contas_a_receber_documento
-- 3. contas_a_receber_linha_credito
--
-- Data: 2025-11-28
-- ============================================================

-- 1. Verificar tabelas existentes (opcional)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'contas_a_receber_pagamento',
    'contas_a_receber_documento',
    'contas_a_receber_linha_credito'
);

-- 2. Contar registros antes de remover (opcional)
-- SELECT 'contas_a_receber_pagamento' as tabela, COUNT(*) as registros FROM contas_a_receber_pagamento
-- UNION ALL
-- SELECT 'contas_a_receber_documento', COUNT(*) FROM contas_a_receber_documento
-- UNION ALL
-- SELECT 'contas_a_receber_linha_credito', COUNT(*) FROM contas_a_receber_linha_credito;

-- 3. Remover FKs de contas_a_receber_reconciliacao (se existirem)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'contas_a_receber_reconciliacao'::regclass
        AND contype = 'f'
        AND (conname ILIKE '%payment%' OR conname ILIKE '%documento%')
    ) LOOP
        EXECUTE 'ALTER TABLE contas_a_receber_reconciliacao DROP CONSTRAINT IF EXISTS "' || r.conname || '"';
        RAISE NOTICE 'FK removida: %', r.conname;
    END LOOP;
END $$;

-- 4. Remover colunas deprecated de contas_a_receber_reconciliacao
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS payment_id;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS documento_id;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS debit_amount_currency;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS credit_amount_currency;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS debit_currency;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS credit_currency;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS full_reconcile_id;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS exchange_move_id;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS company_name;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS odoo_create_uid;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS odoo_create_user;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS odoo_write_uid;
ALTER TABLE contas_a_receber_reconciliacao DROP COLUMN IF EXISTS odoo_write_user;

-- 5. Remover tabelas deprecated (CASCADE remove índices e constraints)
DROP TABLE IF EXISTS contas_a_receber_pagamento CASCADE;
DROP TABLE IF EXISTS contas_a_receber_documento CASCADE;
DROP TABLE IF EXISTS contas_a_receber_linha_credito CASCADE;

-- 6. Verificar que foram removidas
SELECT 'Tabelas restantes:' as status, table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'contas_a_receber%'
ORDER BY table_name;

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================
