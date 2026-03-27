-- Migration: Adicionar colunas valor_unitario e valor_total em carvia_cotacao_motos
-- Data: 2026-03-27
-- Motivo: Model CarviaCotacaoMoto declara essas colunas mas a migration original nao as incluiu
--         Causa 500 em /carvia/cotacoes/<id> (Sentry: ProgrammingError UndefinedColumn)
-- Uso: Executar no Render Shell (SQL idempotente)

ALTER TABLE carvia_cotacao_motos
    ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS valor_total NUMERIC(15,2);
