-- ============================================================================
-- Data fix: substituicao de chassis errados nas NFs de saida da Lojas HORA
--
-- Origem: planilha "alteração sistema.xlsx" (78 pares fornecidos por Rafael).
-- Cada linha eh (nf_saida_numero, chassi_antigo, chassi_novo).
--
-- O que faz, por par:
--   1. Localiza a venda pelo nf_saida_numero (ESCOPO da substituicao).
--   2. Garante que existe hora_moto com PK = chassi_novo (clona da antiga
--      ou cria stub com modelo/cor da antiga ou defaults).
--   3. Atualiza referencias do chassi_antigo APENAS no escopo da venda:
--        - hora_venda_item.numero_chassi
--        - hora_venda_divergencia.numero_chassi
--        - hora_moto_evento (eventos cuja origem aponta para a venda/itens)
--      As FKs sao NO ACTION — UPDATE direto em hora_moto.numero_chassi
--      explodiria, por isso re-apontamos os filhos primeiro.
--   4. (Cleanup final) deleta hora_moto antiga apenas se ficou orfa em
--      TODAS as 11 tabelas filhas. Caso contrario fica preservada.
--
-- Idempotente: re-rodar nao causa dano. Itens ja com chassi_novo nao sao
-- afetados (UPDATE filtra por chassi_antigo).
--
-- Aplicar via Render Shell:
--   psql $DATABASE_URL -f scripts/migrations/hora_data_chassi_substituicao_2026_04_30.sql
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Tabela temporaria com os 78 pares.
-- ----------------------------------------------------------------------------
CREATE TEMP TABLE substituicoes_chassi (
    nf_numero VARCHAR(20) NOT NULL,
    chassi_antigo VARCHAR(30) NOT NULL,
    chassi_novo VARCHAR(30) NOT NULL
) ON COMMIT DROP;

INSERT INTO substituicoes_chassi (nf_numero, chassi_antigo, chassi_novo) VALUES
    ('1', 'WT60V40H3000W2409280024', '92WMCX113SM000279'),
    ('3', 'AUTOPROPELIDO', '172922505660039'),
    ('4', 'AUTOPROPELIDO', '172922506890403'),
    ('7', 'S', '92WMCX113SM000304'),
    ('14', 'MCBRX122507310081I', 'MCBRX122507310081'),
    ('18', 'AUTOPROPELIDO', '172922506890533'),
    ('23', 'AUTOPROPELIDO', '172922506890248'),
    ('31', 'QS60V30H25070502033', 'LA250960V1000W7130'),
    ('36', '92WMCX1132M000447', '92WMCX113SM000447'),
    ('40', 'QS60V30H250504', 'LA250960V1000W7189'),
    ('44', 'IHL5TCAH35S9W60299', 'HL5TCAH35S9W60299'),
    ('45', '172922502660076', '172922505660076'),
    ('49', 'AUTOPROPELIDO', '172922505660136'),
    ('66', 'AUTOPROPELIDO', '172922505661992'),
    ('72', 'MCDRX122508080113', 'MCBRX122508080113'),
    ('73', 'AUTOPROPELIDO', 'MCBRSOMA251024203'),
    ('74', 'L5TCAH39S9W66414', 'HL5TCAH39S9W66414'),
    ('87', 'AUTOPROPELIDO', 'MCBRSOMA251023135'),
    ('91', 'HL5TCAH3XS9W6860', 'HL5TCAH3XS9W68608'),
    ('95', 'MCBRX12507090031', 'MCBRX122507090031'),
    ('102', 'LYDAE393951200007', 'LYDAE3937S1200007'),
    ('105', '92WMCX11SM000274', '92WMCX113SM000274'),
    ('115', 'MCBRX22508080132', 'MCBRX122508080132'),
    ('117', 'MCBREJT2509230207', 'MCBRJET2509230207'),
    ('122', 'AUTOPROPELIDO', '172922505662083'),
    ('129', 'AUTOPROPELIDO', '172922505661924'),
    ('130', 'AUTOPROPELIDO', '172922505661977'),
    ('143', '172922505662085', 'MCBRSOMA251024020'),
    ('145', 'HL5CAH38S9W63374', 'HL5TCAH38S9W63374'),
    ('151', 'AUTOPROPELIDO', 'XL2025060450'),
    ('167', 'LA250960V1000W4947', 'LA250960V1000W4919'),
    ('173', 'MCBRJET2509230221COR', 'MCBRJET2509230221'),
    ('180', 'MCBRX12251100103', 'MCBRX122511100103'),
    ('182', '72922505662037', '172922505662037'),
    ('189', 'MCBRJET2509230085', 'MCBRJET2509230065'),
    ('199', '172922505661928', 'MCBRSOMA251025067'),
    ('225', 'CBRX122507090096', 'MCBRX122507090096'),
    ('230', '172922503482266', '172922503483266'),
    ('236', 'MCBRX122511100110', 'MCBRX122511130110'),
    ('254', 'LA250960V1000VV6283', 'LA250960V1000W6283'),
    ('257', 'MCBRX122511120249', 'MCBRX122602130146'),
    ('268', 'LX24060103', 'QH48V750W2024050819'),
    ('274', 'MCBRX122511120225COR', 'MCBRX122511120225'),
    ('275', 'MCBRX1225507090080', 'MCBRX122507090080'),
    ('280', 'MCBRX1225007080139', 'MCBRX122507080139'),
    ('284', 'LA259601000W9539', 'LA250960V1000W9539'),
    ('288', 'MCBRJET2509260074', 'MCBRJET2509250074'),
    ('317', '172922505661645', 'MCBRSOMA251024131'),
    ('320', 'AUTOPROPELIDO', 'MCBRSOMA251023123'),
    ('326', 'MCBRX122511210126', 'MCBRX122602120396'),
    ('352', 'HL5TCAH32S9W68621COR', 'HL5TCAH32S9W68621'),
    ('375', 'MCBRX122511210126OR', 'MCBRX122511210126'),
    ('379', 'AUTOPROPELIDO', 'XL2025060548'),
    ('385', '172922505661833', 'MCBRSOMA251023097'),
    ('398', 'LYDAE3933S1200732COR', 'LYDAE3933S1200732'),
    ('429', '172922505661669', 'MCBRSOMA251024163'),
    ('477', 'SXKJ22506120514', 'SXRJ22506120514'),
    ('479', '172922505661859', 'MCBRSOMA251024187'),
    ('485', '172922505661811', 'MCBRSOMA251023229'),
    ('510', 'HL5TCAH32S9W65234', 'HL5TCAH32S9W62530'),
    ('518', '172922505660484', 'MCBRSOMA251022022'),
    ('522', '172922505663152', 'MCBRSOMA251025072'),
    ('540', '172922505662889', 'MCBRSOMA251024042'),
    ('543', '172922505662894', 'MCBRSOMA251024047'),
    ('552', '172922505661650', 'MCBRSOMA251023168'),
    ('590', '172922511891443', 'MC172922511891443'),
    ('601', 'FSB202403057', '63824363000161'),
    ('632', '172922505661812', 'MCBRSOMA251023249'),
    ('649', '172922505660637', 'MCBRSOMA251022038'),
    ('656', 'LYDAE3937T1204297COR', 'LYDAE3937T1204297'),
    ('661', 'LYDAE3931T120332', 'LYDAE3931T1203324'),
    ('663', '172922505660703', 'MCBRSOMA251022044'),
    ('686', 'LYDAE3931T1203307COR', 'LYDAE3931T1203307'),
    ('697', 'LYDAE3938T120416', 'LYDAE3938T1204163'),
    ('699', 'MCBRX122682120280', 'MCBRX122602120280'),
    ('707', '172922511890471', 'MC172922511890471'),
    ('713', 'LA2025SA110004002', 'LA2026SA010004002'),
    ('714', '19292251089051', '192922510890511');

