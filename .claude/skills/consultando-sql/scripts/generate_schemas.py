#!/usr/bin/env python3
"""
Script: generate_schemas.py
Gera automaticamente schemas JSON a partir dos modelos SQLAlchemy.

Produz:
  schemas/catalog.json          - Catálogo leve (nome + descrição + key_fields) de TODAS tabelas
  schemas/tables/{table}.json   - Schema detalhado por tabela (campos, tipos, FKs, regras)
  schemas/relationships.json    - Mapa de ForeignKeys entre tabelas

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python .claude/skills/consultando-sql/scripts/generate_schemas.py
    python .claude/skills/consultando-sql/scripts/generate_schemas.py --stats  # apenas estatísticas
"""
import sys
import os
import json
import importlib
import inspect
import re
import argparse

# Adicionar raiz do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, PROJECT_ROOT)

# Diretórios de output
SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), '..', 'schemas')
TABLES_DIR = os.path.join(SCHEMAS_DIR, 'tables')

# =====================================================================
# TABELAS BLOQUEADAS — Nunca expor ao LLM
# =====================================================================
BLOCKED_TABLES = {
    # Auth / Permissões
    'usuarios', 'permission_category', 'permission_module',
    'permission_submodule', 'user_permission', 'permission_template',
    'permission_cache', 'permission_log', 'batch_operation',
    'perfil_usuario', 'vendedor_permission', 'equipe_permission',
    # Agente
    'agent_sessions', 'agent_memories', 'agent_memory_versions',
    # Alembic
    'alembic_version',
    # Sessões web
    'portal_sessoes',
    # Tokens/OAuth
    'tagplus_oauth_token',
}

# =====================================================================
# TABELAS MORTAS — 0 registros em produção (levantamento 2026-02-01)
# Excluídas do catálogo para reduzir ruído no prompt do LLM.
# Schemas detalhados NÃO são gerados para estas tabelas.
# Reavalie periodicamente: se uma tabela ganhar dados, remova-a daqui.
# =====================================================================
DEAD_TABLES = {
    # BI (todas vazias)
    'bi_analise_regional', 'bi_despesa_detalhada', 'bi_frete_agregado',
    'bi_indicador_mensal', 'bi_performance_transportadora',
    # Módulo MOTO (inteiro vazio)
    'cliente_moto', 'embarque_moto', 'empresa_venda_moto',
    'equipe_vendas_moto', 'modelo_moto', 'moto',
    'pedido_venda_moto', 'pedido_venda_moto_item',
    'transportadora_moto', 'vendedor_moto',
    # Financeiro fantasma (nunca populadas)
    'comissao_vendedor', 'custos_operacionais', 'despesa_mensal',
    'liberacao_antecipacao', 'movimentacao_financeira',
    'titulo_a_pagar', 'titulo_financeiro',
    # Carteira / Separação (vazias)
    'carteira_copia', 'controle_cruzado_separacao',
    'vinculacao_carteira_separacao',
    # Devoluções (parcialmente mortas)
    'anexo_ocorrencia', 'contagem_devolucao',
    'descarte_devolucao', 'descarte_item', 'divergencia_fiscal',
    # Frete (vazias)
    'fretes_lancados', 'custos_extra_entrega',
    'tabela_preco_crossdocking', 'cross_docking',
    # Comercial/Vendas (nunca usadas)
    'equipe_vendas', 'vendedor', 'user_equipe', 'user_vendedor',
    'regra_comissao', 'tabela_preco_equipe',
    # Notificações/Webhooks (vazias)
    'alerta_notificacoes', 'webhook_configs',
    # Integrações (vazias)
    'log_integracao', 'mapeamento_tipo_odoo',
    # Pedidos (fantasma — 'pedidos' não existe no banco, demais vazias)
    'pedidos', 'pedido_venda_auditoria', 'embarque_pedido',
    # Custos/Custeio (vazias)
    'custo_mensal',
    # Contas a receber (vazias)
    'contas_a_receber_abatimento', 'contas_a_receber_tipos',
    # Outros (0 registros)
    'lead_time_fornecedor', 'plano_mestre_producao',
    'portal_configuracoes', 'portal_tenda_agendamentos',
    'portal_tenda_local_entrega_depara', 'portal_tenda_produto_depara_ean',
    'tipo_carga', 'vale_pallets',
}

