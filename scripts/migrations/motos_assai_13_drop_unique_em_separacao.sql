-- Motos Assaí — Migration 13: drop UNIQUE em_separacao para permitir N veículos
-- Idempotente.
--
-- Reverte indice criado erroneamente na migration 12. Regra de negócio
-- (2026-05-12): separações representam veículos de carregamento. 2+ veículos
-- podem carregar paralelamente do mesmo (pedido, loja) — ao finalizar uma, o
-- saldo migra para outra ativa.
--
-- Concorrência de chassi continua protegida via:
--   1. with_for_update em AssaiMoto (lock pessimista por chassi)
--   2. Validação de status_atual(chassi) == DISPONIVEL antes de SEPARADA
-- — mesmo chassi não pode estar em 2 separações ativas.

DROP INDEX IF EXISTS ux_assai_separacao_pedido_loja_em_separacao;
