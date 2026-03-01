-- =============================================================================
-- Remover Indices Duplicados — 84 indices redundantes
-- Avaliacao: 01/03/2026
-- Executar via: Render Shell (psql) ou script Python
-- =============================================================================
--
-- CAUSA RAIZ: 2 geradores de indices em conflito:
--   1. SQLAlchemy auto-gera ix_tabela_campo (via Column(index=True))
--   2. Migrations manuais criaram idx_tabela_campo
--
-- REGRA DE RESOLUCAO:
--   - Constraint (pkey, unique _key, uq_, uk_) → MANTER
--   - ix_ (SQLAlchemy auto) → MANTER (evita Alembic querer recriar)
--   - idx_ (migration manual) → DROPAR quando duplicado de ix_ ou constraint
--   - UNIQUE INDEX (uq_) sem constraint → MANTER (enforça integridade)
--
-- IMPACTO ESTIMADO: ~15 MB de espaco liberado + writes mais rapidos
-- =============================================================================

BEGIN;

-- =============================================
-- GRUPO 1: idx_ duplicados de constraints
-- (constraint enforça integridade, idx_ e redundante)
-- =============================================

-- agent_memory_embeddings: idx_ame_memory_id duplica uq_memory_embedding
DROP INDEX IF EXISTS idx_ame_memory_id;

-- agent_sessions: idx_agent_sessions_session_id duplica agent_sessions_session_id_key
DROP INDEX IF EXISTS idx_agent_sessions_session_id;

-- cadastro_cliente: idx_cadastro_cliente_cnpj duplica cadastro_cliente_cnpj_cpf_key
DROP INDEX IF EXISTS idx_cadastro_cliente_cnpj;

-- cadastro_sub_rota: idx_sub_rota_uf_cidade duplica uk_uf_cidade
DROP INDEX IF EXISTS idx_sub_rota_uf_cidade;

-- carrier_embeddings: idx_carrier_name duplica uq_carrier_name
DROP INDEX IF EXISTS idx_carrier_name;

-- codigo_sistema_gerado: idx_codigo_nome duplica codigo_sistema_gerado_nome_key
DROP INDEX IF EXISTS idx_codigo_nome;

-- conhecimento_transporte: idx_cte_chave_acesso duplica conhecimento_transporte_chave_acesso_key
DROP INDEX IF EXISTS idx_cte_chave_acesso;

-- conhecimento_transporte: idx_cte_dfe_id duplica conhecimento_transporte_dfe_id_key
DROP INDEX IF EXISTS idx_cte_dfe_id;

-- contagem_devolucao: idx_contagem_linha duplica contagem_devolucao_nf_devolucao_linha_id_key
DROP INDEX IF EXISTS idx_contagem_linha;

-- contas_a_pagar: idx_conta_pagar_odoo_line duplica contas_a_pagar_odoo_line_id_key
DROP INDEX IF EXISTS idx_conta_pagar_odoo_line;

-- correcao_data_nf_credito: idx_correcao_odoo_move_id duplica uq_correcao_odoo_move_id (UNIQUE INDEX)
DROP INDEX IF EXISTS idx_correcao_odoo_move_id;

-- custo_frete: idx_custo_frete_vigencia duplica custo_frete_incoterm_cod_uf_vigencia_inicio_key
DROP INDEX IF EXISTS idx_custo_frete_vigencia;

-- embarque_moto: idx_embarque_numero duplica embarque_moto_numero_embarque_key
DROP INDEX IF EXISTS idx_embarque_numero;

-- empresa_venda_moto: idx_empresa_venda_moto_cnpj duplica empresa_venda_moto_cnpj_empresa_key
DROP INDEX IF EXISTS idx_empresa_venda_moto_cnpj;

-- grupo_empresarial: idx_grupo_empresarial_prefixo duplica uk_prefixo_cnpj
DROP INDEX IF EXISTS idx_grupo_empresarial_prefixo;

-- movimentacao_prevista: idx_mov_prevista_produto_data duplica uq_produto_data
DROP INDEX IF EXISTS idx_mov_prevista_produto_data;

-- ncm_ibscbs_validado: idx_ncm_ibscbs_validado_prefixo duplica ncm_ibscbs_validado_ncm_prefixo_key
DROP INDEX IF EXISTS idx_ncm_ibscbs_validado_prefixo;

-- nf_devolucao: idx_nfd_chave duplica nf_devolucao_chave_nfd_key
DROP INDEX IF EXISTS idx_nfd_chave;

