-- Migration HORA 31: Remove motos cadastradas erroneamente como pecas.
--
-- Causa-raiz: backfill_service.executar_backfill_produtos_pecas pulava motos via
-- ncm.startswith('8711'). Como TagPlus retorna NCM vazio em todos os produtos,
-- a heuristica nunca disparou e modelos de moto entraram como peca.
--
-- Limpeza pontual em producao (2026-05-06): IDs 6 e 207.
--
--   peca_id=6   MT-MC20             "Ciclomotor MC20 3000W"
--   peca_id=207 MT-X12 10 - 18X     "Scooter Eletrica X12-10 1000w"
--
-- Ambos sem uso (zero pedidos, vendas, NF de entrada, movimentos).
--
-- Demais 17 IDs reportados pelo agente original (3, 4, 7, 8, 9, 195, 196..206,
-- 208..213) ja foram removidos manualmente em sessao anterior.
--
-- Idempotente: DELETE WHERE id IN (...) -- segunda execucao nao faz nada.

BEGIN;

-- 1) Remover mapeamento TagPlus -> peca primeiro (FK)
DELETE FROM hora_tagplus_peca_map
 WHERE peca_id IN (6, 207);

-- 2) Remover registros de peca
DELETE FROM hora_peca
 WHERE id IN (6, 207);

COMMIT;
