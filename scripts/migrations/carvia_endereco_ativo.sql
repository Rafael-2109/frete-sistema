-- Migration: Coluna `ativo` em carvia_cliente_enderecos + recriacao de indices parciais
-- Data: 16/04/2026
-- Descricao:
--   1. Adiciona coluna `ativo BOOLEAN NOT NULL DEFAULT TRUE` para suportar soft-delete
--   2. Recria uq_carvia_end_cliente_cnpj_tipo com AND ativo = TRUE (senao registro
--      desativado continua bloqueando cadastros novos).
--   3. Recria uq_carvia_end_origem_global com AND ativo = TRUE (mesmo motivo).
--
-- Objetivo: permitir que enderecos incorretos sejam marcados como inativos sem
-- quebrar historico (cotacoes existentes) nem bloquear o cadastro correto.
-- Idempotente.

-- 1. Adicionar coluna ativo (idempotente)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_cliente_enderecos'
          AND column_name = 'ativo'
    ) THEN
        ALTER TABLE carvia_cliente_enderecos
          ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
END $$;

-- 2. Dropar indices antigos (serao recriados com filtro ativo=TRUE)
DROP INDEX IF EXISTS uq_carvia_end_cliente_cnpj_tipo;
DROP INDEX IF EXISTS uq_carvia_end_origem_global;

-- 3. Recriar uq_carvia_end_cliente_cnpj_tipo com filtro ativo=TRUE
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_end_cliente_cnpj_tipo
  ON carvia_cliente_enderecos (cliente_id, cnpj, tipo)
  WHERE cnpj IS NOT NULL AND cliente_id IS NOT NULL AND ativo = TRUE;

-- 4. Recriar uq_carvia_end_origem_global com filtro ativo=TRUE
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_end_origem_global
  ON carvia_cliente_enderecos (cnpj)
  WHERE tipo = 'ORIGEM' AND cliente_id IS NULL AND cnpj IS NOT NULL AND ativo = TRUE;

-- 5. Index auxiliar para filtrar rapidamente enderecos ativos em listagens
CREATE INDEX IF NOT EXISTS ix_carvia_endereco_ativo
  ON carvia_cliente_enderecos (ativo)
  WHERE ativo = FALSE;
