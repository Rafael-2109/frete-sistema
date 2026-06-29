-- Migration Pessoal 01: suporte a Nubank (OFX) — contas + casamento de transferencias.
-- Idempotente (IF NOT EXISTS / ALTER TYPE re-aplicavel). Para Render Shell / psql.

-- 1. numero_conta comporta o ACCTID UUID do cartao Nubank (36 chars)
ALTER TABLE pessoal_contas ALTER COLUMN numero_conta TYPE VARCHAR(50);

-- 2. Coluna de casamento entre as duas pontas de uma transferencia propria
ALTER TABLE pessoal_transacoes ADD COLUMN IF NOT EXISTS transferencia_par_id INTEGER;

-- 3. FK self-referencial (ON DELETE SET NULL), criada so se ainda nao existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_pessoal_transacoes_transferencia_par'
    ) THEN
        ALTER TABLE pessoal_transacoes
            ADD CONSTRAINT fk_pessoal_transacoes_transferencia_par
            FOREIGN KEY (transferencia_par_id)
            REFERENCES pessoal_transacoes (id) ON DELETE SET NULL;
    END IF;
END$$;

-- 4. Indice parcial
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_transf_par
    ON pessoal_transacoes (transferencia_par_id)
    WHERE transferencia_par_id IS NOT NULL;