# =====================================================================
# TABELAS IRRELEVANTES PARA CONSULTAS ANALÍTICAS
# Têm dados em produção mas não são alvo de perguntas analíticas.
# Excluídas para reduzir ruído no catálogo do LLM.
# Revisão: 2026-02-01 (curadoria manual pelo usuário)
# =====================================================================
IRRELEVANT_TABLES = {
    # Logística — tabelas auxiliares/histórico sem valor analítico
    'alertas_separacao_cotada', 'pre_separacao_item',
    'historico_pedidos', 'historico_data_prevista',
    'faturamento_parcial_justificativa', 'inconsistencia_faturamento',
    'relatorio_faturamento_importado',
    # Fretes — tabelas auxiliares (conta corrente, cotações, histórico)
    'conta_corrente_transportadoras', 'cotacao_itens', 'cotacoes',
    'historico_tabelas_frete',
    # Financeiro — lotes/headers (itens mantidos), logs, pendências
    'baixa_pagamento_lote', 'baixa_titulo_lote',
    'cnab_retorno_lote', 'extrato_lote',
    'pendencias_financeiras_nf', 'log_permissao_comercial',
    # Cadastros — dados de cliente já estão em carteira/contas_a_receber
    'cadastro_cliente',
}

# =====================================================================
# TABELAS CORE — Mantidas no schema.json manual com regras de negócio
# curadas à mão. O catálogo referencia-as mas o schema detalhado
# delas vem do core_schema.json (o schema.json original renomeado).
# =====================================================================
CORE_TABLES = {
    'carteira_principal', 'separacao', 'movimentacao_estoque',
    'programacao_producao', 'cadastro_palletizacao', 'faturamento_produto',
    'embarques', 'embarque_itens', 'saldo_standby',
}

