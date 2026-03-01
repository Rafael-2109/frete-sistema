"""
Remover Indices Duplicados — 84 indices redundantes

Avaliacao: 01/03/2026

CAUSA RAIZ: 2 geradores de indices em conflito:
  1. SQLAlchemy auto-gera ix_tabela_campo (via Column(index=True))
  2. Migrations manuais criaram idx_tabela_campo

REGRA DE RESOLUCAO:
  - Constraint (pkey, unique _key, uq_, uk_) -> MANTER
  - ix_ (SQLAlchemy auto) -> MANTER (evita recreacao em db.create_all())
  - idx_ (migration manual) -> DROPAR quando duplicado de ix_ ou constraint
  - UNIQUE INDEX (uq_) sem constraint -> MANTER (enforce integridade)

IMPACTO ESTIMADO: ~15 MB de espaco liberado + writes mais rapidos em 50+ tabelas
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


# =============================================
# GRUPO 1: idx_ duplicados de constraints
# =============================================
GRUPO_1_CONSTRAINT_DUPES = [
    # (indice_a_dropar, tabela, constraint_mantida)
    ('idx_ame_memory_id', 'agent_memory_embeddings', 'uq_memory_embedding'),
    ('idx_agent_sessions_session_id', 'agent_sessions', 'agent_sessions_session_id_key'),
    ('idx_cadastro_cliente_cnpj', 'cadastro_cliente', 'cadastro_cliente_cnpj_cpf_key'),
    ('idx_sub_rota_uf_cidade', 'cadastro_sub_rota', 'uk_uf_cidade'),
    ('idx_carrier_name', 'carrier_embeddings', 'uq_carrier_name'),
    ('idx_codigo_nome', 'codigo_sistema_gerado', 'codigo_sistema_gerado_nome_key'),
    ('idx_cte_chave_acesso', 'conhecimento_transporte', 'conhecimento_transporte_chave_acesso_key'),
    ('idx_cte_dfe_id', 'conhecimento_transporte', 'conhecimento_transporte_dfe_id_key'),
    ('idx_contagem_linha', 'contagem_devolucao', 'contagem_devolucao_nf_devolucao_linha_id_key'),
    ('idx_conta_pagar_odoo_line', 'contas_a_pagar', 'contas_a_pagar_odoo_line_id_key'),
    ('idx_correcao_odoo_move_id', 'correcao_data_nf_credito', 'uq_correcao_odoo_move_id'),
    ('idx_custo_frete_vigencia', 'custo_frete', 'custo_frete_incoterm_cod_uf_vigencia_inicio_key'),
    ('idx_embarque_numero', 'embarque_moto', 'embarque_moto_numero_embarque_key'),
    ('idx_empresa_venda_moto_cnpj', 'empresa_venda_moto', 'empresa_venda_moto_cnpj_empresa_key'),
    ('idx_grupo_empresarial_prefixo', 'grupo_empresarial', 'uk_prefixo_cnpj'),
    ('idx_mov_prevista_produto_data', 'movimentacao_prevista', 'uq_produto_data'),
    ('idx_ncm_ibscbs_validado_prefixo', 'ncm_ibscbs_validado', 'ncm_ibscbs_validado_ncm_prefixo_key'),
    ('idx_nfd_chave', 'nf_devolucao', 'nf_devolucao_chave_nfd_key'),
    ('idx_nfd_odoo_dfe', 'nf_devolucao', 'nf_devolucao_odoo_dfe_id_key'),
    ('idx_ocorrencia_nfd', 'ocorrencia_devolucao', 'ocorrencia_devolucao_nf_devolucao_id_key'),
    ('idx_ocorrencia_numero', 'ocorrencia_devolucao', 'ocorrencia_devolucao_numero_ocorrencia_key'),
    ('idx_pedido_imp_temp_chave', 'pedido_importacao_temp', 'pedido_importacao_temp_chave_importacao_key'),
    ('idx_pedido_numero_nf', 'pedido_venda_moto', 'pedido_venda_moto_numero_nf_key'),
    ('idx_pedido_numero_pedido', 'pedido_venda_moto', 'pedido_venda_moto_numero_pedido_key'),
    ('idx_pendencia_ibscbs_chave', 'pendencia_fiscal_ibscbs', 'pendencia_fiscal_ibscbs_chave_acesso_key'),
    ('idx_sendas_filial_cnpj', 'portal_sendas_filial_depara', 'portal_sendas_filial_depara_cnpj_key'),
    ('idx_sendas_filial_filial', 'portal_sendas_filial_depara', 'portal_sendas_filial_depara_filial_key'),
    ('idx_prod_emb_cod', 'product_embeddings', 'product_embeddings_cod_produto_key'),
    ('idx_rastreamento_embarques_embarque_id', 'rastreamento_embarques', 'rastreamento_embarques_embarque_id_key'),
    ('idx_rastreamento_embarques_token', 'rastreamento_embarques', 'rastreamento_embarques_token_acesso_key'),
    ('idx_regiao_rede_uf', 'regiao_tabela_rede', 'uq_regiao_rede_uf'),
    ('idx_alocacao_odoo_allocation_id', 'requisicao_compra_alocacao', 'requisicao_compra_alocacao_odoo_allocation_id_key'),
    ('idx_alocacao_odoo_ids', 'requisicao_compra_alocacao', 'uq_allocation_request_order'),
    ('idx_saldo_cache_produto', 'saldo_estoque_cache', 'saldo_estoque_cache_cod_produto_key'),
    ('idx_validacao_dfe_odoo', 'validacao_fiscal_dfe', 'validacao_fiscal_dfe_odoo_dfe_id_key'),
]

# =============================================
# GRUPO 2: idx_ duplicados de ix_ (SQLAlchemy)
# =============================================
GRUPO_2_SQLALCHEMY_DUPES = [
    # (indice_a_dropar, tabela, ix_mantido)
    ('idx_alertas_num_pedido', 'alertas_separacao_cotada', 'ix_alertas_separacao_cotada_num_pedido'),
    ('idx_alertas_reimpresso', 'alertas_separacao_cotada', 'ix_alertas_separacao_cotada_reimpresso'),
    ('idx_alertas_separacao_lote', 'alertas_separacao_cotada', 'ix_alertas_separacao_cotada_separacao_lote_id'),
    ('idx_palletizacao_cod_produto', 'cadastro_palletizacao', 'ix_cadastro_palletizacao_cod_produto'),
    ('idx_carteira_cod_produto', 'carteira_principal', 'ix_carteira_principal_cod_produto'),
    ('idx_carteira_num_pedido', 'carteira_principal', 'ix_carteira_principal_num_pedido'),
    ('idx_estoque_tempo_real_atualizado', 'estoque_tempo_real', 'ix_estoque_tempo_real_atualizado_em'),
    ('idx_faturamento_pedido', 'faturamento_produto', 'ix_faturamento_produto_origem'),
    ('idx_faturamento_produto_nf', 'faturamento_produto', 'ix_faturamento_produto_numero_nf'),
    ('idx_hist_data', 'historico_pedidos', 'ix_historico_pedidos_data_pedido'),
    ('idx_hist_grupo', 'historico_pedidos', 'ix_historico_pedidos_nome_grupo'),
    ('idx_hist_produto', 'historico_pedidos', 'ix_historico_pedidos_cod_produto'),
    ('idx_ltf_fornecedor', 'lead_time_fornecedor', 'ix_lead_time_fornecedor_cnpj_fornecedor'),
    ('idx_ltf_produto', 'lead_time_fornecedor', 'ix_lead_time_fornecedor_cod_produto'),
    ('idx_lm_componente', 'lista_materiais', 'ix_lista_materiais_cod_produto_componente'),
    ('idx_lm_produzido', 'lista_materiais', 'ix_lista_materiais_cod_produto_produzido'),
    ('idx_lm_status', 'lista_materiais', 'ix_lista_materiais_status'),
    ('idx_mapeamento_tipo_odoo', 'mapeamento_tipo_odoo', 'ix_mapeamento_tipo_odoo_tipo_odoo'),
    ('idx_mapeamento_tipo_sistema', 'mapeamento_tipo_odoo', 'ix_mapeamento_tipo_odoo_tipo_sistema_id'),
    ('idx_alocacao_match_item', 'match_nf_po_alocacao', 'ix_match_nf_po_alocacao_match_item_id'),
    ('idx_op_data_inicio', 'ordem_producao', 'ix_ordem_producao_data_inicio_prevista'),
    ('idx_op_linha', 'ordem_producao', 'ix_ordem_producao_linha_producao'),
    ('idx_op_numero', 'ordem_producao', 'ix_ordem_producao_numero_ordem'),
    ('idx_op_produto', 'ordem_producao', 'ix_ordem_producao_cod_produto'),
    ('idx_op_separacao_lote', 'ordem_producao', 'ix_ordem_producao_separacao_lote_id'),
    ('idx_op_status', 'ordem_producao', 'ix_ordem_producao_status'),
    ('idx_ordem_producao_pai', 'ordem_producao', 'ix_ordem_producao_ordem_pai_id'),
    ('idx_ped_fornecedor', 'pedido_compras', 'ix_pedido_compras_cnpj_fornecedor'),
    ('idx_ped_numero', 'pedido_compras', 'ix_pedido_compras_num_pedido'),
    ('idx_ped_produto', 'pedido_compras', 'ix_pedido_compras_cod_produto'),
    ('idx_ped_requisicao', 'pedido_compras', 'ix_pedido_compras_num_requisicao'),
    ('idx_pmp_status', 'plano_mestre_producao', 'ix_plano_mestre_producao_status_geracao'),
    ('idx_pre_separacao_carteira_id', 'pre_separacao_itens', 'ix_pre_separacao_itens_carteira_principal_id'),
    ('idx_prev_produto', 'previsao_demanda', 'ix_previsao_demanda_cod_produto'),
    ('idx_programacao_data', 'programacao_producao', 'ix_programacao_producao_data_programacao'),
    ('idx_rec_linha', 'recursos_producao', 'ix_recursos_producao_linha_producao'),
    ('idx_rec_produto', 'recursos_producao', 'ix_recursos_producao_cod_produto'),
    ('idx_req_produto', 'requisicao_compras', 'ix_requisicao_compras_cod_produto'),
    ('idx_req_status', 'requisicao_compras', 'ix_requisicao_compras_status'),
    ('idx_requisicao_odoo_id', 'requisicao_compras', 'ix_requisicao_compras_requisicao_odoo_id'),
    ('idx_unificacao_ativo', 'unificacao_codigos', 'ix_unificacao_codigos_ativo'),
    ('idx_unificacao_destino', 'unificacao_codigos', 'ix_unificacao_codigos_codigo_destino'),
    ('idx_unificacao_origem', 'unificacao_codigos', 'ix_unificacao_codigos_codigo_origem'),
]

# =============================================
# GRUPO 2b: ix_ redundante com PK
# =============================================
GRUPO_2B_PK_DUPES = [
    # (indice_a_dropar, tabela, pk_mantido)
    ('ix_estoque_tempo_real_cod_produto', 'estoque_tempo_real', 'estoque_tempo_real_pkey'),
]

# =============================================
# GRUPO 3: idx_/idx_ duplicados (ambos manuais)
# =============================================
GRUPO_3_MANUAL_DUPES = [
    # (indice_a_dropar, tabela, indice_mantido)
    ('idx_ai_sessions_user_date', 'ai_advanced_sessions', 'idx_ai_sessions_user'),
    ('idx_divergencia_validacao', 'divergencia_nf_po', 'idx_div_nf_po_validacao'),
    ('idx_nfd_odoo_nf_venda_id', 'nf_devolucao', 'idx_nfd_odoo_nf_venda'),
    ('idx_requisicao_num', 'requisicao_compras', 'idx_req_numero'),
    ('idx_validacao_odoo_dfe', 'validacao_nf_po_dfe', 'idx_val_nf_po_dfe'),
]


def contar_indices(app):
    """Conta total de indices no schema public"""
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT count(*) AS total
            FROM pg_indexes
            WHERE schemaname = 'public'
        """))
        return resultado.scalar() or 0