-- Indice auxiliar para os JOINs durante a execucao do DO block.
CREATE INDEX ON substituicoes_chassi (nf_numero);

-- ----------------------------------------------------------------------------
-- 2. Bloco principal: para cada par, executa a substituicao escopada na NF.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    rec        RECORD;
    v_venda_id INTEGER;
    v_loja_id  INTEGER;
    v_item_ids INTEGER[];
    v_modelo_id INTEGER;
    v_cor      VARCHAR(50);
    v_ano      INTEGER;
    v_existe_antiga BOOLEAN;
    v_atualizou_items INTEGER;
    n_total    INTEGER := 0;
    n_pulado   INTEGER := 0;
    n_aplicado INTEGER := 0;
    n_inalterado INTEGER := 0;
BEGIN
    FOR rec IN SELECT * FROM substituicoes_chassi LOOP
        n_total := n_total + 1;

        -- 2.1 Localiza venda pela nf_saida_numero. Pode haver mais de 1 (raro);
        -- pegamos a mais recente FATURADO por seguranca.
        SELECT v.id, v.loja_id INTO v_venda_id, v_loja_id
        FROM hora_venda v
        WHERE v.nf_saida_numero = rec.nf_numero
        ORDER BY v.id DESC
        LIMIT 1;

        IF v_venda_id IS NULL THEN
            RAISE NOTICE 'Pulando NF %: venda nao encontrada (chassi % -> %)',
                rec.nf_numero, rec.chassi_antigo, rec.chassi_novo;
            n_pulado := n_pulado + 1;
            CONTINUE;
        END IF;

        -- 2.2 Garante hora_moto destino. Clona da antiga se existir; senao
        -- cria stub minimo (modelo qualquer + cor INDEFINIDA).
        SELECT TRUE, modelo_id, cor, ano_modelo
        INTO v_existe_antiga, v_modelo_id, v_cor, v_ano
        FROM hora_moto
        WHERE numero_chassi = rec.chassi_antigo;

        IF NOT FOUND THEN
            v_existe_antiga := FALSE;
            -- Stub: usa primeiro modelo cadastrado e cor INDEFINIDA.
            SELECT id INTO v_modelo_id FROM hora_modelo ORDER BY id LIMIT 1;
            v_cor := 'INDEFINIDA';
            v_ano := NULL;
        END IF;

        IF v_modelo_id IS NULL THEN
            RAISE NOTICE 'Pulando NF %: nenhum hora_modelo cadastrado — '
                         'nao da pra criar stub do chassi %',
                rec.nf_numero, rec.chassi_novo;
            n_pulado := n_pulado + 1;
            CONTINUE;
        END IF;

        INSERT INTO hora_moto (numero_chassi, modelo_id, cor, ano_modelo, criado_em)
        VALUES (rec.chassi_novo, v_modelo_id, v_cor, v_ano,
                (NOW() AT TIME ZONE 'UTC'))
        ON CONFLICT (numero_chassi) DO NOTHING;

        -- 2.3 Captura ids dos hora_venda_item afetados (para escopar
        -- atualizacao de hora_moto_evento por origem_id).
        SELECT array_agg(id) INTO v_item_ids
        FROM hora_venda_item
        WHERE venda_id = v_venda_id
          AND numero_chassi = rec.chassi_antigo;

        -- 2.4 Atualiza hora_venda_item da venda.
        UPDATE hora_venda_item
        SET numero_chassi = rec.chassi_novo
        WHERE venda_id = v_venda_id
          AND numero_chassi = rec.chassi_antigo;
        GET DIAGNOSTICS v_atualizou_items = ROW_COUNT;

        -- 2.5 Atualiza hora_venda_divergencia da venda.
        UPDATE hora_venda_divergencia
        SET numero_chassi = rec.chassi_novo
        WHERE venda_id = v_venda_id
          AND numero_chassi = rec.chassi_antigo;

        -- 2.6 Atualiza hora_moto_evento ESCOPADO:
        --   (a) eventos com origem_tabela='hora_venda_item' apontando para
        --       os item_ids capturados;
        --   (b) eventos relacionados a venda diretamente (NF_EMITIDA,
        --       NF_CANCELADA, RESERVADA, VENDIDA, DEVOLVIDA).
        IF v_item_ids IS NOT NULL AND array_length(v_item_ids, 1) > 0 THEN
            UPDATE hora_moto_evento
            SET numero_chassi = rec.chassi_novo
            WHERE numero_chassi = rec.chassi_antigo
              AND origem_tabela = 'hora_venda_item'
              AND origem_id = ANY(v_item_ids);
        END IF;

        UPDATE hora_moto_evento
        SET numero_chassi = rec.chassi_novo
        WHERE numero_chassi = rec.chassi_antigo
          AND origem_tabela IN (
              'hora_venda', 'hora_tagplus_nfe_emissao',
              'hora_venda_divergencia'
          )
          AND origem_id = v_venda_id;

        IF v_atualizou_items = 0 THEN
            -- Pode acontecer se ja foi rodado antes. Apenas garante que a
            -- moto destino existe (ja garantimos acima).
            n_inalterado := n_inalterado + 1;
            RAISE NOTICE 'NF %: 0 items afetados (chassi % ja era %?)',
                rec.nf_numero, rec.chassi_antigo, rec.chassi_novo;
        ELSE
            n_aplicado := n_aplicado + 1;
            RAISE NOTICE 'NF %: % item(s) atualizado(s) (% -> %, venda_id=%)',
                rec.nf_numero, v_atualizou_items,
                rec.chassi_antigo, rec.chassi_novo, v_venda_id;
        END IF;
    END LOOP;

    RAISE NOTICE '=== Resumo: total=% aplicado=% inalterado=% pulado=% ===',
        n_total, n_aplicado, n_inalterado, n_pulado;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Cleanup: remove hora_moto antigas que ficaram orfas.