# =====================================================================
# MAPA DE DESCRIÇÕES — Descrições curtas curadas para o catálogo
# Quando não existe aqui, usa docstring da classe ou gera automático
# =====================================================================
TABLE_DESCRIPTIONS = {
    # Core (já no schema.json)
    'carteira_principal': 'Pedidos com saldo pendente. Fonte da verdade para demanda.',
    'separacao': 'Itens separados para expedição. Projeta saídas de estoque.',
    'movimentacao_estoque': 'Movimentos de estoque: entradas, saídas, ajustes, produção.',
    'programacao_producao': 'Produção programada por data e linha.',
    'cadastro_palletizacao': 'Cadastro de produtos com peso, pallet, conversões.',
    'faturamento_produto': 'NFs emitidas por produto. Registros de faturamento.',
    'embarques': 'Embarques que agrupam separações para transporte.',
    'embarque_itens': 'Itens individuais dentro de um embarque.',
    'saldo_standby': 'Pedidos em espera: saldo, comercial ou PCP.',
    # Financeiro
    'contas_a_receber': 'Títulos a receber de clientes. Dados do Odoo enriquecidos.',
    'contas_a_receber_abatimento': 'Abatimentos aplicados a títulos a receber.',
    'contas_a_receber_tipos': 'Tipos de conta a receber (boleto, depósito, etc.).',
    'contas_a_receber_snapshot': 'Snapshots históricos de contas a receber.',
    'contas_a_receber_reconciliacao': 'Reconciliações de contas a receber.',
    'contas_a_pagar': 'Títulos a pagar para fornecedores.',
    'liberacao_antecipacao': 'Liberações de antecipação de pagamento.',
    'mapeamento_tipo_odoo': 'Mapeamento de tipos de documento Odoo → sistema.',
    'baixa_titulo_lote': 'Lotes de baixa de títulos a receber.',
    'baixa_titulo_item': 'Itens individuais de baixa de título.',
    'baixa_pagamento_lote': 'Lotes de pagamento para baixa.',
    'baixa_pagamento_item': 'Itens individuais de pagamento.',
    'extrato_lote': 'Lotes de extrato bancário importados.',
    'extrato_item': 'Linhas individuais de extrato bancário.',
    'extrato_item_titulo': 'Vínculo entre extrato bancário e título.',
    'cnab_retorno_lote': 'Lotes de retorno CNAB bancário.',
    'cnab_retorno_item': 'Itens individuais de retorno CNAB.',
    'pendencias_financeiras_nf': 'Pendências financeiras vinculadas a NFs.',
    'comprovante_pagamento_boleto': 'Comprovantes de pagamento de boletos.',
    'lancamento_comprovante': 'Lançamentos de comprovantes financeiros.',
    'correcao_data_nf_credito': 'Correções de data de NFs de crédito.',
    # Fretes
    'fretes': 'Fretes contratados para embarques. Valores e transportadoras.',
    'faturas_frete': 'Faturas de frete emitidas por transportadoras.',
    'despesas_extras': 'Despesas extras de frete (estadia, pedágio, etc.).',
    'conta_corrente_transportadoras': 'Conta corrente com transportadoras.',
    'aprovacoes_frete': 'Aprovações de fretes por alçada.',
    'fretes_lancados': 'Fretes lançados no Odoo.',
    'conhecimento_transporte': 'CT-es (Conhecimento de Transporte Eletrônico).',
    # Devoluções
    'nf_devolucao': 'NFs de devolução recebidas.',
    'nf_devolucao_linha': 'Linhas/itens de NF de devolução.',
    'nf_devolucao_nf_referenciada': 'NFs referenciadas em devoluções.',
    'ocorrencia_devolucao': 'Ocorrências/motivos de devolução.',
    'frete_devolucao': 'Fretes de devoluções.',
    'contagem_devolucao': 'Contagens de itens devolvidos.',
    'anexo_ocorrencia': 'Anexos de ocorrências (fotos, docs).',
    'depara_produto_cliente': 'De-Para de código produto ↔ cliente.',
    'descarte_devolucao': 'Registros de descarte de devoluções.',
    'descarte_item': 'Itens individuais de descarte.',
    # Recebimento
    'validacao_fiscal_dfe': 'Validação fiscal de DFe (NF-e entrada).',
    'validacao_nf_po_dfe': 'Match de NF de compra × PO no Odoo.',
    'match_nf_po_item': 'Itens do match NF × PO.',
    'match_nf_po_alocacao': 'Alocação de quantidades NF × PO.',
    'divergencia_nf_po': 'Divergências encontradas NF × PO.',
    'divergencia_fiscal': 'Divergências fiscais detectadas.',
    'perfil_fiscal_produto_fornecedor': 'Perfil fiscal produto × fornecedor.',
    'cadastro_primeira_compra': 'Cadastro de primeira compra.',
    'ncm_ibscbs_validado': 'NCMs validados contra IBSCBS.',
    'pendencia_fiscal_ibscbs': 'Pendências fiscais IBSCBS.',
    'produto_fornecedor_depara': 'De-Para produto × fornecedor.',
    'recebimento_fisico': 'Recebimentos físicos de materiais.',
    'recebimento_lote': 'Lotes de recebimento físico.',
    'recebimento_quality_check': 'Quality checks de recebimento.',
    'picking_recebimento': 'Pickings de recebimento (Odoo).',
    'picking_recebimento_produto': 'Produtos por picking de recebimento.',
    'picking_recebimento_move_line': 'Move lines de picking de recebimento.',
    'picking_recebimento_quality_check': 'Quality checks de picking.',
    # Rastreamento
    'rastreamento_embarques': 'Rastreamento GPS de embarques.',
    'pings_gps': 'Pings GPS de veículos.',
    'logs_rastreamento': 'Logs de rastreamento.',
    'configuracao_rastreamento': 'Configurações de rastreamento.',
    'entregas_rastreadas': 'Entregas com rastreamento ativo.',
    'entregas_monitoradas': 'Monitoramento de entregas com status e ocorrências.',
    'agendamentos_entrega': 'Agendamentos de entrega.',
    'eventos_entrega': 'Eventos de entrega (tentativa, sucesso, falha).',
    'custos_extra_entrega': 'Custos extras de entrega.',
    'logs_entrega': 'Logs de entrega.',
    'comentarios_nf': 'Comentários em notas fiscais.',
    'historico_data_prevista': 'Histórico de datas previstas.',
    'arquivo_entrega': 'Arquivos anexados a entregas.',
    # Cotação
    'cotacoes': 'Cotações de frete para embarques.',
    'cotacao_itens': 'Itens de cotação de frete.',
    # Transportadoras
    'transportadoras': 'Cadastro de transportadoras com dados logísticos e financeiros.',
    'veiculos': 'Frota de veículos por transportadora.',
    'cidades_atendidas': 'Cidades atendidas por transportadora com lead time.',
    # Localidades
    'cidades': 'Cadastro de cidades do Brasil.',
    'cadastro_rota': 'Cadastro de rotas logísticas por UF.',
    'cadastro_sub_rota': 'Sub-rotas por cidade.',
    # Estoque
    'unificacao_codigos': 'Unificação de códigos de produto.',
    'grupo_empresarial': 'Grupos empresariais.',
    # Faturamento extra
    'relatorio_faturamento_importado': 'Relatórios de faturamento importados.',
    'inconsistencia_faturamento': 'Inconsistências encontradas no faturamento.',
    'faturamento_parcial_justificativa': 'Justificativas de faturamento parcial.',
    # Pedidos
    'pedidos': 'Pedidos do TagPlus importados.',
    'cadastro_cliente': 'Cadastro de clientes.',
    'pre_separacao_item': 'Itens de pré-separação.',
    'controle_cruzado_separacao': 'Controle cruzado de separações.',
    # Carteira
    'carteira_copia': 'Cópia de segurança da carteira.',
    # Portaria
    'motoristas': 'Cadastro de motoristas.',
    'controle_portaria': 'Controle de entrada/saída na portaria.',
    # Notificações
    'alerta_notificacoes': 'Alertas e notificações do sistema.',
    'webhook_configs': 'Configurações de webhooks.',
    # BI
    'bi_frete_agregado': 'BI: fretes agregados por período.',
    'bi_despesa_detalhada': 'BI: despesas detalhadas.',
    'bi_performance_transportadora': 'BI: performance de transportadoras.',
    'bi_analise_regional': 'BI: análise regional de fretes.',
    'bi_indicador_mensal': 'BI: indicadores mensais.',
    # Tabelas de preço/frete
    'tabelas_frete': 'Tabelas de preço de frete.',
    'historico_tabelas_frete': 'Histórico de tabelas de frete.',
    # Custeio
    'custo_mensal': 'Custos mensais operacionais.',
    'custo_considerado': 'Custos considerados para análise.',
    'custo_frete': 'Custos de frete calculados.',
    'parametro_custeio': 'Parâmetros de custeio.',
    # Comercial
    'permissao_comercial': 'Permissões comerciais por vendedor.',
    'log_permissao_comercial': 'Logs de permissões comerciais.',
    # Alertas
    'alertas_separacao_cotada': 'Alertas de separações cotadas.',
    # Email
    'emails_anexados': 'Emails anexados a documentos.',
    # Validação pedidos
    'tabela_rede_precos': 'Tabela de preços por rede.',
    'regiao_tabela_rede': 'Regiões por tabela de rede.',
    # Integrações Odoo
    'registro_pedido_odoo': 'Registro de pedidos enviados ao Odoo.',
    'pedido_importacao_temp': 'Pedidos temporários para importação.',
    'lancamento_frete_odoo_auditoria': 'Auditoria de lançamentos de frete no Odoo.',
    # Contatos
    'contatos_agendamento': 'Contatos para agendamento de entrega.',
    # Vendedores / Equipes
    'vendedor': 'Cadastro de vendedores.',
    'equipe_vendas': 'Equipes de vendas.',
    'user_vendedor': 'Vínculo usuário ↔ vendedor.',
    'user_equipe': 'Vínculo usuário ↔ equipe.',
    # Log integração
    'log_integracao': 'Logs de integrações com sistemas externos.',
    # NF TagPlus
    'nf_pendente_tagplus': 'NFs pendentes no TagPlus.',
}