-- nf_devolucao: idx_nfd_odoo_dfe duplica nf_devolucao_odoo_dfe_id_key
DROP INDEX IF EXISTS idx_nfd_odoo_dfe;

-- ocorrencia_devolucao: idx_ocorrencia_nfd duplica ocorrencia_devolucao_nf_devolucao_id_key
DROP INDEX IF EXISTS idx_ocorrencia_nfd;

-- ocorrencia_devolucao: idx_ocorrencia_numero duplica ocorrencia_devolucao_numero_ocorrencia_key
DROP INDEX IF EXISTS idx_ocorrencia_numero;

-- pedido_importacao_temp: idx_pedido_imp_temp_chave duplica pedido_importacao_temp_chave_importacao_key
DROP INDEX IF EXISTS idx_pedido_imp_temp_chave;

-- pedido_venda_moto: idx_pedido_numero_nf duplica pedido_venda_moto_numero_nf_key
DROP INDEX IF EXISTS idx_pedido_numero_nf;

-- pedido_venda_moto: idx_pedido_numero_pedido duplica pedido_venda_moto_numero_pedido_key
DROP INDEX IF EXISTS idx_pedido_numero_pedido;

-- pendencia_fiscal_ibscbs: idx_pendencia_ibscbs_chave duplica pendencia_fiscal_ibscbs_chave_acesso_key
DROP INDEX IF EXISTS idx_pendencia_ibscbs_chave;

-- portal_sendas_filial_depara: idx_sendas_filial_cnpj duplica portal_sendas_filial_depara_cnpj_key
DROP INDEX IF EXISTS idx_sendas_filial_cnpj;

-- portal_sendas_filial_depara: idx_sendas_filial_filial duplica portal_sendas_filial_depara_filial_key
DROP INDEX IF EXISTS idx_sendas_filial_filial;

-- product_embeddings: idx_prod_emb_cod duplica product_embeddings_cod_produto_key
DROP INDEX IF EXISTS idx_prod_emb_cod;

-- rastreamento_embarques: idx_rastreamento_embarques_embarque_id duplica rastreamento_embarques_embarque_id_key
DROP INDEX IF EXISTS idx_rastreamento_embarques_embarque_id;

-- rastreamento_embarques: idx_rastreamento_embarques_token duplica rastreamento_embarques_token_acesso_key
DROP INDEX IF EXISTS idx_rastreamento_embarques_token;

-- regiao_tabela_rede: idx_regiao_rede_uf duplica uq_regiao_rede_uf
DROP INDEX IF EXISTS idx_regiao_rede_uf;

-- requisicao_compra_alocacao: idx_alocacao_odoo_allocation_id duplica requisicao_compra_alocacao_odoo_allocation_id_key
DROP INDEX IF EXISTS idx_alocacao_odoo_allocation_id;

-- requisicao_compra_alocacao: idx_alocacao_odoo_ids duplica uq_allocation_request_order
DROP INDEX IF EXISTS idx_alocacao_odoo_ids;

-- saldo_estoque_cache: idx_saldo_cache_produto duplica saldo_estoque_cache_cod_produto_key
DROP INDEX IF EXISTS idx_saldo_cache_produto;

-- validacao_fiscal_dfe: idx_validacao_dfe_odoo duplica validacao_fiscal_dfe_odoo_dfe_id_key
DROP INDEX IF EXISTS idx_validacao_dfe_odoo;


-- =============================================
-- GRUPO 2: idx_ duplicados de ix_ (SQLAlchemy auto)
-- (ix_ vem do model Column(index=True), manter para consistencia)
-- =============================================

-- alertas_separacao_cotada: idx_ duplica ix_
DROP INDEX IF EXISTS idx_alertas_num_pedido;
DROP INDEX IF EXISTS idx_alertas_reimpresso;
DROP INDEX IF EXISTS idx_alertas_separacao_lote;

-- cadastro_palletizacao: idx_ duplica ix_
DROP INDEX IF EXISTS idx_palletizacao_cod_produto;

-- carteira_principal: idx_ duplica ix_
DROP INDEX IF EXISTS idx_carteira_cod_produto;
DROP INDEX IF EXISTS idx_carteira_num_pedido;

-- estoque_tempo_real: idx_ duplica ix_
DROP INDEX IF EXISTS idx_estoque_tempo_real_atualizado;

-- estoque_tempo_real: ix_ duplica PK (cod_produto e PK)
DROP INDEX IF EXISTS ix_estoque_tempo_real_cod_produto;

