-- Migration: flag local_cd em carvia_pedidos + carvia_cotacoes (Frente A do redesign)
-- Data: 2026-06-18
-- Descricao:
--   A VIEW pedidos (Partes 2A/2B) expoe hoje local_cd CarVia = literal fixo
--   'VICTORIO_MARCHEZINE'. Para a tela /pedidos/lista_pedidos refletir o CD REAL
--   (VM/TM) de um pedido CarVia, a flag precisa MORAR em carvia_pedidos/cotacoes —
--   alimentada por propagacao a partir da Coleta (fonte: CarviaColeta.local_cd ->
--   CarviaNf.local_cd -> CarviaPedido/CarviaCotacao via numero_nf). Na VIEW e SO LEITURA.
--
--   BACKFILL: ADD COLUMN NOT NULL DEFAULT 'VICTORIO_MARCHEZINE' preenche o historico
--   (metadata-only no PG 11+). Em seguida, propaga TM retroativo a partir das CarviaNf
--   ja marcadas (= coletas TM existentes), via numero_nf normalizado.
--
--   NAO recria a VIEW pedidos — isso fica na migration alterar_view_pedidos_v12_*.
-- Idempotente (ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).

-- ============================================================
-- 1. Colunas local_cd (NOT NULL default VM = backfill historico)
-- ============================================================
ALTER TABLE carvia_cotacoes
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

ALTER TABLE carvia_pedidos
    ADD COLUMN IF NOT EXISTS local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE';

-- ============================================================
-- 2. Indices parciais (TM e minoria; VM e o default dominante)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_carvia_cotacoes_local_cd
    ON carvia_cotacoes (local_cd) WHERE local_cd <> 'VICTORIO_MARCHEZINE';
CREATE INDEX IF NOT EXISTS idx_carvia_pedidos_local_cd
    ON carvia_pedidos (local_cd) WHERE local_cd <> 'VICTORIO_MARCHEZINE';

-- ============================================================
-- 3. Backfill TM retroativo a partir das CarviaNf (= Coleta) via numero_nf
--    Normalizacao = mesma do coleta_service (_norm_nf): so digitos, sem zeros a esq.
-- ============================================================
UPDATE carvia_pedidos ped
SET local_cd = sub.local_cd
FROM (
    SELECT DISTINCT pi.pedido_id, nf.local_cd
    FROM carvia_pedido_itens pi
    JOIN carvia_nfs nf
      ON NULLIF(ltrim(regexp_replace(pi.numero_nf, '\D', '', 'g'), '0'), '')
       = NULLIF(ltrim(regexp_replace(nf.numero_nf, '\D', '', 'g'), '0'), '')
    WHERE pi.numero_nf IS NOT NULL AND pi.numero_nf <> ''
      AND nf.local_cd <> 'VICTORIO_MARCHEZINE'
) sub
WHERE ped.id = sub.pedido_id
  AND ped.local_cd = 'VICTORIO_MARCHEZINE';

UPDATE carvia_cotacoes cot
SET local_cd = 'TENENTE_MARQUES'
WHERE cot.local_cd = 'VICTORIO_MARCHEZINE'
  AND EXISTS (
      SELECT 1 FROM carvia_pedidos ped
      WHERE ped.cotacao_id = cot.id AND ped.local_cd = 'TENENTE_MARQUES'
  );
