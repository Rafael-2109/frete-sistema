-- Migration: Unique constraints em faturas CarVia
-- Previne duplicatas na importacao de faturas PDF
--
-- IMPORTANTE: Executar fix_carvia_faturas_duplicadas.sql ANTES deste script,
-- pois o unique index falhara se duplicatas ainda existirem.
--
-- Execucao: Render Shell (psql)

-- 1. carvia_faturas_cliente: UNIQUE(numero_fatura, cnpj_cliente)
CREATE UNIQUE INDEX IF NOT EXISTS uq_fatura_cliente_num_cnpj
    ON carvia_faturas_cliente (numero_fatura, cnpj_cliente);

-- 2. carvia_faturas_transportadora: UNIQUE(numero_fatura, transportadora_id)
CREATE UNIQUE INDEX IF NOT EXISTS uq_fatura_transp_num_transp
    ON carvia_faturas_transportadora (numero_fatura, transportadora_id);
