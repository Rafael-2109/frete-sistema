-- GAP-01: Converter status EMITIDA → PENDENTE em carvia_faturas_cliente
-- Idempotente: roda quantas vezes quiser sem efeito colateral

UPDATE carvia_faturas_cliente
SET status = 'PENDENTE'
WHERE status = 'EMITIDA';
