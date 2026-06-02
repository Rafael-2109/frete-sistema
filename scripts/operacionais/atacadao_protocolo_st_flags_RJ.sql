-- ============================================================================
-- Flags de Protocolo ST — Atacadão RJ  (rodar no Render Shell / psql PROD)
-- ============================================================================
-- Fonte: Excel depara_atacadao_20260410 (grupo "COM PROTOCOLO") + 5 azeitonas
-- BULNEZ (varejo) classificadas por padrão. Cogumelos BULNEZ = SEM (cogumelo
-- nunca é ST no mapeamento do Excel).
--
-- O que faz:
--   1) protocolo_st = TRUE nos 35 produtos COM PROTOCOLO (De-Para Atacadão)
--   2) separar_protocolo_st = TRUE para ATACADAO/RJ (liga o split por UF)
-- Idempotente. Os demais produtos permanecem FALSE (default).
-- ============================================================================

BEGIN;

-- (1) Produtos COM PROTOCOLO ST  (30 do Excel + 5 azeitonas BULNEZ varejo)
UPDATE portal_atacadao_produto_depara
SET protocolo_st = TRUE
WHERE codigo_nosso IN (
    -- 30 do Excel "COM PROTOCOLO"
    '4729098','4080178','4080177','4159301','4070176','4060171','4220179','4210176','4329301','4320154',
    '4320147','4310146','4320172','4320177','4310152','4310145','4310141','4310177','43109068','4350150',
    '4369301','4360155','4360147','4310148','4360172','4360177','4050176','4141178','4142178','4143178',
    -- 5 azeitonas BULNEZ (varejo) — SACHE/VD/POUCH
    '4219901','4319901','4319902','4329901','4369901'
);

-- (2) Liga a separação por UF para Atacadão/RJ
UPDATE regiao_tabela_rede
SET separar_protocolo_st = TRUE
WHERE rede = 'ATACADAO' AND uf = 'RJ';

COMMIT;

-- ============================================================================
-- VERIFICAÇÃO (rodar após o COMMIT)
-- ============================================================================
-- Quantos produtos COM PROTOCOLO marcados (esperado: linhas dos 35 códigos):
--   SELECT count(*) FILTER (WHERE protocolo_st) AS com_st,
--          count(*) FILTER (WHERE NOT protocolo_st) AS sem_st
--   FROM portal_atacadao_produto_depara WHERE ativo;
-- RJ ligado?
--   SELECT rede, uf, separar_protocolo_st FROM regiao_tabela_rede
--   WHERE rede='ATACADAO' AND uf='RJ';
