-- =============================================================================
-- Migration: Limpar tabelas deprecated e indices nao usados
-- Data: 2026-02-12
-- Descricao: Remove 30 tabelas vazias/deprecated e 10 indices com 0 scans
-- =============================================================================

-- AI (7 tabelas)
DROP TABLE IF EXISTS ai_feedback_history CASCADE;
DROP TABLE IF EXISTS ai_semantic_embeddings CASCADE;
DROP TABLE IF EXISTS ai_learning_patterns CASCADE;
DROP TABLE IF EXISTS ai_performance_metrics CASCADE;
DROP TABLE IF EXISTS ai_response_templates CASCADE;
DROP TABLE IF EXISTS ai_business_contexts CASCADE;
DROP TABLE IF EXISTS ai_grupos_empresariais CASCADE;

-- MCP (6 tabelas)
DROP TABLE IF EXISTS mcp_error_logs CASCADE;
DROP TABLE IF EXISTS mcp_entity_mappings CASCADE;
DROP TABLE IF EXISTS mcp_confirmation_requests CASCADE;
DROP TABLE IF EXISTS mcp_query_history CASCADE;
DROP TABLE IF EXISTS mcp_learning_patterns CASCADE;
DROP TABLE IF EXISTS mcp_user_preferences CASCADE;

-- Permissions v2 (10 tabelas) - ORDEM: dependentes primeiro, depois pais
DROP TABLE IF EXISTS user_permission CASCADE;
DROP TABLE IF EXISTS equipe_permission CASCADE;
DROP TABLE IF EXISTS vendedor_permission CASCADE;
DROP TABLE IF EXISTS permission_cache CASCADE;
DROP TABLE IF EXISTS permission_log CASCADE;
DROP TABLE IF EXISTS batch_operation CASCADE;
DROP TABLE IF EXISTS permission_template CASCADE;
DROP TABLE IF EXISTS permission_submodule CASCADE;
DROP TABLE IF EXISTS permission_module CASCADE;
DROP TABLE IF EXISTS permission_category CASCADE;

-- Permissions v1 orphaned (4 tabelas)
DROP TABLE IF EXISTS permissao_usuario CASCADE;
DROP TABLE IF EXISTS permissao_equipe CASCADE;
DROP TABLE IF EXISTS permissao_vendedor CASCADE;
DROP TABLE IF EXISTS funcao_modulo CASCADE;

-- Outros (3 tabelas)
DROP TABLE IF EXISTS inconsistencia_faturamento CASCADE;
DROP TABLE IF EXISTS vinculacao_carteira_separacao CASCADE;
DROP TABLE IF EXISTS controle_descasamento_nf CASCADE;

-- Indices nao usados (10)
DROP INDEX IF EXISTS idx_hist_ped_num_data;
DROP INDEX IF EXISTS idx_hist_ped_pedido_data;
DROP INDEX IF EXISTS idx_ai_sessions_metadata_gin;
DROP INDEX IF EXISTS idx_ai_sessions_metadata;
DROP INDEX IF EXISTS idx_carteira_cnpj_saldo;
DROP INDEX IF EXISTS idx_carteira_pedido_cliente_unaccent;
DROP INDEX IF EXISTS idx_historico_componente_data;
DROP INDEX IF EXISTS ix_historico_pedidos_num_pedido;
DROP INDEX IF EXISTS idx_carteira_raz_social_unaccent;
DROP INDEX IF EXISTS idx_conta_receber_titulo_nf;
