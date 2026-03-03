-- ============================================================
-- LIMPEZA COMPLETA DAS TABELAS CARVIA
-- ============================================================
-- Motivo: Dados importados ANTES da implementacao de
--         armazenamento de PDFs no S3 (Amazon).
--         Necessario limpar para reimportar com S3 ativo.
--
-- Tabelas afetadas (11):
--   carvia_conta_movimentacoes      (0 registros)
--   carvia_fatura_transportadora_itens (0 registros)
--   carvia_faturas_transportadora   (0 registros)
--   carvia_fatura_cliente_itens     (31 registros)
--   carvia_faturas_cliente          (23 registros)
--   carvia_subcontratos             (0 registros)
--   carvia_operacao_nfs             (19 registros)
--   carvia_operacoes                (31 registros)
--   carvia_nf_itens                 (69 registros)
--   carvia_nfs                      (23 registros)
--   carvia_despesas                 (0 registros)
--
-- Total: 196 registros
--
-- Uso: Executar no Render Shell (psql)
-- ============================================================

BEGIN;

-- TRUNCATE com CASCADE resolve automaticamente a ordem de FK
-- RESTART IDENTITY reseta as sequences (IDs voltam a 1)
TRUNCATE TABLE
    carvia_conta_movimentacoes,
    carvia_fatura_transportadora_itens,
    carvia_faturas_transportadora,
    carvia_fatura_cliente_itens,
    carvia_faturas_cliente,
    carvia_despesas,
    carvia_subcontratos,
    carvia_operacao_nfs,
    carvia_operacoes,
    carvia_nf_itens,
    carvia_nfs
RESTART IDENTITY CASCADE;

-- Verificacao pos-limpeza
SELECT 'carvia_nfs' AS tabela, COUNT(*) AS registros FROM carvia_nfs
UNION ALL SELECT 'carvia_nf_itens', COUNT(*) FROM carvia_nf_itens
UNION ALL SELECT 'carvia_operacoes', COUNT(*) FROM carvia_operacoes
UNION ALL SELECT 'carvia_operacao_nfs', COUNT(*) FROM carvia_operacao_nfs
UNION ALL SELECT 'carvia_faturas_cliente', COUNT(*) FROM carvia_faturas_cliente
UNION ALL SELECT 'carvia_fatura_cliente_itens', COUNT(*) FROM carvia_fatura_cliente_itens
UNION ALL SELECT 'carvia_faturas_transportadora', COUNT(*) FROM carvia_faturas_transportadora
UNION ALL SELECT 'carvia_fatura_transportadora_itens', COUNT(*) FROM carvia_fatura_transportadora_itens
UNION ALL SELECT 'carvia_subcontratos', COUNT(*) FROM carvia_subcontratos
UNION ALL SELECT 'carvia_despesas', COUNT(*) FROM carvia_despesas
UNION ALL SELECT 'carvia_conta_movimentacoes', COUNT(*) FROM carvia_conta_movimentacoes
ORDER BY tabela;

COMMIT;
