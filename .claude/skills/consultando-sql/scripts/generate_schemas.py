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
    # Agente (tabelas internas — não expor ao LLM SQL)
    'agent_sessions', 'agent_memories', 'agent_memory_versions',
    'agent_memory_embeddings', 'session_turn_embeddings',
    'table_catalog_embeddings',  # S1: infra de busca semantica de tabela
    'agent_skill_effectiveness',  # infra do agente (efetividade de skills)
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
    # Fretes — tabelas auxiliares (histórico)
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
    'movimentacao_estoque': 'Movimentos de estoque: entradas, saidas, ajustes, producao. Historico: ORDER BY data_movimentacao DESC. Origem do estoque: GROUP BY tipo_movimentacao. Estoque parado: MAX(data_movimentacao WHERE tipo=SAIDA) < 30 dias + saldo > 0. Giro: saidas_periodo / saldo_medio.',
    'programacao_producao': 'Produção programada por data e linha.',
    'cadastro_palletizacao': 'Cadastro de produtos com peso, pallet, conversões.',
    'faturamento_produto': 'NFs emitidas por produto. IMPORTANTE: campo origem = num_pedido (link direto pedido->NF). Comparativo mensal: SUM(valor_produto_faturado) GROUP BY DATE_TRUNC(month, data_fatura). Clientes novos: cnpj_cliente NOT IN subquery periodo anterior. Campos: numero_nf, cnpj_cliente, nome_cliente, cod_produto, nome_produto, qtd_faturada, valor_produto_faturado, data_fatura, origem.',
    'embarques': 'Embarques que agrupam separacoes para transporte. Campos: numero (unico), data_embarque, tipo_carga (DIRETA ou FRACIONADA), transportadora_id, peso_total, valor_total, pallet_total, status. Concentracao semanal: EXTRACT(DOW FROM data_embarque). Co-passageiros: JOIN embarque_itens WHERE embarque_id = X.',
    'embarque_itens': 'Itens individuais dentro de um embarque. Campos: embarque_id, separacao_lote_id, cnpj_cliente, cliente, pedido, nota_fiscal, peso, valor, volumes, pallets, uf_destino, cidade_destino. Para co-passageiros: SELECT * FROM embarque_itens WHERE embarque_id = X.',
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
    'fretes': 'Fretes contratados para embarques. 4 tipos de valor: valor_cotado (calculado pela tabela de frete), valor_cte (cobrado pela transportadora no CTe), valor_considerado (validado internamente), valor_pago (efetivamente pago). Para custo real use valor_pago. Divergencia: ABS(valor_cte - valor_cotado). numeros_nfs e campo CSV com NFs do frete. tipo_carga: DIRETA ou FRACIONADA. Pendentes Odoo: status=APROVADO AND lancado_odoo_em IS NULL.',
    'faturas_frete': 'Faturas de frete emitidas por transportadoras.',
    'despesas_extras': 'Despesas extras de frete. tipo_despesa: REENTREGA, TDE, DEVOLUCAO, PERNOITE, DIARIA, COMPLEMENTO DE FRETE, COMPRA/AVARIA, TRANSFERENCIA, DESCARGA, ESTACIONAMENTO, CARRO DEDICADO, ARMAZENAGEM. Para custo de devolucao: tipo_despesa=DEVOLUCAO. Link para NFDevolucao via nfd_id. valor_despesa contem o valor.',
    'conta_corrente_transportadoras': 'Conta corrente com transportadoras. Saldo = SUM(valor_credito) - SUM(valor_debito). tipo_movimentacao: CREDITO, DEBITO, COMPENSACAO. status: ATIVO, COMPENSADO, DESCONSIDERADO. Cada registro vincula a um frete_id.',
    'aprovacoes_frete': 'Aprovações de fretes por alçada.',
    'fretes_lancados': 'Fretes lançados no Odoo.',
    'conhecimento_transporte': 'CT-es (Conhecimento de Transporte Eletrônico).',
    # Devoluções
    'nf_devolucao': 'NFs de devolução recebidas.',
    'nf_devolucao_linha': 'Linhas/itens de NF de devolucao. Produtos devolvidos: GROUP BY codigo_produto_cliente ou codigo_produto_interno para ranking. Campo quantidade (NAO qtd_devolvida). Campos: nfd_id (FK nf_devolucao), codigo_produto_cliente, codigo_produto_interno, quantidade, valor_total.',
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
    'entregas_monitoradas': 'Monitoramento de entregas com status e ocorrencias. Atraso: status_finalizacao IS NULL AND data_entrega_prevista < CURRENT_DATE. Em transito: data_embarque IS NOT NULL AND status_finalizacao IS NULL AND nf_cd=False. Lead time: data_hora_entrega_realizada - data_embarque. Taxa sucesso: COUNT(entregue=True)/COUNT(*). Campos: numero_nf, cnpj_cliente, transportadora, uf, municipio, valor_nf, separacao_lote_id.',
    'agendamentos_entrega': 'Agendamentos de entrega. Reagendamentos: GROUP BY entrega_id HAVING COUNT(*) > N. Campos: entrega_id, data_agendada, hora_agendada, forma_agendamento, status (aguardando, confirmado, etc.).',
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
    'controle_portaria': 'Controle de entrada/saida na portaria da fabrica. Veiculos na fabrica: data_saida IS NULL. Tempo carregamento: hora_saida - hora_entrada. Campos: placa, empresa, tipo_carga (Coleta, Devolucao, etc.), hora_chegada, hora_entrada, hora_saida, data_chegada, data_entrada, data_saida, embarque_id, motorista_id. NOTA: status e property calculada, NAO coluna.',
    # Pallet
    'pallet_creditos': 'Creditos de pallets a receber. Saldo por responsavel: SUM(qtd_saldo) WHERE status IN (PENDENTE, PARCIAL). tipo_responsavel: TRANSPORTADORA ou CLIENTE. Campos: cnpj_responsavel, nome_responsavel, qtd_original, qtd_saldo, status, prazo_dias, data_vencimento, nf_remessa_id.',
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
    # =================================================================
    # Dominio AGENTE — tabelas com JSONB opaco / juncao nao-FK / 2 IDs.
    # Descricoes ricas para o text_to_sql nao gerar query ingenua (vazia).
    # =================================================================
    'agent_adhoc_script': (
        "Pipeline de APRENDIZADO (Fase 2): captura Bash 'substantivo' pos-sessao para "
        "detectar gaps de skill e clusterizar comandos parecidos (cluster_id, tipo_gap). "
        "NAO e' repositorio de recuperacao: command_masked e' MASCARADO (PII) + truncado "
        "(8000c) + filtrado (so inline/heredoc/SQL; exclui scripts de arquivo). Para o "
        "SCRIPT INTEGRO que a sessao rodou, use a tool mcp__sessions__get_session_transcript "
        "(ou claude_session_store), NAO esta tabela."
    ),
    'agent_sessions': (
        "Sessao do agente (1 linha por conversa). session_id = UUID interno nosso. "
        "JSONB 'data' contem as chaves (NAO sao colunas): channel ('web'/'teams'), "
        "sdk_session_id (junta ao transcript cru em claude_session_store), messages "
        "(array do historico produto), subagent_costs.entries (custo por subagente), "
        "forked_from, plan, deliberation_log, s3_archive. JSONB 'summary' contem: "
        "resumo_geral, topicos_abordados, ferramentas_usadas, tarefas_pendentes, "
        "alertas, acoes_usuario, pedidos_mencionados, decisoes_tomadas, perfil_signals. "
        "Filtrar canal: data->>'channel'='teams'. Para o que a sessao EXECUTOU "
        "(Bash/scripts/tools), use a tool mcp__sessions__get_session_transcript em vez "
        "de SQL cru. admin_only."
    ),
    'claude_session_store': (
        "Transcript SDK cru (1 linha por evento JSONL; source-of-truth do conteudo de "
        "sessao). ATENCAO 2 IDs: session_id aqui = sdk_session_id (efemero do CLI), NAO "
        "agent_sessions.session_id. Juncao SEM FK: JOIN agent_sessions a ON "
        "a.data->>'sdk_session_id' = claude_session_store.session_id. subpath='' = "
        "transcript principal; subagentes tem subpath proprio. entry (jsonb) = evento "
        "do SDK; blocos entry->'message'->'content'[*] com type='tool_use' name='Bash' "
        "tem input.command (script executado, INTEGRO). Prefira a tool "
        "mcp__sessions__get_session_transcript a montar esta query a mao."
    ),
    'agent_step': (
        "Telemetria por turno (1 linha por turn). step_uid = '{session_id}:{turn_seq}' "
        "— o numero do turno vem de split_part(step_uid,':',2)::int (NAO ha coluna "
        "turn_seq). session_id e' coluna sem FK: DELETE da sessao NAO apaga os steps "
        "(use LEFT JOIN). outcome_signal (JSONB) tem judge.evidencia (truncado em 500c)."
    ),
    'agent_skill_effectiveness': (
        "Avaliacao pos-sessao de efetividade de skill. action_ref e' string com prefixo: "
        "'memory:<id>' / 'dialogue:<id>' / 'approval:<id>' (parseie o prefixo p/ saber a "
        "tabela). anchor_msg_id referencia agent_sessions.data->'messages'[].id (sem FK). "
        "evidencia_json e' mascarado (PII) e truncado — nao e' a conversa integra."
    ),
    'agent_memories': (
        "Memorias persistentes do agente. Para memorias ESTRUTURADAS (heuristica/"
        "armadilha/protocolo/correcao) a FONTE DE VERDADE e' o JSONB 'meta' (kind, "
        "dominio, nivel, when, do, criterios, titulo); a coluna 'content' e' DERIVADA "
        "de meta (NAO filtrar por content). Filtre por meta->>'kind' e meta->>'dominio'. "
        "is_cold=true = memoria fria (excluir de busca operacional)."
    ),
    'agent_improvement_dialogue': (
        "Dialogo de melhoria Agent SDK <-> Claude Code (D8 + real-time). evidence_json "
        "(JSONB) e source_session_ids (array) guardam o contexto. suggestion_key e' a "
        "chave de dedup; status: proposed/closed/etc."
    ),
    'agente_artifacts': (
        "Artefatos HTML gerados pelo agente. O conteudo HTML NAO esta no banco: s3_key "
        "aponta o bundle no S3 (acesse via presigned URL)."
    ),
    'teams_tasks': (
        "Tarefas do canal Teams. pending_questions, conversation_reference e resposta_card "
        "sao JSON. pending_question_session_id e' a ponte (sem FK) para "
        "agent_sessions.session_id."
    ),
}


