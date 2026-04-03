-- Backfill: Marcar faturas cliente como PAGA quando conciliacao ja e 100%
-- A regra R11 foi implementada no service, mas faturas anteriores ficaram pendentes.
-- Executar via Render Shell (idempotente)

-- Verificar ANTES
SELECT status, COUNT(*) as qtd
FROM carvia_faturas_cliente
GROUP BY status
ORDER BY status;

-- Listar afetadas
SELECT id, numero_fatura, status, valor_total, total_conciliado, cnpj_cliente
FROM carvia_faturas_cliente
WHERE status NOT IN ('PAGA', 'CANCELADA')
  AND total_conciliado >= valor_total - 0.01
  AND valor_total > 0
ORDER BY id;

-- Executar backfill
UPDATE carvia_faturas_cliente
SET status = 'PAGA',
    pago_em = NOW(),
    pago_por = 'BACKFILL_CONCILIACAO',
    conciliado = true
WHERE status NOT IN ('PAGA', 'CANCELADA')
  AND total_conciliado >= valor_total - 0.01
  AND valor_total > 0;

-- Verificar DEPOIS
SELECT status, COUNT(*) as qtd
FROM carvia_faturas_cliente
GROUP BY status
ORDER BY status;
