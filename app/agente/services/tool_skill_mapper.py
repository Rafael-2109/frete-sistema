"""
Mapeamento de MCP Tools para categorias de negocio.

Traduz nomes tecnicos (mcp__sql__consultar_sql) em categorias legiveis
para o dashboard de insights (Consulta SQL → Dados).

Hierarquia em 3 niveis:
    MCP Tool Name  →  Categoria de Negocio  →  Dominio
    mcp__sql__*    →  "Consulta SQL"        →  "Dados"
    mcp__browser__ →  "Operacao SSW"        →  "SSW"
    Skill:cotando  →  "Cotacao de Frete"    →  "Logistica"

Uso:
    from .tool_skill_mapper import map_tool_to_category, aggregate_by_category
    cat = map_tool_to_category('mcp__sql__consultar_sql')
    # → 'Consulta SQL'
"""

from typing import Dict, List


# =============================================================================
# NIVEL 1: MCP Tool → Categoria de Negocio
# =============================================================================

TOOL_TO_CATEGORY: Dict[str, str] = {
    # ── MCP SQL Tools ──
    'mcp__sql__consultar_sql': 'Consulta SQL',
    'mcp__sql__query_database': 'Consulta SQL',
    'mcp__sql__listar_tabelas': 'Consulta SQL',

    # ── MCP Memory Tools ──
    'mcp__memory__save_memory': 'Memoria do Agente',
    'mcp__memory__read_memory': 'Memoria do Agente',
    'mcp__memory__list_memories': 'Memoria do Agente',
    'mcp__memory__update_memory': 'Memoria do Agente',
    'mcp__memory__delete_memory': 'Memoria do Agente',

    # ── MCP Schema Tools ──
    'mcp__schema__describe_table': 'Catalogo de Dados',
    'mcp__schema__search_schemas': 'Catalogo de Dados',
    'mcp__schema__list_tables': 'Catalogo de Dados',

    # ── MCP Session Search Tools ──
    'mcp__sessions__semantic_search_sessions': 'Busca de Sessoes',

    # ── MCP Render Tools ──
    'mcp__render__consultar_logs': 'Monitoramento Render',
    'mcp__render__consultar_erros': 'Monitoramento Render',
    'mcp__render__status_servicos': 'Monitoramento Render',

    # ── MCP Browser/SSW Tools ──
    'mcp__browser__browser_navigate': 'Operacao SSW',
    'mcp__browser__browser_click': 'Operacao SSW',
    'mcp__browser__browser_type': 'Operacao SSW',
    'mcp__browser__browser_select': 'Operacao SSW',
    'mcp__browser__browser_read_content': 'Operacao SSW',
    'mcp__browser__browser_screenshot': 'Operacao SSW',
    'mcp__browser__browser_evaluate_js': 'Operacao SSW',
    'mcp__browser__browser_switch_frame': 'Operacao SSW',
    'mcp__browser__browser_ssw_login': 'Operacao SSW',
    'mcp__browser__browser_ssw_navigate_option': 'Operacao SSW',

    # ── SDK Built-in Tools ──
    'Bash': 'Execucao de Comandos',
    'Read': 'Leitura de Arquivos',
    'Write': 'Escrita de Arquivos',
    'Edit': 'Edicao de Arquivos',
    'Glob': 'Busca de Arquivos',
    'Grep': 'Busca em Conteudo',
    'AskUserQuestion': 'Interacao com Usuario',
    'Skill': 'Execucao de Skill',
    'WebSearch': 'Pesquisa Web',
    'WebFetch': 'Acesso Web',
    'LSP': 'Analise de Codigo',
    'Task': 'Subagente',
    # Task* tools (SDK 0.2.82+: substituiu TodoWrite — ver SDK_CHANGELOG.md)
    'TaskCreate': 'Gestao de Tarefas',
    'TaskUpdate': 'Gestao de Tarefas',
    'TaskGet': 'Gestao de Tarefas',
    'TaskList': 'Gestao de Tarefas',
    'NotebookEdit': 'Edicao de Notebook',
}


# =============================================================================
# NIVEL 1b: Skills → Categoria de Negocio
# =============================================================================

