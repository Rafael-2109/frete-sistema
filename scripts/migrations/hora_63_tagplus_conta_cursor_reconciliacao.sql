-- Idempotente. Adiciona ultimo_pedido_numero_reconciliado (INTEGER, NULL) a
-- hora_tagplus_conta. Cursor do numero-walk +3 (Fase 3 da sync HORA<->TagPlus):
-- maior numero de pedido ja varrido na descoberta reversa. Persistido para o
-- scheduler retomar de onde parou. Sem indice (conta e singleton, 1 linha).
-- Migration HORA 63 (2026-06-29).
ALTER TABLE hora_tagplus_conta
    ADD COLUMN IF NOT EXISTS ultimo_pedido_numero_reconciliado INTEGER;