# =====================================================================
# FUNÇÕES DE EXTRAÇÃO
# =====================================================================

def get_sqlalchemy_type_str(col_type) -> str:
    """Converte tipo SQLAlchemy para string legível."""
    type_name = type(col_type).__name__

    type_map = {
        'String': lambda t: f"varchar({t.length})" if t.length else "varchar",
        'Integer': lambda t: "integer",
        'BigInteger': lambda t: "bigint",
        'SmallInteger': lambda t: "smallint",
        'Float': lambda t: "float",
        'Numeric': lambda t: f"numeric({t.precision},{t.scale})" if t.precision else "numeric",
        'Boolean': lambda t: "boolean",
        'Text': lambda t: "text",
        'Date': lambda t: "date",
        'DateTime': lambda t: "timestamp",
        'Time': lambda t: "time",
        'JSON': lambda t: "json",
        'LargeBinary': lambda t: "bytea",
        'Enum': lambda t: f"enum({','.join(t.enums)})" if hasattr(t, 'enums') else "enum",
    }

    converter = type_map.get(type_name)
    if converter:
        try:
            return converter(col_type)
        except Exception:
            return type_name.lower()

    return type_name.lower()


def _clean_description(desc: str) -> str:
    """
    Limpa uma descrição extraída do source code.
    Remove emojis, marcadores de debug, separadores visuais, etc.
    Retorna string vazia se a descrição não tiver valor informativo.
    """
    if not desc:
        return ""

    # Limpar emojis unicode (✅📋🔍⭐🆔👥📦📊💰🏷️💳🏠📅🔄🗑️📸🛡️←→ etc.)
    desc = re.sub(
        r'[\U0001F000-\U0001FFFF'   # Supplemental Symbols
        r'\u2190-\u21FF'             # Arrows (←→↑↓)
        r'\u2600-\u27BF'             # Misc Symbols + Dingbats
        r'\u2B50\u2705\u26A0'        # Star, Check, Warning
        r'\u2714\u2716\u2728'        # Check, X, Sparkles
        r'\u274C\u274E'              # Cross marks
        r']+\s*', '', desc
    )

    # Separadores visuais (===, ----, ****)
    if re.match(r'^[=\-*_]{3,}', desc):
        return ""

    # Marcadores de debug (<--- AQUI, TODO, FIXME, HACK, XXX)
    if re.search(r'<-{2,}|TODO\b|FIXME\b|HACK\b|XXX\b', desc, re.IGNORECASE):
        return ""

    # Títulos de seção ALL-CAPS puros (ex: "DADOS DO PEDIDO", "CAMPOS DE VALOR")
    if re.match(r'^[A-ZÁÉÍÓÚÂÊÔ\s]{5,}$', desc):
        return ""

    # Prefixos ALL-CAPS sem valor informativo (patterns mais longos primeiro)
    desc = re.sub(
        r'^(NOVOS?\s+CAMPOS?\s*(?:DE\s+\w+)?|NOVO|ADICIONADO|REMOVIDO|ALTERADO)\s*:?\s*',
        '', desc, flags=re.IGNORECASE
    )

    # Metadata técnica (Constraint, Index, Unique, Migration)
    if re.match(r'^(Constraint|Index|Unique|Migration|FK\s|PK\s)', desc, re.IGNORECASE):
        return ""

    desc = desc.strip()
    if desc and len(desc) > 3:
        return desc[:120]
    return ""


