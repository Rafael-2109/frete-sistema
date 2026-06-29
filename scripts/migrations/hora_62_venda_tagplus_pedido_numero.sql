-- Idempotente. Adiciona tagplus_pedido_numero (INTEGER, NULL) a hora_venda.
-- Numero VISIVEL do pedido no TagPlus (pedido['numero'] / pedido_os_vinculada.numero),
-- distinto do tagplus_pedido_id (ID interno). Resolve a inconsistencia de exibir
-- o ID como se fosse o numero. Migration HORA 62 (2026-06-29).
ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS tagplus_pedido_numero INTEGER;
CREATE INDEX IF NOT EXISTS ix_hora_venda_tagplus_pedido_numero
    ON hora_venda (tagplus_pedido_numero);