def verificar_existencia(app, indices_para_dropar):
    """Verifica quais dos indices listados realmente existem"""
    nomes = [idx[0] for idx in indices_para_dropar]
    with app.app_context():
        resultado = db.session.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = ANY(:nomes)
        """), {'nomes': nomes})
        existentes = {r.indexname for r in resultado.fetchall()}
    return existentes


def executar_drops(app, indices_para_dropar, grupo_nome, dry_run=True):
    """Executa DROP INDEX para uma lista de indices"""
    existentes = verificar_existencia(app, indices_para_dropar)

    print(f"\n  {grupo_nome}:")
    print(f"  {'='*70}")

    drops_executados = 0
    for idx_nome, tabela, mantido in indices_para_dropar:
        existe = idx_nome in existentes
        if not existe:
            print(f"    SKIP  {idx_nome} (ja removido)")
            continue

        if dry_run:
            print(f"    DROP  {idx_nome} ({tabela}) -- mantendo {mantido}")
            drops_executados += 1
        else:
            try:
                with app.app_context():
                    db.session.execute(text(f"DROP INDEX IF EXISTS {idx_nome}"))
                    db.session.commit()
                print(f"    OK    {idx_nome} ({tabela})")
                drops_executados += 1
            except Exception as e:
                print(f"    ERRO  {idx_nome}: {e}")

    return drops_executados


if __name__ == '__main__':
    print("=" * 80)
    print("REMOVER INDICES DUPLICADOS — 84 indices redundantes")
    print("=" * 80)

    dry_run = '--execute' not in sys.argv
    app = create_app()

    # Contagem antes
    total_antes = contar_indices(app)
    print(f"\n  Total de indices ANTES: {total_antes}")

    todos_indices = (
        GRUPO_1_CONSTRAINT_DUPES
        + GRUPO_2_SQLALCHEMY_DUPES
        + GRUPO_2B_PK_DUPES
        + GRUPO_3_MANUAL_DUPES
    )

    print(f"  Indices a dropar: {len(todos_indices)}")

    if dry_run:
        print(f"\n  [DRY RUN] Listando indices que seriam removidos:")
    else:
        print(f"\n  [EXECUTANDO] Removendo indices duplicados:")

    total_drops = 0
    total_drops += executar_drops(
        app,
        GRUPO_1_CONSTRAINT_DUPES,
        "GRUPO 1: idx_ duplicados de constraints",
        dry_run
    )
    total_drops += executar_drops(
        app,
        GRUPO_2_SQLALCHEMY_DUPES,
        "GRUPO 2: idx_ duplicados de ix_ (SQLAlchemy)",
        dry_run
    )
    total_drops += executar_drops(
        app,
        GRUPO_2B_PK_DUPES,
        "GRUPO 2b: ix_ redundante com PK",
        dry_run
    )
    total_drops += executar_drops(
        app,
        GRUPO_3_MANUAL_DUPES,
        "GRUPO 3: idx_/idx_ duplicados entre si",
        dry_run
    )

    print(f"\n{'='*80}")
    print(f"  Total processado: {total_drops} indices")

    if dry_run:
        print(f"\n  [DRY RUN] Nenhuma acao executada.")
        print(f"  Para executar: python {__file__} --execute")
        print(f"  Ou via Render Shell: copiar comandos de remover_indices_duplicados.sql")
    else:
        total_depois = contar_indices(app)
        print(f"\n  Total de indices ANTES:  {total_antes}")
        print(f"  Total de indices DEPOIS: {total_depois}")
        removidos = total_antes - total_depois
        print(f"  Indices removidos:       {removidos}")
        print(f"\n  PROXIMO PASSO: Executar VACUUM em tabelas afetadas para liberar espaco.")

    print(f"{'='*80}")