def extract_field_description(model_class, field_name: str) -> str:
    """
    Tenta extrair descrição do campo a partir de:
    1. info dict do Column
    2. doc/comment do Column
    3. Comentário inline no source code (processado linha por linha)
    """
    # Tentar info dict
    col = model_class.__table__.columns.get(field_name)
    if col is not None:
        info = getattr(col, 'info', {})
        if isinstance(info, dict) and 'description' in info:
            return _clean_description(info['description'])

        comment = getattr(col, 'comment', None)
        if comment:
            return _clean_description(comment)

    # Tentar extrair comentário inline do source code (LINHA POR LINHA)
    try:
        source = inspect.getsource(model_class)
        # Processar linha por linha para evitar cruzar newlines
        # BUG FIX: \s* no regex antigo cruzava \n, capturando headers de seção
        for line in source.splitlines():
            # Procurar: field_name = db.Column(...) # Descrição
            # Word boundary ((?<![a-zA-Z_])) evita match parcial
            # ex: 'cliente' não matcha em 'qtd_pallet_cliente'
            pattern = rf'(?<![a-zA-Z_]){re.escape(field_name)}\s*=\s*db\.Column\([^)]*\)[^\n#]*#\s*(.+)'
            match = re.search(pattern, line)
            if match:
                desc = _clean_description(match.group(1).strip())
                if desc:
                    return desc
    except (TypeError, OSError):
        pass

    return ""


