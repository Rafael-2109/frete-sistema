"""
Service: Razao Geral (General Ledger) do Odoo
==============================================

Extrai dados contabeis do Odoo (account.move.line) e gera Excel
formatado do relatorio Razao Geral com saldo inicial para contas
patrimoniais.

Otimizacoes aplicadas:
- ID-based cursor pagination (O(1) por batch, sem degradacao por offset)
- Transformacao inline (sem duplicacao de memoria)
- xlsxwriter com constant_memory (5x mais rapido que openpyxl)

Modelos Odoo utilizados:
- account.move.line (linhas de lancamento)
- account.account (plano de contas)

Autor: Sistema de Fretes
Data: 2026-01-23
"""

import logging
from io import BytesIO
from datetime import datetime
import xlsxwriter

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTES
# ============================================================

# Empresas disponiveis para o relatorio
EMPRESAS_RAZAO_GERAL = [
    {'id': 1, 'nome': 'NACOM GOYA - FB', 'sigla': 'FB'},
    {'id': 3, 'nome': 'NACOM GOYA - SC', 'sigla': 'SC'},
    {'id': 4, 'nome': 'NACOM GOYA - CD', 'sigla': 'CD'},
    {'id': 5, 'nome': 'LA FAMIGLIA - LF', 'sigla': 'LF'},
]

# Account types patrimoniais (recebem saldo inicial)
ACCOUNT_TYPES_PATRIMONIAIS = [
    'asset_receivable', 'asset_cash', 'asset_current',
    'asset_non_current', 'asset_prepayments', 'asset_fixed',
    'liability_payable', 'liability_credit_card',
    'liability_current', 'liability_non_current',
    'equity', 'equity_unaffected'
]

# Campos a buscar no account.move.line
CAMPOS_MOVE_LINE = [
    'id', 'date', 'move_name', 'account_id', 'partner_id',
    'ref', 'name', 'debit', 'credit', 'balance',
    'journal_id', 'matching_number'
]

# Configuracao de paginacao
BATCH_SIZE = 3000

# Colunas do Excel
COLUNAS = ['Conta Contabil', 'Data', 'Lancamento', 'Diario', 'Parceiro',
           'Referencia', 'Label', 'Debito', 'Credito', 'Saldo Acumulado', 'Conciliacao']