# =====================================================================
# SERIALIZAÇÃO CANÔNICA E ESCRITA IDEMPOTENTE (subsistema S0)
# =====================================================================
# Causa raiz da poluição de git (Passo 0 do MASTER text-to-sql): a serialização
# iterava coleções que em SQLAlchemy são `set` — table.indexes, table.constraints
# e col.foreign_keys — cuja ordem de iteração varia entre processos Python. Logo,
# tables/*.json mudavam entre duas execuções SEM mudança de modelo, poluindo o git.
# (catalog.json/relationships.json já eram estáveis por iterarem sorted(...).)
# Correção: ordenar de forma canônica (nas funções de extração) + gravar só quando
# o conteúdo muda (write-if-changed), com a MESMA serialização p/ gravar e comparar.

def _dump_canonical(obj) -> str:
    """Serialização JSON canônica e determinística (usada p/ gravar E p/ comparar).

    NÃO usa sort_keys: preserva a ordem das colunas do modelo dentro de cada
    tabela (decisão 3 do plano S0). Newline final fixo (git-friendly).
    """
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _read_text(path: str):
    """Lê o conteúdo de `path` (UTF-8) ou retorna None se não existir."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None


def _write_if_changed(path: str, content_str: str) -> bool:
    """Escreve `content_str` em `path` somente se diferir do conteúdo atual.

    Retorna True se escreveu (arquivo novo ou alterado), False se já estava igual.
    É o que mantém o git limpo entre execuções idempotentes.
    """
    if _read_text(path) == content_str:
        return False
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content_str)
    return True


def _fk_ref(fk) -> str:
    """Chave canônica de uma ForeignKey: 'tabela.coluna' do alvo (ordena sets)."""
    return f"{fk.column.table.name}.{fk.column.name}"


# Tabelas que EXISTEM no banco PROD mas NAO tem modelo ORM no codigo (verificado
# via MCP Render em 2026-06-07): o schema fica "congelado" no disco e o gerador
# (que deriva do metadata ORM) nao as cobre. NUNCA apagar como "orfa" — sao vivas:
#   claude_session_store          67.216 linhas (gerenciada pelo SDK Agent)
#   carvia_sessoes_cotacao             2 linhas (sem modelo ORM atual)
#   carvia_sessao_demandas             2 linhas (sem modelo ORM atual)
#   carvia_aprovacoes_subcontrato      0 linhas (vazia, sem modelo)
# teams_tasks NAO entra: tem modelo (app/teams/models.py) e passou a ser gerada
# via auto-descoberta (_discover_model_modules).
ORFAOS_VIVOS_PRESERVAR = {
    'claude_session_store',
    'carvia_sessoes_cotacao',
    'carvia_sessao_demandas',
    'carvia_aprovacoes_subcontrato',
}


def _find_orphan_schemas(tables_dir: str, generated_table_names) -> list:
    """Schemas em tables/<t>.json sem tabela correspondente no metadata gerado.

    ATENÇÃO: um órfão pode ser uma tabela VIVA cujo módulo de modelo não está na
    lista de import (descoberto no Passo 0 do S0). Por isso a remoção NUNCA é
    automática — ver _resolve_orphans_to_delete.
    """
    generated = set(generated_table_names)
    try:
        existing = {f[:-5] for f in os.listdir(tables_dir) if f.endswith('.json')}
    except FileNotFoundError:
        return []
    return sorted(existing - generated)


def _resolve_orphans_to_delete(orphan_files, import_complete: bool, do_prune: bool) -> list:
    """Decide quais órfãos remover. Salvaguardas INVIOLÁVEIS (S0):

    1. Só remove com `do_prune` (flag --prune-orphans explícita). O fluxo
       automático/hook NUNCA apaga — apenas loga.
    2. Mesmo com a flag, só remove com `import_complete` (zero ImportError).
       Import parcial NUNCA apaga: um models.py quebrado no meio de uma edição
       faria o hook apagar schemas válidos.
    3. NUNCA remove tabela em ORFAOS_VIVOS_PRESERVAR: existe no banco PROD sem
       modelo ORM (apagar tiraria do agente uma tabela real).
    """
    if not do_prune or not import_complete:
        return []
    return [o for o in orphan_files if o not in ORFAOS_VIVOS_PRESERVAR]


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
    """Extrai docstring PROPRIA da classe do modelo.

    Usa `__doc__` direto, NAO `inspect.getdoc` — este ultimo herda a docstring da
    superclasse `db.Model` via MRO quando a classe nao tem docstring propria,
    injetando "The base class of the :attr:`.SQLAlchemy.Model` declarative model
    class." como "descricao" da tabela. Bug pre-existente exposto pela
    auto-descoberta (2026-06-07): mais classes mapeadas -> mais tabelas sem
    docstring caindo no lixo herdado. Com `__doc__`, classe sem docstring -> None
    -> fallback "Tabela X" (correto).
    """
    doc = model_class.__doc__
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
                fk = sorted(col.foreign_keys, key=_fk_ref)[0]
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

        # Foreign keys — ordenar a iteração do set p/ determinismo
        # (a ordem ENTRE colunas é preservada pelo loop externo de table.columns).
        for fk in sorted(col.foreign_keys, key=_fk_ref):
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
    # table.constraints é set -> ordenar a LISTA de constraints p/ determinismo
    # (a ordem das colunas DENTRO de cada constraint é semântica e preservada).
    unique_constraints.sort(key=lambda cols: tuple(cols))

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
    # CAUSA RAIZ (Passo 0): table.indexes é set -> ordenar a LISTA de índices p/
    # determinismo (a ordem das colunas DENTRO de cada índice é semântica).
    indices.sort(key=lambda i: ((i.get('name') or ''), tuple(i['columns'])))

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


# =====================================================================
# CATÁLOGO — key_fields por relevância + domínio (subsistema S1)
# =====================================================================
# Achado N2 (MASTER text-to-sql): a heurística antiga usava as 3 PRIMEIRAS
# colunas como "chave" (quase sempre id + 2 FKs) — lixo semântico p/ ESCOLHER a
# tabela. Esta versão seleciona o conjunto MÍNIMO útil: chaves de negócio
# (num_pedido, cod_produto, cnpj...) + 1-3 filtros (status, 1 data, uf), sem id
# técnico nem auditoria. Tudo determinístico (compatível com idempotência S0).

# Campos nunca usados como key_field (técnicos / auditoria).
KEY_FIELD_SKIP = {
    'id', 'created_at', 'updated_at', 'criado_em', 'atualizado_em',
    'ativo', 'created_by', 'updated_by', 'criado_por', 'atualizado_por',
    'data_criacao', 'data_atualizacao', 'importado_em', 'importado_por',
}

# Chaves de negócio "fortes" — identificam a tabela de imediato. A ORDEM é a
# prioridade de SELEÇÃO (não a ordem da coluna): garante que cod_produto entre
# antes de uma chave secundária em tabelas com muitos ids (ex: separacao).
_STRONG_KEYS_ORDER = [
    'num_pedido', 'cod_produto', 'numero_nf', 'cnpj_cpf', 'cnpj_cliente',
    'cnpj', 'separacao_lote_id', 'nota_fiscal', 'chave_nfe', 'codigo_ibge',
]
_STRONG_KEYS = set(_STRONG_KEYS_ORDER)

_DIM_EXACT = {
    'estado', 'cod_uf', 'uf', 'municipio', 'cidade', 'nome_cidade',
    'vendedor', 'equipe_vendas', 'transportadora', 'cliente', 'nome_cliente',
    'raz_social', 'raz_social_red',
}


def _is_id_like(n: str) -> bool:
    """Identificador de negócio (não o id técnico surrogate).

    NÃO usa sufixo '_pedido'/'_nf': os ids reais (num_pedido, numero_nf) já são
    chaves "fortes"; o sufixo só causava falso positivo (data_pedido,
    status_pedido viravam "id" e roubavam o lugar de filtros úteis).
    """
    return (
        n.startswith(('num_', 'numero_', 'cod_', 'codigo_', 'cnpj', 'cpf'))
        or (n.endswith('_id') and n != 'id')
    )


def _is_dim(n: str) -> bool:
    """Dimensão/filtro comum (status, data, localização, cliente, tipo)."""
    return (
        'status' in n
        or n in _DIM_EXACT
        or n.startswith('tipo_')
        or n.startswith('data_') or n.endswith('_data')
        or 'expedicao' in n or 'vencimento' in n or 'agendamento' in n
    )


def _key_field_score(name: str) -> int:
    """Score de relevância de um campo p/ ESCOLHER a tabela. -1 = excluir."""
    n = name.lower()
    if n in KEY_FIELD_SKIP or n.endswith('_por') or n.endswith('_by'):
        return -1
    if n in _STRONG_KEYS:
        return 4
    if _is_id_like(n):
        return 3
    if _is_dim(n):
        return 2
    return 1


def _select_key_fields(table, teto: int = 5) -> list:
    """Seleciona até `teto` campos-chave por relevância (determinístico).

    Conjunto MÍNIMO p/ ESCOLHER a tabela (achado N2): chaves de negócio + 1-3
    filtros, sem id técnico nem auditoria. Determinístico: chaves fortes pela
    ordem canônica (_STRONG_KEYS_ORDER), demais ids/dims pela posição da coluna;
    no máx 1 campo "data" p/ não redundar.
    """
    cols = [c.name for c in table.columns]
    pos = {name: i for i, name in enumerate(cols)}

    def _strong_rank(n):
        return _STRONG_KEYS_ORDER.index(n) if n in _STRONG_KEYS_ORDER else 999

    # PK surrogate 'id' já cai no score -1 (KEY_FIELD_SKIP). PKs compostas de FKs
    # (tabelas de associação, ex: grupo_id + categoria_id) NÃO são excluídas —
    # são justamente as chaves de negócio dessas tabelas.
    strong = sorted(
        [n for n in cols if _key_field_score(n) == 4],
        key=lambda n: (_strong_rank(n), pos[n]),
    )
    other_ids = sorted(
        [n for n in cols if _key_field_score(n) == 3],
        key=lambda n: pos[n],
    )
    dims = sorted(
        [n for n in cols if _key_field_score(n) == 2],
        key=lambda n: pos[n],
    )
    rest = sorted(
        [n for n in cols if _key_field_score(n) == 1],
        key=lambda n: pos[n],
    )

    selecionados = []
    # 1) até 3 chaves de negócio (fortes primeiro, depois outros ids)
    for n in (strong + other_ids):
        if len(selecionados) >= 3:
            break
        if n not in selecionados:
            selecionados.append(n)
    # 2) até 2 filtros/dimensões; no máx 1 campo "data" p/ não redundar
    add_dim, data_usada = 0, False
    for n in dims:
        if add_dim >= 2 or len(selecionados) >= teto:
            break
        eh_data = n.startswith('data_') or n.endswith('_data')
        if eh_data and data_usada:
            continue
        if n not in selecionados:
            selecionados.append(n)
            add_dim += 1
            data_usada = data_usada or eh_data
    # 3) fallback: garantir ao menos alguns campos quando não há id/dim
    if len(selecionados) < 3:
        for n in rest:
            if len(selecionados) >= 3:
                break
            if n not in selecionados:
                selecionados.append(n)

    # 4) último recurso: tabela só com id + auditoria — evita key_fields vazio
    #    (key_fields vazio é inútil p/ a busca de tabela por intenção).
    if not selecionados:
        for n in cols:
            if n != 'id':
                selecionados.append(n)
            if len(selecionados) >= 3:
                break

    return selecionados[:teto]


# =====================================================================
# DOMÍNIO — derivado do app de origem do modelo (zero curadoria manual)
# =====================================================================
DOMINIO_LABELS = {
    'carteira': 'Carteira', 'separacao': 'Separação', 'faturamento': 'Faturamento',
    'embarques': 'Embarques', 'fretes': 'Fretes', 'financeiro': 'Financeiro',
    'estoque': 'Estoque', 'monitoramento': 'Monitoramento', 'producao': 'Produção',
    'manufatura': 'Manufatura', 'recebimento': 'Recebimento', 'devolucao': 'Devoluções',
    'transportadoras': 'Transportadoras', 'veiculos': 'Veículos',
    'localidades': 'Localidades', 'cotacao': 'Cotação', 'pallet': 'Pallets',
    'portaria': 'Portaria', 'rastreamento': 'Rastreamento', 'pedidos': 'Pedidos',
    'tabelas': 'Tabelas de Frete', 'cadastros_agendamento': 'Agendamento',
    'comercial': 'Comercial', 'custeio': 'Custeio', 'bi': 'BI',
    'notificacoes': 'Notificações', 'integracoes': 'Integrações',
    'portal': 'Portal', 'vinculos': 'Vínculos', 'auth': 'Autenticação',
    'permissions': 'Permissões', 'agente': 'Agente', 'motochefe': 'MotoChefe',
    'hora': 'Lojas HORA', 'motos_assai': 'Motos Assaí',
}

# Fallback por prefixo de nome de tabela (tabelas sem model_class — ex: órfãos
# vivos preservados, que não têm __module__).
_DOMINIO_PREFIXO = {
    'carvia_': 'CarVia', 'claude_': 'Agente', 'assai_': 'Motos Assaí',
    'portal_': 'Portal', 'bi_': 'BI', 'agent_': 'Agente',
}


def _dominio_from_table_name(table_name: str) -> str:
    n = (table_name or '').lower()
    for prefixo, label in _DOMINIO_PREFIXO.items():
        if n.startswith(prefixo):
            return label
    return 'Outros'


def _dominio_from_module(module_name, table_name: str) -> str:
    """Domínio (grupo navegável) derivado do app de origem do modelo.

    Ex: 'app.carteira.models' -> 'Carteira'; 'app.pallet.models.credito' ->
    'Pallets'. Sem model_class (módulo None) -> fallback por prefixo do nome.
    Decisão 3 do plano S1: zero curadoria manual de tabela->domínio.
    """
    if module_name and module_name.startswith('app.'):
        parts = module_name.split('.')
        if len(parts) >= 2:
            mod = parts[1]
            return DOMINIO_LABELS.get(mod, mod.replace('_', ' ').title())
    return _dominio_from_table_name(table_name)


def generate_catalog_entry(table_name: str, table, model_class=None) -> dict:
    """Gera entrada leve do catálogo: nome + descrição + key_fields + domínio.

    key_fields por relevância (N2) e domínio pelo app de origem (S1).
    """
    description = TABLE_DESCRIPTIONS.get(table_name, "")
    if not description and model_class:
        description = extract_class_docstring(model_class)
    if not description:
        description = f"Tabela {table_name}"

    key_fields = _select_key_fields(table)
    module_name = getattr(model_class, '__module__', None) if model_class else None
    dominio = _dominio_from_module(module_name, table_name)

    return {
        'name': table_name,
        'description': description,
        'key_fields': key_fields,
        'dominio': dominio,
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

    # Ordenação canônica (defensiva — já itera sorted(tables); decisão 4 do S0).
    relationships.sort(
        key=lambda r: (r['from_table'], r['from_column'], r['to_table'], r['to_column'])
    )
    return relationships


# =====================================================================
# IMPORTAÇÃO DOS MODELOS
# =====================================================================

def _discover_model_modules():
    """Descobre modulos de modelo varrendo app/, retornando nomes dotted.

    Resolve a causa raiz da "nao-atualizacao" (ex: teams_tasks): a lista hardcoded
    esquecia modulos novos. Candidato por NOME (models.py, models_*.py, *_models.py,
    ou arquivo dentro de pacote models/) E confirmado por CONTEUDO (`__tablename__`
    presente no arquivo). O filtro de conteudo elimina falsos positivos que casam o
    nome mas NAO sao ORM (ex: utils/ml_models, agente/sdk/model_router,
    financeiro/parsers/models, carteira/models_adapter_presep). Exclui __init__,
    test_* e __pycache__. Unida, na chamada, a uma lista legada de garantia.
    """
    found = set()
    app_dir = os.path.join(PROJECT_ROOT, 'app')
    for root, dirs, files in os.walk(app_dir):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        in_models_pkg = os.path.basename(root) == 'models'
        for fn in files:
            if not fn.endswith('.py') or fn.startswith('test_') or fn == '__init__.py':
                continue
            stem = fn[:-3]
            name_match = (
                stem == 'models'
                or stem.startswith('models_')
                or stem.endswith('_models')
            )
            if not (name_match or in_models_pkg):
                continue
            fpath = os.path.join(root, fn)
            try:
                with open(fpath, 'r', encoding='utf-8') as fh:
                    if '__tablename__' not in fh.read():
                        continue
            except (OSError, UnicodeDecodeError):
                continue
            rel = os.path.relpath(fpath, PROJECT_ROOT)
            found.add(rel[:-3].replace(os.sep, '.'))
    return found


def import_all_models():
    """Importa modelos SQLAlchemy. Retorna (metadata, model_map, import_errors).

    import_errors: lista de (modulo, erro). Quando NÃO vazia, o import ficou
    PARCIAL e a remoção de órfãos é bloqueada (salvaguarda inviolável do S0).
    """

    # Importar app para inicializar SQLAlchemy metadata
    os.environ.setdefault('FLASK_ENV', 'development')

    from app import create_app, db

    app = create_app()

    with app.app_context():
        # Modelo -> tabela mapping
        model_map = {}  # table_name -> model_class

        # Lista LEGADA de garantia (unida a auto-descoberta abaixo).
        legacy_modules = [
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
        # Uniao: auto-descoberta (pega modulos novos, ex: app.teams.models) +
        # legado de garantia. sorted -> determinístico (compativel com S0).
        model_modules = sorted(set(_discover_model_modules()) | set(legacy_modules))

        import_errors = []
        for module_name in model_modules:
            try:
                mod = importlib.import_module(module_name)

                # Mapear classes que são db.Model
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if hasattr(obj, '__tablename__') and hasattr(obj, '__table__'):
                        table_name = obj.__tablename__
                        model_map[table_name] = obj

            except Exception as e:
                import_errors.append((module_name, str(e)))
                print(f"⚠️  Erro ao importar {module_name}: {e}")

        return db.metadata, model_map, import_errors


# =====================================================================
# GERAÇÃO DOS ARQUIVOS
# =====================================================================

def generate_all(stats_only=False, check_only=False, prune_orphans=False):
    """Gera todos os schemas. Retorna código de saída (0=ok, 1=drift em --check)."""
    print("🔍 Importando modelos SQLAlchemy...")
    metadata, model_map, import_errors = import_all_models()

    all_tables = sorted(metadata.tables.keys())
    excluded = BLOCKED_TABLES | DEAD_TABLES | IRRELEVANT_TABLES
    allowed_tables = [t for t in all_tables if t not in excluded]
    # Admin-only: auth/agent/alembic/sessions/tokens — admin SQL bypassa o filtro padrao
    admin_only_tables = [t for t in all_tables if t in BLOCKED_TABLES]
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

    # Conteúdo canônico de cada destino: {path absoluto -> string JSON canônica}.
    # Construído em memória primeiro para suportar tanto a escrita idempotente
    # (write-if-changed) quanto o modo --check (comparar sem escrever).
    outputs = {}
    admin_only_set = set(admin_only_tables)

    # 1. Schemas individuais por tabela (allowed + admin_only)
    # admin_only tem schema gerado mas so e usavel via admin_mode (USUARIOS_SQL_ADMIN).
    # Safety validator bloqueia uso por nao-admin via tabelas_bloqueadas.
    print(f"\n📝 Gerando schemas individuais...")
    for table_name in list(allowed_tables) + admin_only_tables:
        table = metadata.tables[table_name]
        model_class = model_map.get(table_name)

        schema = extract_table_schema(table_name, table, model_class)
        if table_name in admin_only_set:
            schema['admin_only'] = True

        output_path = os.path.join(TABLES_DIR, f"{table_name}.json")
        outputs[output_path] = _dump_canonical(schema)

    # 2. Gerar catálogo
    print(f"\n📝 Gerando catálogo...")
    catalog = {
        'version': '2.1.0',
        'database': 'postgresql',
        'notas_gerais': [
            'Todos os valores monetários em BRL (R$)',
            'Datas no formato YYYY-MM-DD no banco',
            'Campos Boolean: True/False (PostgreSQL)',
            'Registros ativos: ativo = True (quando o campo existe)',
            'Para usar campos detalhados, consultar schemas/tables/{tabela}.json'
        ],
        # tabelas_bloqueadas: usado pelo safety validator (bloqueia em nao-admin).
        # Inclui BLOCKED_TABLES + DEAD_TABLES + IRRELEVANT_TABLES.
        'tabelas_bloqueadas': sorted(BLOCKED_TABLES | DEAD_TABLES | IRRELEVANT_TABLES),
        'total_tabelas': len(allowed_tables),
        'tabelas': [],
        # tabelas_admin: visiveis APENAS para usuarios em USUARIOS_SQL_ADMIN.
        # Mesmo formato de 'tabelas' (name, description, key_fields). NUNCA incluir
        # no prompt do LLM em modo nao-admin (ver SchemaProvider.get_catalog_text).
        'tabelas_admin': []
    }

    for table_name in allowed_tables:
        table = metadata.tables[table_name]
        model_class = model_map.get(table_name)
        entry = generate_catalog_entry(table_name, table, model_class)
        catalog['tabelas'].append(entry)

    for table_name in admin_only_tables:
        table = metadata.tables[table_name]
        model_class = model_map.get(table_name)
        entry = generate_catalog_entry(table_name, table, model_class)
        entry['admin_only'] = True
        catalog['tabelas_admin'].append(entry)

    # Ordenação canônica por nome (defensiva — decisão 4 do S0; catalog já
    # iterava allowed_tables ordenado, mas garantimos estabilidade explícita).
    catalog['tabelas'].sort(key=lambda e: e['name'])
    catalog['tabelas_admin'].sort(key=lambda e: e['name'])

    catalog_path = os.path.join(SCHEMAS_DIR, 'catalog.json')
    outputs[catalog_path] = _dump_canonical(catalog)
    catalog_size = len(outputs[catalog_path].encode('utf-8'))

    # 3. Gerar relationships
    print(f"\n📝 Gerando mapa de relacionamentos...")
    relationships = extract_relationships(metadata)

    rel_data = {
        'version': '2.0.0',
        'total_relationships': len(relationships),
        'relationships': relationships,
    }

    rel_path = os.path.join(SCHEMAS_DIR, 'relationships.json')
    outputs[rel_path] = _dump_canonical(rel_data)

    # --- Modo --check: comparar com o disco SEM escrever (drift detector) ---
    if check_only:
        drift = [p for p in sorted(outputs) if _read_text(p) != outputs[p]]
        if drift:
            print(f"\n❌ DRIFT: {len(drift)} arquivo(s) de schema desatualizado(s):")
            for p in drift:
                print(f"   • {os.path.relpath(p, PROJECT_ROOT)}")
            print("\n   Rode: python .claude/skills/consultando-sql/scripts/generate_schemas.py")
            return 1
        print(f"\n✅ --check: {len(outputs)} schemas atualizados (sem drift).")
        return 0

    # --- Escrita idempotente (write-if-changed): só grava o que mudou ---
    written = 0
    for path in sorted(outputs):
        if _write_if_changed(path, outputs[path]):
            written += 1
    unchanged = len(outputs) - written

    # --- Órfãos: schemas no disco sem tabela gerada ---
    # Política (decisão do usuário 2026-06-07): o fluxo automático/hook NUNCA
    # apaga — só LOGA. A remoção real exige --prune-orphans E import 100% completo
    # (salvaguarda dupla). Motivo (Passo 0): um "órfão" pode ser uma tabela VIVA
    # cujo módulo de modelo não está na lista de import.
    generated_table_names = set(allowed_tables) | set(admin_only_tables)
    orphans = _find_orphan_schemas(TABLES_DIR, generated_table_names)
    import_complete = not import_errors
    deleted = _resolve_orphans_to_delete(orphans, import_complete, prune_orphans)
    for name in deleted:
        os.remove(os.path.join(TABLES_DIR, f"{name}.json"))
    if orphans:
        if deleted:
            print(f"\n🗑️  {len(deleted)} schema(s) órfão(s) removido(s) (--prune-orphans):")
            for n in deleted:
                print(f"      - {n}")
        else:
            preservados = [o for o in orphans if o in ORFAOS_VIVOS_PRESERVAR]
            a_revisar = [o for o in orphans if o not in ORFAOS_VIVOS_PRESERVAR]
            if preservados:
                print(f"\nℹ️  {len(preservados)} schema(s) órfão(s) PRESERVADO(s) "
                      f"(vivos no PROD sem modelo ORM — allow-list ORFAOS_VIVOS_PRESERVAR):")
                for n in preservados:
                    print(f"      • {n}.json")
            if a_revisar:
                print(f"\n⚠️  {len(a_revisar)} schema(s) órfão(s) no disco (NÃO removidos):")
                for n in a_revisar:
                    print(f"      • {n}.json")
                if prune_orphans and not import_complete:
                    print(f"   ⛔ --prune-orphans IGNORADO: import parcial "
                          f"({len(import_errors)} módulo(s) com erro) — salvaguarda inviolável.")
                else:
                    print("   ⚠️  Um órfão pode ser tabela VIVA cujo módulo não está na "
                          "lista de import. REVISE antes de remover com --prune-orphans.")

    # 4. Resumo final
    total_fields = sum(
        len(metadata.tables[t].columns) for t in allowed_tables
    )
    print(f"\n{'='*60}")
    print(f"✅ GERAÇÃO COMPLETA")
    print(f"   Tabelas: {len(allowed_tables)}")
    print(f"   Campos totais: {total_fields}")
    print(f"   Relacionamentos: {len(relationships)}")
    print(f"   Arquivos: {len(outputs)} ({written} escritos, {unchanged} inalterados)")
    print(f"      schemas/catalog.json ({catalog_size:,} bytes)")
    print(f"      schemas/relationships.json")
    print(f"      schemas/tables/*.json")
    print(f"{'='*60}")
    return 0


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
    parser.add_argument(
        '--check', action='store_true',
        help='Não escreve; sai com código != 0 se algum schema estiver defasado (drift)'
    )
    parser.add_argument(
        '--prune-orphans', action='store_true',
        help='Remove schemas órfãos (sem tabela no metadata). Só age com import '
             'sem erros; o fluxo normal apenas LOGA os órfãos.'
    )
    args = parser.parse_args()

    rc = generate_all(
        stats_only=args.stats, check_only=args.check, prune_orphans=args.prune_orphans
    )
    if rc:
        sys.exit(rc)


if __name__ == '__main__':
    main()