SKILL_TO_CATEGORY: Dict[str, str] = {
    # ── Logistica ──
    'cotando-frete': 'Cotacao de Frete',
    'gerindo-expedicao': 'Gestao de Expedicao',
    'monitorando-entregas': 'Monitoramento de Entregas',
    'criar-separacao': 'Gestao de Expedicao',
    'comunicar-pcp': 'Comunicacao PCP',
    'comunicar-comercial': 'Comunicacao Comercial',
    'verificar-disponibilidade': 'Verificacao de Estoque',
    'consultar-estoque': 'Verificacao de Estoque',
    'analise-carteira': 'Analise de Carteira',

    # ── Produto ──
    'visao-produto': 'Visao de Produto',
    'resolvendo-entidades': 'Resolucao de Entidades',

    # ── Dados / BI ──
    'consultando-sql': 'Consulta SQL',
    'exportando-arquivos': 'Exportacao de Dados',
    'lendo-arquivos': 'Importacao de Dados',
    'padronizando-docs': 'Padronizacao de Docs',
    'diagnosticando-banco': 'Diagnostico de Banco',

    # ── Odoo ──
    'rastreando-odoo': 'Rastreamento Odoo',
    'executando-odoo-financeiro': 'Financeiro Odoo',
    'conciliando-odoo-po': 'Conciliacao PO',
    'descobrindo-odoo-estrutura': 'Estrutura Odoo',
    'validacao-nf-po': 'Validacao NF x PO',
    'recebimento-fisico-odoo': 'Recebimento Fisico',
    'razao-geral-odoo': 'Razao Geral Odoo',
    'integracao-odoo': 'Integracao Odoo',
    'conciliando-transferencias-internas': 'Financeiro Odoo',
    'gerando-baseline-conciliacao': 'Baseline Conciliacao',
    'ajustando-quant-odoo': 'Estoque Odoo (Write)',
    'transferindo-interno-odoo': 'Estoque Odoo (Write)',
    'operando-reservas-odoo': 'Estoque Odoo (Write)',
    'operando-picking-odoo': 'Estoque Odoo (Write)',
    'operando-mo-odoo': 'Estoque Odoo (Write)',
    'escriturando-odoo': 'Escrituracao Entrada Odoo (Write)',
    'faturando-odoo': 'Estoque Odoo (Write)',
    'planejando-pre-etapa-odoo': 'Estoque Odoo (Write)',
    'consultando-quant-odoo': 'Estoque Odoo (Read)',
    'auditando-cadastro-fiscal-odoo': 'Pre-Flight Cadastro Fiscal Odoo',
    'auditando-reclassificacao-odoo': 'Auditoria Reclassificacao Odoo',

    # ── SPED ECD audit (subagente auditor-sped-ecd) ──
    'parseando-sped-ecd': 'Auditoria SPED ECD',
    'auditando-sped-contabil': 'Auditoria SPED ECD',
    'auditando-sped-vs-manual': 'Auditoria SPED ECD',
    'comparando-sped-ground-truth': 'Auditoria SPED ECD',

    # ── CarVia ──
    'gerindo-carvia': 'Gestao CarVia',

    # ── SSW ──
    'acessando-ssw': 'Consulta SSW',
    'operando-ssw': 'Operacao SSW',

    # ── Portal Atacadao (Hodie Booking) ──
    'operando-portal-atacadao': 'Operacao Portal Atacadao',

    # ── Sistema ──
    'frontend-design': 'Design Frontend',
    'gerindo-agente': 'Memoria do Agente',
    'skill-creator': 'Criacao de Skills',
    'ralph-wiggum': 'Dev Autonomo',
    'prd-generator': 'Geracao de PRD',
    'gerando-artifact': 'Geracao de Artifact',
    'consultando-sentry': 'Monitoramento Sentry',

    # ── Lojas HORA (B2C motos eletricas — Agente Lojas HORA) ──
    'acompanhando-pedido': 'Pipeline Lojas HORA',
    'conferindo-recebimento': 'Pipeline Lojas HORA',
    'consultando-estoque-loja': 'Pipeline Lojas HORA',
    'consultando-pecas-faltando': 'Pipeline Lojas HORA',
    'consultando-venda-loja': 'Pipeline Lojas HORA',
    'rastreando-chassi': 'Rastreamento Chassi HORA',

    # ── Motos Assai (B2B Q.P.A. Sendas) ──
    'consultando-estoque-assai': 'Pipeline Motos Assai',
    'rastreando-chassi-assai': 'Rastreamento Chassi Assai',
    'acompanhando-pedido-compra-assai': 'Pedidos VOE Q.P.A. + Compras Motochefe',
    'acompanhando-saida-assai': 'Saida Motos Assai (Separacao + NF Q.P.A.)',
    'conferindo-recibo-assai': 'Recibos Motochefe (Conferencia)',
    'registrando-evento-moto-assai': 'Eventos Pipeline Motos Assai',
    'carregando-motos-assai': 'Saida Motos Assai (Carregamento)',
}


