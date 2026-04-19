-- Migration B2 (2026-04-18) — UniqueConstraints parciais em numeros
-- sequenciais CarVia (exceto CANCELADO, que pode reusar numeros legitimamente).
--
-- Design pos-baseline: baseline_pre_sprint_a detectou 8 dupes em
-- carvia_subcontratos.cte_numero — todas CANCELADO+CONFIRMADO (legit).
-- Constraint simples quebraria fluxo operacional. Parcial WHERE
-- status != 'CANCELADO' respeita o padrao existente de CarviaFrete
-- (R7 do CLAUDE.md — numero_sequencial_transportadora).
--
-- Idempotente (IF NOT EXISTS).
--
-- Uso Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/carvia_b2_unique_numeros_sequenciais.sql

BEGIN;

-- 1. carvia_operacoes.cte_numero
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_carvia_operacoes_cte_numero_ativo
    ON carvia_operacoes (cte_numero)
    WHERE cte_numero IS NOT NULL AND status != 'CANCELADO';

-- 2. carvia_subcontratos.cte_numero
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_carvia_subcontratos_cte_numero_ativo
    ON carvia_subcontratos (cte_numero)
    WHERE cte_numero IS NOT NULL AND status != 'CANCELADO';

-- 3. carvia_cte_complementares.numero_comp
CREATE UNIQUE INDEX IF NOT EXISTS
    uq_carvia_cte_complementares_numero_comp_ativo
    ON carvia_cte_complementares (numero_comp)
    WHERE numero_comp IS NOT NULL AND status != 'CANCELADO';

COMMIT;