def extract_class_docstring(model_class) -> str:
    """Extrai docstring da classe do modelo."""
    doc = inspect.getdoc(model_class)
    if doc:
        # Primeira linha significativa
        for line in doc.split('\n'):
            line = line.strip()
            if line and len(line) > 10:
                return line[:200]
    return ""


def extract_table_schema(table_name: str, table, model_class=None) -> dict:
    """Extrai schema detalhado de uma tabela SQLAlchemy."""
    fields = []
    foreign_keys = []

    for col in table.columns:
        field = {
            'name': col.name,
            'type': get_sqlalchemy_type_str(col.type),
        }

        # Descrição
        desc = ""
        if col.primary_key:
            # Primary key sempre tem descrição fixa
            desc = "Primary key"
        elif model_class:
            desc = extract_field_description(model_class, col.name)
        if not desc:
            # Gerar descrição automática
            if col.name.endswith('_id') and col.foreign_keys:
                fk = list(col.foreign_keys)[0]
                desc = f"FK → {fk.column.table.name}.{fk.column.name}"
            elif col.name in ('created_at', 'criado_em'):
                desc = "Data de criação"
            elif col.name in ('updated_at', 'atualizado_em'):
                desc = "Última atualização"
            elif col.name == 'ativo':
                desc = "True = registro ativo"
        if desc:
            field['description'] = desc

        # Nullable
        if not col.nullable and not col.primary_key:
            field['nullable'] = False

        # Default
        if col.default is not None:
            default_val = col.default
            if hasattr(default_val, 'arg'):
                arg = default_val.arg
                if isinstance(arg, (str, int, float, bool)):
                    field['default'] = arg

        fields.append(field)

        # Foreign keys
        for fk in col.foreign_keys:
            foreign_keys.append({
                'column': col.name,
                'references': f"{fk.column.table.name}.{fk.column.name}"
            })

    # Descrição da tabela
    description = TABLE_DESCRIPTIONS.get(table_name, "")
    if not description and model_class:
        description = extract_class_docstring(model_class)
    if not description:
        description = f"Tabela {table_name}"

    # Unique constraints
    unique_constraints = []
    for constraint in table.constraints:
        from sqlalchemy import UniqueConstraint
        if isinstance(constraint, UniqueConstraint) and constraint.columns:
            cols = [c.name for c in constraint.columns]
            if len(cols) > 1:  # Só compostos
                unique_constraints.append(cols)

    # Índices
    indices = []
    for idx in table.indexes:
        cols = [c.name for c in idx.columns]
        if cols:
            indices.append({
                'name': idx.name,
                'columns': cols,
                'unique': idx.unique
            })

    schema = {
        'name': table_name,
        'description': description,
        'fields': fields,
    }

    if foreign_keys:
        schema['foreign_keys'] = foreign_keys
    if unique_constraints:
        schema['unique_constraints'] = unique_constraints
    if indices:
        schema['indices'] = indices

    return schema


def generate_catalog_entry(table_name: str, table, model_class=None) -> dict:
    """Gera entrada leve do catálogo: nome + descrição + 3 campos-chave."""
    description = TABLE_DESCRIPTIONS.get(table_name, "")
    if not description and model_class:
        description = extract_class_docstring(model_class)
    if not description:
        description = f"Tabela {table_name}"

    # Selecionar 3 campos-chave (excluindo id, created_at, etc.)
    skip_fields = {'id', 'created_at', 'updated_at', 'criado_em', 'atualizado_em', 'ativo'}
    key_fields = []
    for col in table.columns:
        if col.name in skip_fields:
            continue
        if col.primary_key:
            continue
        key_fields.append(col.name)
        if len(key_fields) >= 3:
            break

    return {
        'name': table_name,
        'description': description,
        'key_fields': key_fields,
    }


def extract_relationships(metadata) -> list:
    """Extrai relacionamentos FK entre tabelas."""
    relationships = []
    seen = set()

    for table_name, table in sorted(metadata.tables.items()):
        if table_name in BLOCKED_TABLES:
            continue

        for col in table.columns:
            for fk in col.foreign_keys:
                ref_table = fk.column.table.name
                if ref_table in BLOCKED_TABLES:
                    continue

                key = f"{table_name}.{col.name}->{ref_table}.{fk.column.name}"
                if key not in seen:
                    seen.add(key)
                    relationships.append({
                        'from_table': table_name,
                        'from_column': col.name,
                        'to_table': ref_table,
                        'to_column': fk.column.name,
                    })

    return relationships