# =============================================================================
# NIVEL 2: Categoria de Negocio → Dominio
# =============================================================================

CATEGORY_TO_DOMAIN: Dict[str, str] = {
    # ── Logistica ──
    'Cotacao de Frete': 'Logistica',
    'Gestao de Expedicao': 'Logistica',
    'Monitoramento de Entregas': 'Logistica',
    'Comunicacao PCP': 'Logistica',
    'Comunicacao Comercial': 'Logistica',
    'Verificacao de Estoque': 'Logistica',
    'Analise de Carteira': 'Logistica',

    # ── Produto ──
    'Visao de Produto': 'Produto',
    'Resolucao de Entidades': 'Produto',

    # ── Dados ──
    'Consulta SQL': 'Dados',
    'Catalogo de Dados': 'Dados',
    'Busca de Sessoes': 'Dados',
    'Exportacao de Dados': 'Dados',
    'Importacao de Dados': 'Dados',
    'Diagnostico de Banco': 'Dados',

    # ── Odoo ──
    'Rastreamento Odoo': 'Odoo',
    'Financeiro Odoo': 'Odoo',
    'Conciliacao PO': 'Odoo',
    'Estrutura Odoo': 'Odoo',
    'Validacao NF x PO': 'Odoo',
    'Recebimento Fisico': 'Odoo',
    'Razao Geral Odoo': 'Odoo',
    'Integracao Odoo': 'Odoo',
    'Estoque Odoo (Write)': 'Odoo',
    'Estoque Odoo (Read)': 'Odoo',
    'Escrituracao Entrada Odoo (Write)': 'Odoo',
    'Pre-Flight Cadastro Fiscal Odoo': 'Odoo',
    'Auditoria SPED ECD': 'Odoo',
    'Baseline Conciliacao': 'Financeiro',

    # ── CarVia ──
    'Gestao CarVia': 'Logistica',

    # ── Motos Assai ──
    'Pipeline Motos Assai': 'Motos Assai',
    'Rastreamento Chassi Assai': 'Motos Assai',
    'Pedidos VOE Q.P.A. + Compras Motochefe': 'Motos Assai',
    'Saida Motos Assai (Separacao + NF Q.P.A.)': 'Motos Assai',
    'Recibos Motochefe (Conferencia)': 'Motos Assai',
    'Eventos Pipeline Motos Assai': 'Motos Assai',

    # ── Lojas HORA ──
    'Pipeline Lojas HORA': 'Lojas HORA',
    'Rastreamento Chassi HORA': 'Lojas HORA',

    # ── SSW ──
    'Consulta SSW': 'SSW',
    'Operacao SSW': 'SSW',
    'Operacao Portal Atacadao': 'SSW',

    # ── Sistema ──
    'Busca de Rotas': 'Sistema',
    'Monitoramento Render': 'Sistema',
    'Memoria do Agente': 'Sistema',
    'Execucao de Comandos': 'Sistema',
    'Leitura de Arquivos': 'Sistema',
    'Escrita de Arquivos': 'Sistema',
    'Edicao de Arquivos': 'Sistema',
    'Busca de Arquivos': 'Sistema',
    'Busca em Conteudo': 'Sistema',
    'Interacao com Usuario': 'Sistema',
    'Execucao de Skill': 'Sistema',
    'Pesquisa Web': 'Sistema',
    'Acesso Web': 'Sistema',
    'Analise de Codigo': 'Sistema',
    'Subagente': 'Sistema',
    'Gestao de Tarefas': 'Sistema',
    'Edicao de Notebook': 'Sistema',
    'Design Frontend': 'Sistema',
    'Criacao de Skills': 'Sistema',
    'Dev Autonomo': 'Sistema',
    'Geracao de PRD': 'Sistema',
    'Geracao de Artifact': 'Sistema',
    'Monitoramento Sentry': 'Sistema',
}

