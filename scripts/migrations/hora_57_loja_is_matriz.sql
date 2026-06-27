-- Idempotente. Adiciona is_matriz (BOOLEAN NOT NULL DEFAULT FALSE) a hora_loja.
-- A matriz (CNPJ 62634044000120 = "HORA Comercio de Motocicletas Eletricas LTDA",
-- emitente fiscal de TODAS as NFes — invariante CLAUDE.md secao 7) NAO vende: e
-- marcada com is_matriz=TRUE para ser EXCLUIDA das superficies de venda (rankings,
-- escopos, dropdowns, contagens) e nunca ser gravada como loja_id de uma venda.
-- Permanece ativa (default de NF de entrada + alvo do resolver de divergencia).
-- Migration HORA 57 (2026-06-27).
ALTER TABLE hora_loja ADD COLUMN IF NOT EXISTS is_matriz BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE hora_loja
   SET is_matriz = TRUE
 WHERE regexp_replace(cnpj, '\D', '', 'g') = '62634044000120'
   AND is_matriz = FALSE;