# =====================================================================
# IMPORTAÇÃO DOS MODELOS
# =====================================================================

def import_all_models():
    """Importa todos os modelos SQLAlchemy e retorna metadata + model_map."""

    # Importar app para inicializar SQLAlchemy metadata
    os.environ.setdefault('FLASK_ENV', 'development')

    from app import create_app, db

    app = create_app()

    with app.app_context():
        # Modelo -> tabela mapping
        model_map = {}  # table_name -> model_class

        # Importar todos os módulos de modelos
        model_modules = [
            'app.agente.models',
            'app.auth.models',
            'app.bi.models',
            'app.cadastros_agendamento.models',
            'app.carteira.models',
            'app.carteira.models_alertas',
            'app.comercial.models',
            'app.cotacao.models',
            'app.custeio.models',
            'app.devolucao.models',
            'app.embarques.models',
            'app.estoque.models',
            'app.faturamento.models',
            'app.financeiro.models',
            'app.financeiro.models_comprovante',
            'app.financeiro.models_correcao_datas',
            'app.fretes.email_models',
            'app.fretes.models',
            'app.integracoes.tagplus.models',
            'app.localidades.models',
            'app.manufatura.models',
            'app.monitoramento.models',
            'app.motochefe.models.cadastro',
            'app.motochefe.models.financeiro',
            'app.motochefe.models.logistica',
            'app.motochefe.models.operacional',
            'app.motochefe.models.produto',
            'app.motochefe.models.vendas',
            'app.notificacoes.models',
            'app.pallet.models.credito',
            'app.pallet.models.documento',
            'app.pallet.models.nf_remessa',
            'app.pallet.models.nf_solucao',
            'app.pallet.models.solucao',
            'app.pallet.models.vale_pallet',
            'app.pedidos.integracao_odoo.models',
            'app.pedidos.models',
            'app.pedidos.validacao.models',
            'app.permissions.models',
            'app.portal.atacadao.models',
            'app.portal.models',
            'app.portal.models_fila_sendas',
            'app.portal.sendas.models',
            'app.portal.sendas.models_planilha',
            'app.portal.tenda.models',
            'app.portaria.models',
            'app.producao.models',
            'app.rastreamento.models',
            'app.recebimento.models',
            'app.separacao.models',
            'app.tabelas.models',
            'app.transportadoras.models',
            'app.veiculos.models',
            'app.vinculos.models',
        ]

        for module_name in model_modules:
            try:
                mod = importlib.import_module(module_name)

                # Mapear classes que são db.Model
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if hasattr(obj, '__tablename__') and hasattr(obj, '__table__'):
                        table_name = obj.__tablename__
                        model_map[table_name] = obj

            except Exception as e:
                print(f"⚠️  Erro ao importar {module_name}: {e}")

        return db.metadata, model_map


# =====================================================================
# GERAÇÃO DOS ARQUIVOS
# =====================================================================

