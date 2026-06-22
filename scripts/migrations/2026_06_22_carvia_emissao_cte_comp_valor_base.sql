-- Migration: coluna `valor_base` em carvia_emissao_cte_complementar + backfill.
-- Data: 2026-06-22
-- Descricao:
--   O tracking de emissao SSW 222 so persistia `valor_calculado` (valor JA com
--   grossing-up PIS/COFINS + ICMS). O worker, porem, precisa do valor_base LIQUIDO
--   (= valor do CustoEntrega OU valor a cobrar) para o SSW 222 refazer o grossing-up
--   ao vivo com o ICMS atual do CTe pai. Ate aqui o worker lia esse liquido de
--   `emissao.custo_entrega.valor`, o que QUEBRAVA (AttributeError em None) no CTe
--   complementar AVULSO (TDE/Diaria — repasse puro, sem CustoEntrega de contrapartida).
--   Esta migration:
--     1) adiciona a coluna `valor_base` (idempotente);
--     2) backfilla o liquido das emissoes JA vinculadas a um CE (e.custo_entrega_id),
--        a partir de carvia_custos_entrega.valor (so onde ainda esta NULL).
--   Emissoes avulsas legadas (sem CE) ficam NULL — o worker mantem fallback para o CE
--   quando existir; sem nenhum dos dois, marca ERRO em vez de crashar.
-- Idempotente (ADD COLUMN IF NOT EXISTS + UPDATE condicional).
ALTER TABLE carvia_emissao_cte_complementar
    ADD COLUMN IF NOT EXISTS valor_base NUMERIC(15, 2);

-- Backfill do liquido a partir do CustoEntrega vinculado (so onde ainda nao tem).
UPDATE carvia_emissao_cte_complementar e
   SET valor_base = c.valor
  FROM carvia_custos_entrega c
 WHERE e.custo_entrega_id = c.id
   AND e.valor_base IS NULL
   AND c.valor IS NOT NULL;
