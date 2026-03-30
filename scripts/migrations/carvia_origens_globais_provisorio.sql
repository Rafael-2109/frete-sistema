-- Migration: Origens globais + destinos provisorios
-- Data: 30/03/2026
-- Descricao: Permite origens compartilhadas (cliente_id NULL) e destinos
--            provisorios sem CNPJ (cnpj NULL, provisorio=TRUE).
--
-- Alteracoes em carvia_cliente_enderecos:
--   1. cliente_id -> nullable (origens globais nao tem cliente)
--   2. cnpj -> nullable (destinos provisorios)
--   3. Nova coluna provisorio BOOLEAN
--   4. Constraints parciais substituem unique antiga

-- 1. Tornar cliente_id nullable
ALTER TABLE carvia_cliente_enderecos
  ALTER COLUMN cliente_id DROP NOT NULL;

-- 2. Tornar cnpj nullable
ALTER TABLE carvia_cliente_enderecos
  ALTER COLUMN cnpj DROP NOT NULL;

-- 3. Adicionar coluna provisorio
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cliente_enderecos'
          AND column_name = 'provisorio'
    ) THEN
        ALTER TABLE carvia_cliente_enderecos
          ADD COLUMN provisorio BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

-- 4. Drop unique constraint antiga (nome pode variar)
ALTER TABLE carvia_cliente_enderecos
  DROP CONSTRAINT IF EXISTS uq_carvia_cliente_endereco;

-- 5. Unique parcial: destinos por cliente (cnpj preenchido)
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_end_cliente_cnpj_tipo
  ON carvia_cliente_enderecos (cliente_id, cnpj, tipo)
  WHERE cnpj IS NOT NULL AND cliente_id IS NOT NULL;

-- 6. Unique parcial: origens globais (sem duplicata de CNPJ)
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_end_origem_global
  ON carvia_cliente_enderecos (cnpj)
  WHERE tipo = 'ORIGEM' AND cliente_id IS NULL AND cnpj IS NOT NULL;

-- 7. Index para busca de origens globais
CREATE INDEX IF NOT EXISTS ix_carvia_end_origem_global
  ON carvia_cliente_enderecos (tipo, provisorio)
  WHERE cliente_id IS NULL;
