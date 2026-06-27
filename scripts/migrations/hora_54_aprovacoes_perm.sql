-- Idempotente. Separa a permissao de APROVAR pedido (#28 Fatia 2 + #5b) do
-- modulo legado 'comissao' (que ficou so com config + relatorio) para o novo
-- modulo 'aprovacoes'. Sem DDL — hora_user_permissao.modulo ja e VARCHAR(40).
-- Backfill: quem tinha comissao/aprovar passa a ter aprovacoes (ver + aprovar),
-- preservando o acesso dos gerentes atuais. Migration HORA 54 (2026-06-26).
INSERT INTO hora_user_permissao
    (user_id, modulo, pode_ver, pode_criar, pode_editar, pode_apagar, pode_aprovar, atualizado_em)
SELECT user_id, 'aprovacoes', TRUE, FALSE, FALSE, FALSE, TRUE,
       (NOW() AT TIME ZONE 'America/Sao_Paulo')
FROM hora_user_permissao
WHERE modulo = 'comissao' AND pode_aprovar = TRUE
ON CONFLICT (user_id, modulo) DO UPDATE
    SET pode_ver = TRUE, pode_aprovar = TRUE,
        atualizado_em = (NOW() AT TIME ZONE 'America/Sao_Paulo');
