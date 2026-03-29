-- =============================================================================
-- BACKFILL: Propagar data_embarque de embarques para separacao
--
-- Problema: separacoes vinculadas a embarques ativos (com data_embarque)
--           mas que nao receberam a propagacao de data_embarque.
--           Isso faz com que aparecam como "Pend. de Embarque" na lista de pedidos.
--
-- Criterio: separacao.nf_cd = false
--           AND separacao.data_embarque IS NULL
--           AND embarque ativo com data_embarque preenchida
--           AND item do embarque ativo
-- =============================================================================

-- 1) DIAGNOSTICO: Ver quantos registros serao afetados
SELECT
    s.separacao_lote_id,
    s.num_pedido,
    s.raz_social_red,
    s.status         AS sep_status,
    s.nf_cd,
    s.data_embarque  AS sep_data_embarque,
    e.id             AS embarque_id,
    e.numero         AS embarque_numero,
    e.data_embarque  AS emb_data_embarque,
    e.status         AS emb_status,
    ei.status        AS item_status
FROM separacao s
JOIN embarque_itens ei ON ei.separacao_lote_id = s.separacao_lote_id
JOIN embarques e ON e.id = ei.embarque_id
WHERE s.nf_cd = false
  AND s.data_embarque IS NULL
  AND e.data_embarque IS NOT NULL
  AND e.status != 'cancelado'
  AND ei.status = 'ativo'
ORDER BY e.data_embarque DESC, s.separacao_lote_id;

-- 2) BACKFILL: Propagar data_embarque
-- Usa subquery com DISTINCT ON para evitar duplicidade
-- (caso raro de mesmo lote em 2+ embarques ativos — pega o mais recente)
UPDATE separacao s
SET data_embarque = sub.emb_data_embarque
FROM (
    SELECT DISTINCT ON (ei.separacao_lote_id)
        ei.separacao_lote_id,
        e.data_embarque AS emb_data_embarque
    FROM embarque_itens ei
    JOIN embarques e ON e.id = ei.embarque_id
    WHERE e.data_embarque IS NOT NULL
      AND e.status != 'cancelado'
      AND ei.status = 'ativo'
    ORDER BY ei.separacao_lote_id, e.data_embarque DESC
) sub
WHERE sub.separacao_lote_id = s.separacao_lote_id
  AND s.nf_cd = false
  AND s.data_embarque IS NULL;

-- 3) VERIFICACAO: Confirmar que nao restam orfaos
SELECT COUNT(*) AS restantes_sem_data_embarque
FROM separacao s
JOIN embarque_itens ei ON ei.separacao_lote_id = s.separacao_lote_id
JOIN embarques e ON e.id = ei.embarque_id
WHERE s.nf_cd = false
  AND s.data_embarque IS NULL
  AND e.data_embarque IS NOT NULL
  AND e.status != 'cancelado'
  AND ei.status = 'ativo';
-- Esperado: 0