LARGURAS_COLUNAS = [30, 12, 22, 12, 35, 25, 40, 15, 15, 18, 15]


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def _formatar_data_br(data_str):
    """Converte YYYY-MM-DD para DD/MM/YYYY"""
    if not data_str:
        return ''
    try:
        dt = datetime.strptime(str(data_str), '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return str(data_str)


def _normalizar_many2one(campo):
    """Extrai display_name de campo many2one [id, name]"""
    if campo and isinstance(campo, (list, tuple)) and len(campo) > 1:
        return campo[1]
    return ''


def _tratar_false(valor, tipo='str'):
    """Trata valores False do Odoo"""
    if valor is False or valor is None:
        return '' if tipo == 'str' else 0.0
    return valor


# ============================================================
# FUNCOES DE BUSCA NO ODOO
# ============================================================

def calcular_saldos_iniciais(connection, account_ids_patrimoniais, data_inicio, company_ids):
    """
    Calcula saldos iniciais para contas patrimoniais via read_group.
    Uma UNICA query agrupando por account_id.

    Args:
        connection: OdooConnection autenticada
        account_ids_patrimoniais: Lista de IDs de contas patrimoniais
        data_inicio: Data inicio do periodo (string YYYY-MM-DD)
        company_ids: Lista de company_ids

    Returns:
        dict: {account_id: {'debit': X, 'credit': Y, 'balance': Z}}
    """
    if not account_ids_patrimoniais:
        return {}

    domain = [
        ['account_id', 'in', account_ids_patrimoniais],
        ['date', '<', data_inicio],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', company_ids]
    ]

    result = connection.execute_kw(
        'account.move.line',
        'read_group',
        [domain],
        {
            'fields': ['account_id', 'debit:sum', 'credit:sum', 'balance:sum'],
            'groupby': ['account_id'],
            'lazy': False
        },
        timeout_override=180
    )

    saldos = {}
    for grupo in result:
        acc_id = grupo['account_id']
        if isinstance(acc_id, (list, tuple)):
            acc_id = acc_id[0]

        saldos[acc_id] = {
            'debit': grupo.get('debit', 0) or 0,
            'credit': grupo.get('credit', 0) or 0,
            'balance': grupo.get('balance', 0) or 0
        }

    return saldos


def buscar_movimentos_razao(connection, data_ini, data_fim, company_ids, conta_filter=None):
    """
    Busca todos os movimentos contabeis do periodo com ID-cursor pagination
    e transformacao inline (sem duplicacao de memoria).

    Usa cursor baseado em ID ao inves de offset para performance constante
    O(1) por batch, independente da posicao na tabela.

    Args:
        connection: OdooConnection autenticada
        data_ini: Data inicial (string YYYY-MM-DD)
        data_fim: Data final (string YYYY-MM-DD)
        company_ids: Lista de company_ids
        conta_filter: Codigo parcial da conta para filtrar (opcional)

    Returns:
        tuple: (dados_agrupados, contas_info, saldos_iniciais, total_registros)
            - dados_agrupados: dict {account_id: [movimentos transformados]}
            - contas_info: dict {account_id: {code, name, account_type}}
            - saldos_iniciais: dict {account_id: {debit, credit, balance}}
            - total_registros: int total de linhas contabeis
    """
    # 1. Montar domain base
    domain = [
        ['date', '>=', data_ini],
        ['date', '<=', data_fim],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', company_ids]
    ]

    # Se filtro de conta, buscar account_ids primeiro
    if conta_filter and conta_filter.strip():
        contas_filtradas = connection.execute_kw(
            'account.account', 'search_read',
            [[['code', 'ilike', conta_filter.strip()]]],
            {'fields': ['id'], 'limit': 1000}
        )
        if contas_filtradas:
            account_ids_filtro = [c['id'] for c in contas_filtradas]
            domain.append(['account_id', 'in', account_ids_filtro])
        else:
            return {}, {}, {}, 0

    # 2. Buscar com ID-cursor + transformar inline
    logger.info(f"Buscando account.move.line: {data_ini} a {data_fim}, companies={company_ids}")

    dados_agrupados = {}
    account_ids_encontrados = set()
    total_registros = 0
    last_id = 0

    while True:
        # Cursor baseado em ID — performance constante O(1) por batch
        domain_cursor = domain + [['id', '>', last_id]]

        lote = connection.execute_kw(
            'account.move.line', 'search_read', [domain_cursor],
            {'fields': CAMPOS_MOVE_LINE, 'limit': BATCH_SIZE, 'order': 'id asc'},
            timeout_override=120
        )

        if not lote:
            break

        last_id = lote[-1]['id']
        total_registros += len(lote)

        # Transformar inline — sem acumular registros raw em memoria
        for reg in lote:
            acc_tuple = reg.get('account_id')
            if not acc_tuple or not isinstance(acc_tuple, (list, tuple)):
                continue

            acc_id = acc_tuple[0]
            account_ids_encontrados.add(acc_id)

            dados_agrupados.setdefault(acc_id, []).append({
                'date': reg.get('date') or '',
                'move_name': reg.get('move_name') or '',
                'partner_name': _normalizar_many2one(reg.get('partner_id')),
                'ref': _tratar_false(reg.get('ref')),
                'name': _tratar_false(reg.get('name')),
                'debit': float(reg.get('debit') or 0),
                'credit': float(reg.get('credit') or 0),
                'balance': float(reg.get('balance') or 0),
                'journal_name': _normalizar_many2one(reg.get('journal_id')),
                'matching_number': _tratar_false(reg.get('matching_number'))
            })

        logger.info(f"   ... {total_registros} registros buscados (cursor id>{last_id})")

        if len(lote) < BATCH_SIZE:
            break

    logger.info(f"Total: {total_registros} linhas contabeis em {len(account_ids_encontrados)} contas")

    if not total_registros:
        return {}, {}, {}, 0

    # 3. Buscar dados das contas
    account_ids_lista = list(account_ids_encontrados)
    contas = connection.execute_kw(
        'account.account', 'search_read',
        [[['id', 'in', account_ids_lista]]],
        {'fields': ['id', 'code', 'name', 'account_type'], 'limit': 5000}
    )
    contas_info = {c['id']: c for c in contas}

    # 4. Identificar contas patrimoniais e calcular saldos iniciais
    contas_patrimoniais = [
        c['id'] for c in contas
        if c.get('account_type') in ACCOUNT_TYPES_PATRIMONIAIS
    ]

    saldos_iniciais = calcular_saldos_iniciais(
        connection, contas_patrimoniais, data_ini, company_ids
    )

    return dados_agrupados, contas_info, saldos_iniciais, total_registros


# ============================================================
# GERACAO DO EXCEL (xlsxwriter — constant_memory mode)
# ============================================================

def gerar_excel_razao(dados_agrupados, contas_info, saldos_iniciais, data_ini='', data_fim='', company_ids=None):
    """
    Gera Excel do Razao Geral com xlsxwriter (constant_memory mode).
    Formatos definidos 1x e reutilizados em todas as linhas — ~5x mais rapido que openpyxl.

    Args:
        dados_agrupados: Dict {account_id: [movimentos transformados]}
        contas_info: Dict {account_id: {code, name, account_type}}
        saldos_iniciais: Dict {account_id: {debit, credit, balance}}
        data_ini: Data inicial (para titulo)
        data_fim: Data final (para titulo)
        company_ids: Lista de companies (para titulo)

    Returns:
        BytesIO: Arquivo Excel em memoria
    """
    if company_ids is None:
        company_ids = []

    output = BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True, 'constant_memory': True})
    ws = wb.add_worksheet('Razao Geral')

    # --- Formatos (definidos 1x, reutilizados em todas as linhas) ---
    fmt_titulo = wb.add_format({
        'font_name': 'Calibri', 'font_size': 14, 'bold': True, 'align': 'center'
    })
    fmt_subtitulo = wb.add_format({
        'font_name': 'Calibri', 'font_size': 10, 'align': 'center'
    })
    fmt_cabecalho = wb.add_format({
        'font_name': 'Calibri', 'font_size': 10, 'bold': True,
        'font_color': '#FFFFFF', 'bg_color': '#4472C4',
        'align': 'center', 'border': 1
    })
    fmt_normal = wb.add_format({
        'font_name': 'Calibri', 'font_size': 10, 'border': 1
    })
    fmt_number = wb.add_format({
        'font_name': 'Calibri', 'font_size': 10, 'border': 1, 'num_format': '#,##0.00'
    })
    fmt_saldo_ini = wb.add_format({
        'font_name': 'Calibri', 'font_size': 10, 'italic': True,
        'font_color': '#555555', 'border': 1
    })
    fmt_saldo_ini_num = wb.add_format({
        'font_name': 'Calibri', 'font_size': 10, 'italic': True,
        'font_color': '#555555', 'border': 1, 'num_format': '#,##0.00'
    })

    # --- Larguras das colunas ---
    for col_idx, largura in enumerate(LARGURAS_COLUNAS):
        ws.set_column(col_idx, col_idx, largura)

    # --- Titulo (row 0) ---
    titulo = 'RAZAO GERAL'
    if data_ini and data_fim:
        titulo += f' - Periodo: {_formatar_data_br(data_ini)} a {_formatar_data_br(data_fim)}'
    ws.merge_range(0, 0, 0, len(COLUNAS) - 1, titulo, fmt_titulo)

    # --- Subtitulo (row 1) ---
    empresas_nomes = [e['nome'] for e in EMPRESAS_RAZAO_GERAL if e['id'] in company_ids]
    subtitulo = f'Empresas: {", ".join(empresas_nomes)}' if empresas_nomes else 'Todas as empresas'
    subtitulo += ' | Status: Posted'
    ws.merge_range(1, 0, 1, len(COLUNAS) - 1, subtitulo, fmt_subtitulo)

    # Row 2: vazia (espaco)

    # --- Cabecalho (row 3) ---
    for col_idx, nome_col in enumerate(COLUNAS):
        ws.write(3, col_idx, nome_col, fmt_cabecalho)

    row = 4

    # --- Dados ordenados por codigo de conta ---
    contas_ordenadas = sorted(
        dados_agrupados.keys(),
        key=lambda x: contas_info.get(x, {}).get('code', '999999')
    )

    for account_id in contas_ordenadas:
        conta = contas_info.get(account_id, {})
        code = conta.get('code', '???')
        name = conta.get('name', 'Conta desconhecida')
        conta_label = f'{code} - {name}'
        movimentos = dados_agrupados[account_id]

        # Ordenar por data (dados vem por id asc, precisamos por data)
        movimentos.sort(key=lambda x: (x['date'], x['move_name']))

        # Saldo inicial (se patrimonial)
        saldo_acumulado = 0.0
        if account_id in saldos_iniciais:
            si = saldos_iniciais[account_id]
            saldo_acumulado = si['balance']

            ws.write(row, 0, conta_label, fmt_saldo_ini)
            ws.write(row, 1, '', fmt_saldo_ini)
            ws.write(row, 2, '', fmt_saldo_ini)
            ws.write(row, 3, '', fmt_saldo_ini)
            ws.write(row, 4, '', fmt_saldo_ini)
            ws.write(row, 5, '', fmt_saldo_ini)
            ws.write(row, 6, 'Saldo Inicial', fmt_saldo_ini)
            ws.write(row, 7, si['debit'], fmt_saldo_ini_num)
            ws.write(row, 8, si['credit'], fmt_saldo_ini_num)
            ws.write(row, 9, saldo_acumulado, fmt_saldo_ini_num)
            ws.write(row, 10, '', fmt_saldo_ini)
            row += 1

        # Movimentos do periodo
        for mov in movimentos:
            saldo_acumulado += mov['balance']

            ws.write(row, 0, conta_label, fmt_normal)
            ws.write(row, 1, _formatar_data_br(mov['date']), fmt_normal)
            ws.write(row, 2, mov['move_name'], fmt_normal)
            ws.write(row, 3, mov['journal_name'], fmt_normal)
            ws.write(row, 4, mov['partner_name'], fmt_normal)
            ws.write(row, 5, mov['ref'], fmt_normal)
            ws.write(row, 6, mov['name'], fmt_normal)
            ws.write(row, 7, mov['debit'], fmt_number)
            ws.write(row, 8, mov['credit'], fmt_number)
            ws.write(row, 9, saldo_acumulado, fmt_number)
            ws.write(row, 10, mov['matching_number'], fmt_normal)
            row += 1

    wb.close()
    output.seek(0)

    logger.info(f"Excel gerado: {row - 4} linhas de dados")
    return output
