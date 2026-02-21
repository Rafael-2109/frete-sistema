-- ============================================================================
-- Backfill Marco Zero: SQL de Verificacao PRE/POS
-- ============================================================================
-- Executar no Render Shell antes e depois do backfill para validar resultados.
--
-- Data: 2026-02-21
-- ============================================================================

-- PRE: Contagem antes do backfill
-- ============================================================================

-- Total de titulos nao pagos por tabela
SELECT 'contas_a_pagar' AS tabela, COUNT(*) AS nao_pagos
FROM contas_a_pagar WHERE parcela_paga = false;

SELECT 'contas_a_receber' AS tabela, COUNT(*) AS nao_pagos
FROM contas_a_receber WHERE parcela_paga = false;

-- Detalhe: nao pagos com odoo_line_id (contas_a_pagar) — candidatos ao backfill
SELECT 'contas_a_pagar_com_odoo_id' AS tabela, COUNT(*) AS candidatos
FROM contas_a_pagar WHERE parcela_paga = false AND odoo_line_id IS NOT NULL;

-- Detalhe: nao pagos sem odoo_line_id (contas_a_pagar) — NAO serao processados
SELECT 'contas_a_pagar_sem_odoo_id' AS tabela, COUNT(*) AS sem_link
FROM contas_a_pagar WHERE parcela_paga = false AND odoo_line_id IS NULL;

-- Distribuicao por empresa
SELECT empresa, COUNT(*) AS nao_pagos
FROM contas_a_pagar WHERE parcela_paga = false
GROUP BY empresa ORDER BY empresa;

SELECT empresa, COUNT(*) AS nao_pagos
FROM contas_a_receber WHERE parcela_paga = false
GROUP BY empresa ORDER BY empresa;


-- POS: Titulos atualizados pelo backfill
-- ============================================================================

SELECT 'contas_a_pagar' AS tabela, COUNT(*) AS backfill
FROM contas_a_pagar WHERE atualizado_por = 'Backfill Marco Zero';

SELECT 'contas_a_receber' AS tabela, COUNT(*) AS backfill
FROM contas_a_receber WHERE atualizado_por = 'Backfill Marco Zero';

-- Verificar se ainda restam nao pagos (esperado: menos que antes)
SELECT 'contas_a_pagar' AS tabela, COUNT(*) AS restantes_nao_pagos
FROM contas_a_pagar WHERE parcela_paga = false;

SELECT 'contas_a_receber' AS tabela, COUNT(*) AS restantes_nao_pagos
FROM contas_a_receber WHERE parcela_paga = false;
