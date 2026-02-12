"""
Migration: Limpar tabelas deprecated e indices nao usados
Data: 2026-02-12
Descricao: Remove 30 tabelas vazias/deprecated e 10 indices com 0 scans

Tabelas removidas:
  - AI (7): ai_feedback_history, ai_semantic_embeddings, ai_learning_patterns,
            ai_performance_metrics, ai_response_templates, ai_business_contexts,
            ai_grupos_empresariais
  - MCP (6): mcp_error_logs, mcp_entity_mappings, mcp_confirmation_requests,
             mcp_query_history, mcp_learning_patterns, mcp_user_preferences
  - Permissions v2 (10): user_permission, equipe_permission, vendedor_permission,
                         permission_cache, permission_log, batch_operation,
                         permission_template, permission_submodule, permission_module,
                         permission_category
  - Permissions v1 orphaned (4): permissao_usuario, permissao_equipe,
                                  permissao_vendedor, funcao_modulo
  - Outros (3): inconsistencia_faturamento, vinculacao_carteira_separacao,
                controle_descasamento_nf

Indices removidos (10):
  - idx_hist_ped_num_data, idx_hist_ped_pedido_data, idx_ai_sessions_metadata_gin,
    idx_ai_sessions_metadata, idx_carteira_cnpj_saldo,
    idx_carteira_pedido_cliente_unaccent, idx_historico_componente_data,
    ix_historico_pedidos_num_pedido, idx_carteira_raz_social_unaccent,
    idx_conta_receber_titulo_nf
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text

TABELAS_PARA_REMOVER = [
    # AI (7)
    'ai_feedback_history',
    'ai_semantic_embeddings',
    'ai_learning_patterns',
    'ai_performance_metrics',
    'ai_response_templates',
    'ai_business_contexts',
    'ai_grupos_empresariais',
    # MCP (6)
    'mcp_error_logs',
    'mcp_entity_mappings',
    'mcp_confirmation_requests',
    'mcp_query_history',
    'mcp_learning_patterns',
    'mcp_user_preferences',
    # Permissions v2 (10) - dependentes primeiro
    'user_permission',
    'equipe_permission',
    'vendedor_permission',
    'permission_cache',
    'permission_log',
    'batch_operation',
    'permission_template',
    'permission_submodule',
    'permission_module',
    'permission_category',
    # Permissions v1 orphaned (4)
    'permissao_usuario',
    'permissao_equipe',
    'permissao_vendedor',
    'funcao_modulo',
    # Outros (3)
    'inconsistencia_faturamento',
    'vinculacao_carteira_separacao',
    'controle_descasamento_nf',
]

INDICES_PARA_REMOVER = [
    'idx_hist_ped_num_data',
    'idx_hist_ped_pedido_data',
    'idx_ai_sessions_metadata_gin',
    'idx_ai_sessions_metadata',
    'idx_carteira_cnpj_saldo',
    'idx_carteira_pedido_cliente_unaccent',
    'idx_historico_componente_data',
    'ix_historico_pedidos_num_pedido',
    'idx_carteira_raz_social_unaccent',
    'idx_conta_receber_titulo_nf',
]


def main():
    app = create_app()

    with app.app_context():
        # ====== BEFORE: contar tabelas e indices existentes ======
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename = ANY(:tabelas)"
            ), {'tabelas': TABELAS_PARA_REMOVER})
            tabelas_existentes = [row[0] for row in result]

            result = conn.execute(text(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
                "AND indexname = ANY(:indices)"
            ), {'indices': INDICES_PARA_REMOVER})
            indices_existentes = [row[0] for row in result]

        print(f"\n{'='*60}")
        print(f"BEFORE: {len(tabelas_existentes)}/{len(TABELAS_PARA_REMOVER)} tabelas existem")
        if tabelas_existentes:
            for t in tabelas_existentes:
                print(f"  - {t}")
        print(f"BEFORE: {len(indices_existentes)}/{len(INDICES_PARA_REMOVER)} indices existem")
        if indices_existentes:
            for i in indices_existentes:
                print(f"  - {i}")
        print(f"{'='*60}\n")

        if not tabelas_existentes and not indices_existentes:
            print("Nada a fazer - todas as tabelas e indices ja foram removidos.")
            return

        # ====== EXECUTE: DROP tables + indexes ======
        with db.engine.begin() as conn:
            # Drop tabelas
            for tabela in TABELAS_PARA_REMOVER:
                if tabela in tabelas_existentes:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{tabela}" CASCADE'))
                    print(f"  DROP TABLE {tabela} CASCADE")

            # Drop indices
            for indice in INDICES_PARA_REMOVER:
                if indice in indices_existentes:
                    conn.execute(text(f'DROP INDEX IF EXISTS "{indice}"'))
                    print(f"  DROP INDEX {indice}")

        print("\nDROPs executados com sucesso (auto-commit).")

        # ====== AFTER: verificar remocao ======
        with db.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename = ANY(:tabelas)"
            ), {'tabelas': TABELAS_PARA_REMOVER})
            tabelas_restantes = [row[0] for row in result]

            result = conn.execute(text(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
                "AND indexname = ANY(:indices)"
            ), {'indices': INDICES_PARA_REMOVER})
            indices_restantes = [row[0] for row in result]

        print(f"\n{'='*60}")
        print(f"AFTER: {len(tabelas_restantes)} tabelas restantes (esperado: 0)")
        if tabelas_restantes:
            print(f"  AVISO - tabelas nao removidas: {tabelas_restantes}")
        print(f"AFTER: {len(indices_restantes)} indices restantes (esperado: 0)")
        if indices_restantes:
            print(f"  AVISO - indices nao removidos: {indices_restantes}")

        if not tabelas_restantes and not indices_restantes:
            print("\nMigration concluida com sucesso!")
        else:
            print("\nAVISO: Alguns itens nao foram removidos. Verifique manualmente.")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