--    Verifica TODAS as 11 tabelas filhas. Se ainda ha referencia, preserva.
-- ----------------------------------------------------------------------------
WITH antigos AS (
    SELECT DISTINCT chassi_antigo AS chassi
    FROM substituicoes_chassi
)
DELETE FROM hora_moto m
USING antigos a
WHERE m.numero_chassi = a.chassi
  AND NOT EXISTS (SELECT 1 FROM hora_moto_evento WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_venda_item WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_venda_divergencia WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_nf_entrada_item WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_pedido_item WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_recebimento_conferencia WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_avaria WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_devolucao_fornecedor_item WHERE numero_chassi = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_peca_faltando
                   WHERE numero_chassi = m.numero_chassi OR chassi_doador = m.numero_chassi)
  AND NOT EXISTS (SELECT 1 FROM hora_transferencia_item WHERE numero_chassi = m.numero_chassi);

-- ----------------------------------------------------------------------------
-- 4. Auditoria: lista chassis antigos que ficaram preservados (ainda
--    referenciados por OUTRO contexto). Apenas informativo — nao falha.
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN
        SELECT s.chassi_antigo
        FROM substituicoes_chassi s
        WHERE EXISTS (SELECT 1 FROM hora_moto WHERE numero_chassi = s.chassi_antigo)
        GROUP BY s.chassi_antigo
    LOOP
        RAISE NOTICE 'Chassi antigo preservado (ainda referenciado): %',
            rec.chassi_antigo;
    END LOOP;
END $$;

COMMIT;
