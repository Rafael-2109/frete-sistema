-- Migration: Converter colunas datetime de UTC para Brasil (UTC-3)
-- ================================================================
--
-- CONTEXTO:
--   O sistema armazenava timestamps via agora_utc_naive() em UTC.
--   Este script ajusta TODOS os registros existentes subtraindo 3 horas.
--
-- EXECUÇÃO (Render Shell):
--   psql $DATABASE_URL -f scripts/migrations/migrar_timezone_utc_para_brasil.sql
--
-- IDEMPOTÊNCIA:
--   Usa tabela _migration_log para verificar se já foi executada.
--   Seguro para executar múltiplas vezes.

-- Criar tabela de controle se não existir
CREATE TABLE IF NOT EXISTS _migration_log (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(200) NOT NULL UNIQUE,
    executado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detalhes TEXT
);

-- Verificar se já foi executada
DO $$
DECLARE
    v_already_run BOOLEAN;
    v_total_rows BIGINT := 0;
    v_count BIGINT;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM _migration_log
        WHERE migration_name = 'migrar_timezone_utc_para_brasil_v1'
    ) INTO v_already_run;

    IF v_already_run THEN
        RAISE NOTICE 'Migration já executada. Use DELETE FROM _migration_log WHERE migration_name = ''migrar_timezone_utc_para_brasil_v1'' para re-executar.';
        RETURN;
    END IF;

    RAISE NOTICE 'Iniciando migration UTC -> Brasil (UTC-3)...';

    -- ============================================================
    -- TABELAS COM criado_em
    -- ============================================================
    UPDATE agendamentos_entrega SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE alerta_notificacoes SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE anexo_ocorrencia SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE arquivo_entrega SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE baixa_pagamento_item SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE baixa_pagamento_lote SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE baixa_titulo_item SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE baixa_titulo_lote SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cadastro_cliente SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cadastro_primeira_compra SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cnab_retorno_item SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cnab_retorno_lote SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE comentarios_nf SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE conta_corrente_transportadoras SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contagem_devolucao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_pagar SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber_abatimento SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber_reconciliacao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber_tipos SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE controle_cruzado_separacao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE controle_portaria SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE custo_frete SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE custo_mensal SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE custos_extra_entrega SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE depara_produto_cliente SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE descarte_devolucao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE descarte_item SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE despesas_extras SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE divergencia_fiscal SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE divergencia_nf_po SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE embarques SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE entregas_monitoradas SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE entregas_rastreadas SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE equipe_vendas SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE eventos_entrega SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE extrato_item SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE extrato_item_titulo SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE extrato_lote SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE faturamento_parcial_justificativa SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE faturas_frete SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE fila_agendamento_sendas SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE frete_devolucao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE fretes SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE grupo_empresarial SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE historico_tabelas_frete SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE lancamento_comprovante SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE liberacao_antecipacao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE lista_materiais SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE logs_rastreamento SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE mapeamento_tipo_odoo SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE match_nf_po_alocacao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE match_nf_po_item SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE motoristas SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE movimentacao_estoque SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE ncm_ibscbs_validado SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE nf_devolucao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE nf_devolucao_linha SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE nf_devolucao_nf_referenciada SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE nf_pendente_tagplus SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE ocorrencia_devolucao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pedido_compras SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pedido_importacao_temp SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pedidos SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pendencia_fiscal_ibscbs SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pendencias_financeiras_nf SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE perfil_fiscal_produto_fornecedor SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE perfil_usuario SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE permissao_comercial SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pings_gps SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE plano_mestre_producao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_atacadao_produto_depara SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_configuracoes SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_integracoes SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_logs SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sendas_filial_depara SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sendas_produto_depara SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sessoes SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_tenda_agendamentos SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_tenda_local_entrega_depara SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_tenda_produto_depara_ean SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE previsao_demanda SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE produto_fornecedor_depara SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE rastreamento_embarques SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE recebimento_fisico SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE recebimento_lf SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE recursos_producao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE regiao_tabela_rede SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE registro_pedido_odoo SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE regra_comissao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE relatorio_faturamento_importado SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE requisicao_compra_alocacao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE requisicao_compras SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE saldo_standby SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE separacao SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE tabela_rede_precos SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE tabelas_frete SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE tagplus_oauth_token SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE tipo_carga SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE usuarios SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE validacao_fiscal_dfe SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE validacao_nf_po_dfe SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE vendedor SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE webhook_configs SET criado_em = criado_em - INTERVAL '3 hours' WHERE criado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- ============================================================
    -- TABELAS COM atualizado_em
    -- ============================================================
    UPDATE cadastro_cliente SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE configuracao_rastreamento SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE conhecimento_transporte SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contagem_devolucao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_pagar SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber_abatimento SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contatos_agendamento SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE controle_portaria SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE custo_mensal SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE depara_produto_cliente SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE descarte_devolucao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE descarte_item SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE frete_devolucao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE custo_considerado SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE lead_time_fornecedor SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE liberacao_antecipacao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE lista_materiais SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE motoristas SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE movimentacao_estoque SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE ncm_ibscbs_validado SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE nf_devolucao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE nf_devolucao_linha SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE ocorrencia_devolucao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE parametro_custeio SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pedido_compras SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pedido_importacao_temp SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE perfil_fiscal_produto_fornecedor SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_atacadao_produto_depara SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_configuracoes SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_integracoes SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sendas_filial_depara SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sendas_produto_depara SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sessoes SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_tenda_agendamentos SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_tenda_local_entrega_depara SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_tenda_produto_depara_ean SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE previsao_demanda SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE produto_fornecedor_depara SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE recebimento_lf SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE regra_comissao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE requisicao_compra_alocacao SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE tabela_rede_precos SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE tagplus_oauth_token SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE validacao_fiscal_dfe SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE validacao_nf_po_dfe SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE webhook_configs SET atualizado_em = atualizado_em - INTERVAL '3 hours' WHERE atualizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- ============================================================
    -- TABELAS COM created_at / updated_at
    -- ============================================================
    UPDATE agent_memories SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE agent_memories SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE agent_sessions SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE agent_sessions SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cadastro_palletizacao SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE cadastro_palletizacao SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cadastro_rota SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE cadastro_rota SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE cadastro_sub_rota SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE cadastro_sub_rota SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE carteira_copia SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE carteira_copia SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE carteira_principal SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE carteira_principal SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE faturamento_produto SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE faturamento_produto SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE programacao_producao SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE programacao_producao SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE teams_tasks SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE teams_tasks SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE unificacao_codigos SET created_at = created_at - INTERVAL '3 hours' WHERE created_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;
    UPDATE unificacao_codigos SET updated_at = updated_at - INTERVAL '3 hours' WHERE updated_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- ============================================================
    -- COLUNAS ESPECÍFICAS (changed_at, alterado_em, etc.)
    -- ============================================================
    UPDATE agent_memory_versions SET changed_at = changed_at - INTERVAL '3 hours' WHERE changed_at IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE historico_data_prevista SET alterado_em = alterado_em - INTERVAL '3 hours' WHERE alterado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE historico_pedido_compras SET alterado_em = alterado_em - INTERVAL '3 hours' WHERE alterado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE historico_requisicao_compras SET alterado_em = alterado_em - INTERVAL '3 hours' WHERE alterado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE lista_materiais_historico SET alterado_em = alterado_em - INTERVAL '3 hours' WHERE alterado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE contas_a_receber_snapshot SET alterado_em = alterado_em - INTERVAL '3 hours' WHERE alterado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- processado_em
    UPDATE bi_analise_regional SET processado_em = processado_em - INTERVAL '3 hours' WHERE processado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE bi_despesa_detalhada SET processado_em = processado_em - INTERVAL '3 hours' WHERE processado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE bi_frete_agregado SET processado_em = processado_em - INTERVAL '3 hours' WHERE processado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- calculado_em
    UPDATE bi_indicador_mensal SET calculado_em = calculado_em - INTERVAL '3 hours' WHERE calculado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE bi_performance_transportadora SET calculado_em = calculado_em - INTERVAL '3 hours' WHERE calculado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- validado_em
    UPDATE ncm_ibscbs_validado SET validado_em = validado_em - INTERVAL '3 hours' WHERE validado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE validacao_fiscal_dfe SET validado_em = validado_em - INTERVAL '3 hours' WHERE validado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE validacao_nf_po_dfe SET validado_em = validado_em - INTERVAL '3 hours' WHERE validado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- importado_em
    UPDATE comprovante_pagamento_boleto SET importado_em = importado_em - INTERVAL '3 hours' WHERE importado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE conhecimento_transporte SET importado_em = importado_em - INTERVAL '3 hours' WHERE importado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE historico_pedidos SET importado_em = importado_em - INTERVAL '3 hours' WHERE importado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- sincronizado_em
    UPDATE picking_recebimento SET sincronizado_em = sincronizado_em - INTERVAL '3 hours' WHERE sincronizado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- solicitado_em
    UPDATE aprovacoes_frete SET solicitado_em = solicitado_em - INTERVAL '3 hours' WHERE solicitado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- consolidado_em
    UPDATE validacao_nf_po_dfe SET consolidado_em = consolidado_em - INTERVAL '3 hours' WHERE consolidado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- respondida_em
    UPDATE pendencias_financeiras_nf SET respondida_em = respondida_em - INTERVAL '3 hours' WHERE respondida_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- executado_em
    UPDATE lancamento_frete_odoo_auditoria SET executado_em = executado_em - INTERVAL '3 hours' WHERE executado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- diagnosticado_em
    UPDATE correcao_data_nf_credito SET diagnosticado_em = diagnosticado_em - INTERVAL '3 hours' WHERE diagnosticado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- inativado_em
    UPDATE relatorio_faturamento_importado SET inativado_em = inativado_em - INTERVAL '3 hours' WHERE inativado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- adicionado_em
    UPDATE user_equipe SET adicionado_em = adicionado_em - INTERVAL '3 hours' WHERE adicionado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE user_vendedor SET adicionado_em = adicionado_em - INTERVAL '3 hours' WHERE adicionado_em IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_criacao
    UPDATE cotacoes SET data_criacao = data_criacao - INTERVAL '3 hours' WHERE data_criacao IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE pre_separacao_item SET data_criacao = data_criacao - INTERVAL '3 hours' WHERE data_criacao IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_alerta
    UPDATE alertas_separacao_cotada SET data_alerta = data_alerta - INTERVAL '3 hours' WHERE data_alerta IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_processamento
    UPDATE cnab_retorno_lote SET data_processamento = data_processamento - INTERVAL '3 hours' WHERE data_processamento IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_execucao
    UPDATE log_integracao SET data_execucao = data_execucao - INTERVAL '3 hours' WHERE data_execucao IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_hora
    UPDATE log_permissao_comercial SET data_hora = data_hora - INTERVAL '3 hours' WHERE data_hora IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE logs_entrega SET data_hora = data_hora - INTERVAL '3 hours' WHERE data_hora IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_contagem
    UPDATE contagem_devolucao SET data_contagem = data_contagem - INTERVAL '3 hours' WHERE data_contagem IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_abertura
    UPDATE ocorrencia_devolucao SET data_abertura = data_abertura - INTERVAL '3 hours' WHERE data_abertura IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_autorizacao
    UPDATE descarte_devolucao SET data_autorizacao = data_autorizacao - INTERVAL '3 hours' WHERE data_autorizacao IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_registro
    UPDATE nf_devolucao SET data_registro = data_registro - INTERVAL '3 hours' WHERE data_registro IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_importacao
    UPDATE portal_sendas_planilha_modelo SET data_importacao = data_importacao - INTERVAL '3 hours' WHERE data_importacao IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- data_confirmacao_odoo
    UPDATE requisicao_compras SET data_confirmacao_odoo = data_confirmacao_odoo - INTERVAL '3 hours' WHERE data_confirmacao_odoo IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- vigencia_inicio
    UPDATE custo_considerado SET vigencia_inicio = vigencia_inicio - INTERVAL '3 hours' WHERE vigencia_inicio IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- ultima_utilizacao / valido_ate (portal_sessoes)
    UPDATE portal_sessoes SET ultima_utilizacao = ultima_utilizacao - INTERVAL '3 hours' WHERE ultima_utilizacao IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    UPDATE portal_sessoes SET valido_ate = valido_ate - INTERVAL '3 hours' WHERE valido_ate IS NOT NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT; v_total_rows := v_total_rows + v_count;

    -- ============================================================
    -- REGISTRAR EXECUÇÃO
    -- ============================================================
    INSERT INTO _migration_log (migration_name, detalhes)
    VALUES (
        'migrar_timezone_utc_para_brasil_v1',
        'Total de registros atualizados: ' || v_total_rows::TEXT
    );

    RAISE NOTICE 'Migration concluída! Total de registros atualizados: %', v_total_rows;
END $$;
