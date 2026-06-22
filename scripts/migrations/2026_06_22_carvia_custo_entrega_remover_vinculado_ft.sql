-- Migration de DADOS: colapsa o status VINCULADO_FT em PENDENTE
-- (carvia_custos_entrega). O vinculo a uma Fatura Transportadora passa a ser
-- indicado EXCLUSIVAMENTE pela FK fatura_transportadora_id (CE PENDENTE com FK
-- = sera pago junto da FT). Idempotente.
--
-- Producao 2026-06-22: 6 registros VINCULADO_FT (todos com FK FT).
UPDATE carvia_custos_entrega
SET status = 'PENDENTE'
WHERE status = 'VINCULADO_FT';