def generate_all(stats_only=False):
    """Gera todos os schemas."""
    print("🔍 Importando modelos SQLAlchemy...")
    metadata, model_map = import_all_models()

    all_tables = sorted(metadata.tables.keys())
    excluded = BLOCKED_TABLES | DEAD_TABLES | IRRELEVANT_TABLES
    allowed_tables = [t for t in all_tables if t not in excluded]
    blocked = [t for t in all_tables if t in BLOCKED_TABLES]
    dead = [t for t in all_tables if t in DEAD_TABLES]
    irrelevant = [t for t in all_tables if t in IRRELEVANT_TABLES]

    print(f"\n📊 Estatísticas:")
    print(f"   Total de tabelas no metadata: {len(all_tables)}")
    print(f"   Tabelas bloqueadas (auth/agent): {len(blocked)}")
    print(f"   Tabelas mortas (0 registros): {len(dead)}")
    print(f"   Tabelas irrelevantes (curadoria manual): {len(irrelevant)}")
    print(f"   Tabelas permitidas: {len(allowed_tables)}")
    print(f"   Tabelas core (schema manual): {len(CORE_TABLES)}")
    print(f"   Tabelas para schema auto-gerado: {len(allowed_tables) - len(CORE_TABLES)}")
    print(f"   Models com classe Python mapeada: {len(model_map)}")

    if stats_only:
        print(f"\n📋 Tabelas bloqueadas (auth/agent):")
        for t in sorted(blocked):
            print(f"   ❌ {t}")
        print(f"\n📋 Tabelas mortas (0 registros):")
        for t in sorted(dead):
            print(f"   💀 {t}")
        print(f"\n📋 Tabelas irrelevantes (curadoria manual):")
        for t in sorted(irrelevant):
            print(f"   🚫 {t}")
        print(f"\n📋 Tabelas core (schema.json manual):")
        for t in sorted(CORE_TABLES):
            print(f"   ⭐ {t}")
        print(f"\n📋 Tabelas não-core permitidas:")
        for t in sorted(allowed_tables):
            if t not in CORE_TABLES:
                desc = TABLE_DESCRIPTIONS.get(t, "sem descrição")
                has_model = "✅" if t in model_map else "❓"
                print(f"   {has_model} {t}: {desc}")
        return

    # Garantir diretórios
    os.makedirs(TABLES_DIR, exist_ok=True)

    # 1. Gerar schemas individuais por tabela
    print(f"\n📝 Gerando schemas individuais...")
    tables_generated = 0
    for table_name in allowed_tables:
        table = metadata.tables[table_name]
        model_class = model_map.get(table_name)

        schema = extract_table_schema(table_name, table, model_class)

        output_path = os.path.join(TABLES_DIR, f"{table_name}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

        tables_generated += 1

    print(f"   ✅ {tables_generated} schemas gerados em schemas/tables/")

    # 2. Gerar catálogo
    print(f"\n📝 Gerando catálogo...")
    catalog = {
        'version': '2.0.0',
        'database': 'postgresql',
        'notas_gerais': [
            'Todos os valores monetários em BRL (R$)',
            'Datas no formato YYYY-MM-DD no banco',
            'Campos Boolean: True/False (PostgreSQL)',
            'Registros ativos: ativo = True (quando o campo existe)',
            'Para usar campos detalhados, consultar schemas/tables/{tabela}.json'
        ],
        'tabelas_bloqueadas': sorted(BLOCKED_TABLES | DEAD_TABLES | IRRELEVANT_TABLES),
        'total_tabelas': len(allowed_tables),
        'tabelas': []
    }

    for table_name in allowed_tables:
        table = metadata.tables[table_name]
        model_class = model_map.get(table_name)
        entry = generate_catalog_entry(table_name, table, model_class)
        catalog['tabelas'].append(entry)

    catalog_path = os.path.join(SCHEMAS_DIR, 'catalog.json')
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    catalog_size = os.path.getsize(catalog_path)
    print(f"   ✅ catalog.json gerado ({catalog_size:,} bytes, {len(catalog['tabelas'])} tabelas)")

    # 3. Gerar relationships
    print(f"\n📝 Gerando mapa de relacionamentos...")
    relationships = extract_relationships(metadata)

    rel_data = {
        'version': '2.0.0',
        'total_relationships': len(relationships),
        'relationships': relationships,
    }

    rel_path = os.path.join(SCHEMAS_DIR, 'relationships.json')
    with open(rel_path, 'w', encoding='utf-8') as f:
        json.dump(rel_data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ relationships.json gerado ({len(relationships)} FKs)")

    # 4. Resumo final
    total_fields = sum(
        len(metadata.tables[t].columns) for t in allowed_tables
    )
    print(f"\n{'='*60}")
    print(f"✅ GERAÇÃO COMPLETA")
    print(f"   Tabelas: {len(allowed_tables)}")
    print(f"   Campos totais: {total_fields}")
    print(f"   Relacionamentos: {len(relationships)}")
    print(f"   Arquivos gerados:")
    print(f"      schemas/catalog.json ({catalog_size:,} bytes)")
    print(f"      schemas/relationships.json")
    print(f"      schemas/tables/*.json ({tables_generated} arquivos)")
    print(f"{'='*60}")


# =====================================================================
# MAIN
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Gera schemas JSON a partir dos modelos SQLAlchemy'
    )
    parser.add_argument(
        '--stats', action='store_true',
        help='Apenas mostrar estatísticas, sem gerar arquivos'
    )
    args = parser.parse_args()

    generate_all(stats_only=args.stats)


if __name__ == '__main__':
    main()
