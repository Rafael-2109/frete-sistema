-- Migration de DADOS: numero_custo de 'CE-###' para numero direto ('###' sem
-- zeros a esquerda) em carvia_custos_entrega. Idempotente: so converte valores
-- 'CE-%' cujo resultado seja puramente numerico (evita tocar valores atipicos).
UPDATE carvia_custos_entrega
SET numero_custo = regexp_replace(numero_custo, '^CE-0*', '')
WHERE numero_custo LIKE 'CE-%'
  AND regexp_replace(numero_custo, '^CE-0*', '') ~ '^[0-9]+$';
