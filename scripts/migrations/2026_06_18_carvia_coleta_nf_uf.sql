-- Migration: coluna `uf` em carvia_coleta_nfs + backfill das linhas ja vinculadas.
-- Data: 2026-06-18
-- Descricao:
--   A linha da coleta (papel de pao) ganha UF do destino. Como cidade/nome, a UF se
--   CONSOLIDA com a NF real ao vincular (uf_destinatario da CarviaNf vence). Esta migration:
--     1) adiciona a coluna `uf` (idempotente);
--     2) backfilla UF e cidade das linhas JA vinculadas a partir da CarviaNf
--        (so onde o destino esta vazio na linha e a NF tem o dado).
-- Idempotente (ADD COLUMN IF NOT EXISTS + UPDATE condicional).
ALTER TABLE carvia_coleta_nfs
    ADD COLUMN IF NOT EXISTS uf VARCHAR(2);

-- Backfill da UF a partir da NF vinculada (so onde a linha ainda nao tem UF).
UPDATE carvia_coleta_nfs ln
   SET uf = nf.uf_destinatario
  FROM carvia_nfs nf
 WHERE ln.carvia_nf_id = nf.id
   AND ln.uf IS NULL
   AND nf.uf_destinatario IS NOT NULL;

-- Backfill da cidade a partir da NF vinculada (so onde a linha ainda nao tem cidade).
UPDATE carvia_coleta_nfs ln
   SET cidade_destino = nf.cidade_destinatario
  FROM carvia_nfs nf
 WHERE ln.carvia_nf_id = nf.id
   AND (ln.cidade_destino IS NULL OR ln.cidade_destino = '')
   AND nf.cidade_destinatario IS NOT NULL;