-- faturamento_produto: idx_ duplica ix_
DROP INDEX IF EXISTS idx_faturamento_pedido;
DROP INDEX IF EXISTS idx_faturamento_produto_nf;

-- historico_pedidos: idx_ duplica ix_
DROP INDEX IF EXISTS idx_hist_data;
DROP INDEX IF EXISTS idx_hist_grupo;
DROP INDEX IF EXISTS idx_hist_produto;

-- lead_time_fornecedor: idx_ duplica ix_
DROP INDEX IF EXISTS idx_ltf_fornecedor;
DROP INDEX IF EXISTS idx_ltf_produto;

-- lista_materiais: idx_ duplica ix_
DROP INDEX IF EXISTS idx_lm_componente;
DROP INDEX IF EXISTS idx_lm_produzido;
DROP INDEX IF EXISTS idx_lm_status;

-- mapeamento_tipo_odoo: idx_ duplica ix_
DROP INDEX IF EXISTS idx_mapeamento_tipo_odoo;
DROP INDEX IF EXISTS idx_mapeamento_tipo_sistema;

-- match_nf_po_alocacao: idx_ duplica ix_
DROP INDEX IF EXISTS idx_alocacao_match_item;

-- ordem_producao: idx_ duplica ix_ (7 indices)
DROP INDEX IF EXISTS idx_op_data_inicio;
DROP INDEX IF EXISTS idx_op_linha;
DROP INDEX IF EXISTS idx_op_numero;
DROP INDEX IF EXISTS idx_op_produto;
DROP INDEX IF EXISTS idx_op_separacao_lote;
DROP INDEX IF EXISTS idx_op_status;
DROP INDEX IF EXISTS idx_ordem_producao_pai;

-- pedido_compras: idx_ duplica ix_
DROP INDEX IF EXISTS idx_ped_fornecedor;
DROP INDEX IF EXISTS idx_ped_numero;
DROP INDEX IF EXISTS idx_ped_produto;
DROP INDEX IF EXISTS idx_ped_requisicao;

-- plano_mestre_producao: idx_ duplica ix_
DROP INDEX IF EXISTS idx_pmp_status;

-- pre_separacao_itens: idx_ duplica ix_
DROP INDEX IF EXISTS idx_pre_separacao_carteira_id;

-- previsao_demanda: idx_ duplica ix_
DROP INDEX IF EXISTS idx_prev_produto;

-- programacao_producao: idx_ duplica ix_
DROP INDEX IF EXISTS idx_programacao_data;

-- recursos_producao: idx_ duplica ix_
DROP INDEX IF EXISTS idx_rec_linha;
DROP INDEX IF EXISTS idx_rec_produto;

-- requisicao_compras: idx_ duplica ix_
DROP INDEX IF EXISTS idx_req_produto;
DROP INDEX IF EXISTS idx_req_status;
DROP INDEX IF EXISTS idx_requisicao_odoo_id;

-- unificacao_codigos: idx_ duplica ix_
DROP INDEX IF EXISTS idx_unificacao_ativo;
DROP INDEX IF EXISTS idx_unificacao_destino;
DROP INDEX IF EXISTS idx_unificacao_origem;


-- =============================================
-- GRUPO 3: idx_/idx_ duplicados entre si (ambos manuais)
-- (manter o nome mais curto/claro)
-- =============================================

-- ai_advanced_sessions: idx_ai_sessions_user_date duplica idx_ai_sessions_user
DROP INDEX IF EXISTS idx_ai_sessions_user_date;

-- divergencia_nf_po: idx_divergencia_validacao duplica idx_div_nf_po_validacao
DROP INDEX IF EXISTS idx_divergencia_validacao;

-- nf_devolucao: idx_nfd_odoo_nf_venda_id duplica idx_nfd_odoo_nf_venda
DROP INDEX IF EXISTS idx_nfd_odoo_nf_venda_id;

-- requisicao_compras: idx_requisicao_num duplica idx_req_numero
DROP INDEX IF EXISTS idx_requisicao_num;

-- validacao_nf_po_dfe: idx_validacao_odoo_dfe duplica idx_val_nf_po_dfe
DROP INDEX IF EXISTS idx_validacao_odoo_dfe;

COMMIT;

-- =============================================================================
-- VERIFICACAO POS-EXECUCAO:
-- =============================================================================
-- SELECT count(*) FROM pg_indexes WHERE schemaname = 'public';
-- (deve reduzir em ~84 indices)
--
-- Verificar espaco liberado (requer VACUUM apos DROP):
-- SELECT pg_size_pretty(pg_database_size(current_database())) AS tamanho_banco;
