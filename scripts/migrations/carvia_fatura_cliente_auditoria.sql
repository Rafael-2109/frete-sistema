-- Migration: adicionar auditoria de conferencia a CarviaFaturaCliente
--
-- Refator 2.1 do plano shiny-wiggling-harbor. Espelha os campos de
-- CarviaFaturaTransportadora, adicionando eixo de conferencia gerencial
-- manual ao dominio venda.
--
-- Idempotente (IF NOT EXISTS). Seguro para rodar multiplas vezes.
--
-- Ref: app/carvia/models/faturas.py (CarviaFaturaCliente)
-- Ref: /.claude/plans/sequential-wibbling-kahn.md Secao 4 P1

BEGIN;

ALTER TABLE carvia_faturas_cliente
    ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20)
        NOT NULL DEFAULT 'PENDENTE',
    ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100),
    ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP,
    ADD COLUMN IF NOT EXISTS observacoes_conferencia TEXT;

CREATE INDEX IF NOT EXISTS ix_carvia_faturas_cliente_status_conferencia
    ON carvia_faturas_cliente (status_conferencia);

COMMIT;

-- Verificacao pos-migration (executar manualmente):
--
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'carvia_faturas_cliente'
--   AND column_name IN ('status_conferencia', 'conferido_por',
--                       'conferido_em', 'observacoes_conferencia')
-- ORDER BY column_name;
--
-- SELECT COUNT(*) AS total,
--        SUM(CASE WHEN status_conferencia = 'PENDENTE' THEN 1 ELSE 0 END) AS pendentes
-- FROM carvia_faturas_cliente;
