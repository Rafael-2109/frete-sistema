-- ============================================================================
-- INVERTER protocolo_st — Atacadão (rodar no Render Shell / psql PROD)
-- ============================================================================
-- Motivo: o agrupamento COM/SEM do Excel (validado pelo fiscal) ficou com o flag
-- protocolo_st trocado. Aqui invertemos TODOS: o que está Sim vira Não e vice-versa.
-- A separação no split é a mesma (binária) — só corrige qual grupo é o "protocolo".
-- NÃO mexe em separar_protocolo_st (ATACADAO/RJ continua TRUE).
-- ============================================================================

BEGIN;

UPDATE portal_atacadao_produto_depara
SET protocolo_st = NOT protocolo_st;

COMMIT;

-- VERIFICAÇÃO (rodar após o COMMIT) — antes: 35 Sim; depois: o complemento vira Sim
--   SELECT count(*) FILTER (WHERE protocolo_st)     AS agora_sim,
--          count(*) FILTER (WHERE NOT protocolo_st) AS agora_nao
--   FROM portal_atacadao_produto_depara WHERE ativo;
