-- Motos Assai — Data fix 17 (2026-05-12): deletar AssaiSeparacao 2 orfa
-- Idempotente. Equivalente SQL do script Python homonimo (rodar UM dos dois).
--
-- Sep 2 foi criada AUTOMATICAMENTE pela rota /pedidos/<pid>/separar/<lid>
-- quando o operador navegava sem `?sep_id`. Bug corrigido em
-- separacao_service.get_separacao_ativa (substitui get_ou_criar_separacao).
--
-- Pre-validacao: rodar antes para verificar que esta seguro
-- (todas as contagens devem ser zero):
--
--   SELECT
--     (SELECT COUNT(*) FROM assai_separacao_item WHERE separacao_id = 2)         AS items,
--     (SELECT COUNT(*) FROM assai_separacao_saldo_modelo WHERE separacao_id = 2) AS saldos,
--     (SELECT COUNT(*) FROM assai_nf_qpa WHERE separacao_id = 2)                 AS nfs_apontando,
--     (SELECT COUNT(*) FROM separacao WHERE separacao_lote_id = 'ASSAI-SEP-2')   AS linhas_nacom;
--
-- Se algum > 0: NAO RODAR este DELETE. Investigar manualmente.

DO $$
DECLARE
    items_n INT;
    saldos_n INT;
    nfs_n INT;
    nacom_n INT;
    sep_status VARCHAR;
BEGIN
    -- Confirmar que sep ainda existe e esta EM_SEPARACAO (estado fantasma)
    SELECT status INTO sep_status FROM assai_separacao WHERE id = 2;
    IF sep_status IS NULL THEN
        RAISE NOTICE 'skip: AssaiSeparacao 2 ja nao existe — idempotente OK';
        RETURN;
    END IF;
    IF sep_status <> 'EM_SEPARACAO' THEN
        RAISE NOTICE 'abort: AssaiSeparacao 2 esta % — esperado EM_SEPARACAO', sep_status;
        RETURN;
    END IF;

    -- Validar que esta vazia
    SELECT COUNT(*) INTO items_n FROM assai_separacao_item WHERE separacao_id = 2;
    SELECT COUNT(*) INTO saldos_n FROM assai_separacao_saldo_modelo WHERE separacao_id = 2;
    SELECT COUNT(*) INTO nfs_n FROM assai_nf_qpa WHERE separacao_id = 2;
    SELECT COUNT(*) INTO nacom_n FROM separacao WHERE separacao_lote_id = 'ASSAI-SEP-2';

    IF items_n > 0 OR saldos_n > 0 OR nfs_n > 0 OR nacom_n > 0 THEN
        RAISE NOTICE
            'abort: AssaiSeparacao 2 tem dependencias — items=% saldos=% nfs=% nacom=%',
            items_n, saldos_n, nfs_n, nacom_n;
        RETURN;
    END IF;

    DELETE FROM assai_separacao WHERE id = 2;
    RAISE NOTICE 'ok: AssaiSeparacao 2 deletada com sucesso';
END $$;
