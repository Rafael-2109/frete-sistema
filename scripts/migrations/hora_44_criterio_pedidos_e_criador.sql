-- Migration HORA 44: criterio de listagem de pedidos por usuario + criador do pedido.
-- Idempotente (IF NOT EXISTS). Rodar no Render Shell.

-- 1) Preferencia de criterio de filtragem de pedidos de venda por usuario.
--    'loja' (default, comportamento atual) | 'vendedor' (pedidos do proprio usuario).
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja';

-- 2) Usuario criador do pedido de venda (robustez para o filtro 'vendedor').
--    Sem FK (padrao do modulo HORA: nao acopla a usuarios).
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS criado_por_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_hora_venda_criado_por_id
    ON hora_venda (criado_por_id);

-- 3) Backfill best-effort do criador via auditoria (acao='CRIOU' casando nome).
--    Deterministico: agrega por venda e usa MIN(u.id) — evita resultado
--    arbitrario quando ha usuarios homonimos (usuarios.nome nao e UNIQUE).
UPDATE hora_venda v
   SET criado_por_id = sub.user_id
  FROM (
      SELECT a.venda_id, MIN(u.id) AS user_id
        FROM hora_venda_auditoria a
        JOIN usuarios u ON u.nome = a.usuario
       WHERE a.acao = 'CRIOU'
       GROUP BY a.venda_id
  ) sub
 WHERE sub.venda_id = v.id
   AND v.criado_por_id IS NULL;