# Cores por dominio (para graficos)
DOMAIN_COLORS: Dict[str, str] = {
    'Logistica': '#22d3ee',    # cyan
    'Produto': '#a78bfa',      # violet
    'Dados': '#60a5fa',        # blue
    'Odoo': '#fb923c',         # orange
    'SSW': '#fbbf24',          # amber
    'Sistema': '#94a3b8',      # slate
    'Motos Assai': '#34d399',  # emerald
    'Lojas HORA': '#f472b6',   # pink
    'Outros': '#6b7280',       # gray
}


# =============================================================================
# FUNCOES PUBLICAS
# =============================================================================

def map_tool_to_category(tool_name: str) -> str:
    """
    Mapeia nome de MCP tool para categoria de negocio legivel.

    Args:
        tool_name: Nome da tool (ex: 'mcp__sql__consultar_sql', 'Skill:cotando-frete')

    Returns:
        Categoria de negocio em portugues
    """
    # Direto no mapeamento
    if tool_name in TOOL_TO_CATEGORY:
        return TOOL_TO_CATEGORY[tool_name]

    # Skill prefix (ex: 'Skill:cotando-frete')
    if tool_name.startswith('Skill:'):
        skill_name = tool_name.split(':', 1)[1].strip()
        if skill_name in SKILL_TO_CATEGORY:
            return SKILL_TO_CATEGORY[skill_name]

    # Fallback: parsear mcp__SERVER__tool → usar SERVER como categoria
    if tool_name.startswith('mcp__'):
        parts = tool_name.split('__')
        if len(parts) >= 3:
            server = parts[1].capitalize()
            return f'Ferramenta {server}'

    return 'Outros'


def map_tool_to_domain(tool_name: str) -> str:
    """
    Mapeia nome de MCP tool para dominio de alto nivel.

    Args:
        tool_name: Nome da tool

    Returns:
        Dominio (Logistica, Produto, Dados, Odoo, SSW, Sistema, Outros)
    """
    category = map_tool_to_category(tool_name)
    return CATEGORY_TO_DOMAIN.get(category, 'Outros')


def aggregate_by_category(tool_counts: Dict[str, int]) -> List[Dict]:
    """
    Agrega contagens de tools por categoria de negocio.

    Args:
        tool_counts: Dict {tool_name: count}

    Returns:
        Lista de {category, count, domain, color} ordenada por count DESC
    """
    category_counts: Dict[str, int] = {}

    for tool_name, count in tool_counts.items():
        category = map_tool_to_category(tool_name)
        category_counts[category] = category_counts.get(category, 0) + count

    result = []
    for category, count in category_counts.items():
        domain = CATEGORY_TO_DOMAIN.get(category, 'Outros')
        result.append({
            'category': category,
            'count': count,
            'domain': domain,
            'color': DOMAIN_COLORS.get(domain, DOMAIN_COLORS['Outros']),
        })

    result.sort(key=lambda x: x['count'], reverse=True)
    return result


def aggregate_by_domain(tool_counts: Dict[str, int]) -> List[Dict]:
    """
    Agrega contagens de tools por dominio de alto nivel.

    Args:
        tool_counts: Dict {tool_name: count}

    Returns:
        Lista de {domain, count, color} ordenada por count DESC
    """
    domain_counts: Dict[str, int] = {}

    for tool_name, count in tool_counts.items():
        domain = map_tool_to_domain(tool_name)
        domain_counts[domain] = domain_counts.get(domain, 0) + count

    result = []
    for domain, count in domain_counts.items():
        result.append({
            'domain': domain,
            'count': count,
            'color': DOMAIN_COLORS.get(domain, DOMAIN_COLORS['Outros']),
        })

    result.sort(key=lambda x: x['count'], reverse=True)
    return result
