# -*- coding: utf-8 -*-
"""
Extracao de dados Odoo para SPED ECD Centralizado
===================================================

Consolida dados das 3 companies (FB matriz + SC + CD filiais) para gerar
SPED ECD centralizado.

Mitigacoes aplicadas:
- R3 (RAM): streaming generator para lancamentos (1000 lines por batch)
- R5 (multi-company): agregacao TUDO por `code` (nao por account_id)
- R12 (5 contas divergentes): busca FB primeiro, completa com SC/CD apenas para codes nao-existentes
- R20 (retry Odoo): tenacity decorator nas queries criticas

Autor: Sistema de Fretes
Data: 2026-05-14
"""

import logging
from datetime import date, timedelta
from typing import Dict, Generator, List, Tuple, Union

from app.relatorios_fiscais.services.sped_ecd_constantes import (
    ACCOUNT_TYPES_PATRIMONIAIS,
    ACCOUNT_TYPES_RESULTADO,
    BATCH_SIZE_LANCAMENTOS,
    CNPJ_MATRIZ,
    COMPANIES_ECD,
    COMPANY_MATRIZ_ID,
    TIMEOUT_QUERY_PESADA,
    TIMEOUT_QUERY_SIMPLES,
)

logger = logging.getLogger(__name__)


# ============================================================
# HELPER PAGINACAO (mitigacao code-review BLOCKER #4)
# ============================================================

def _buscar_paginado(connection, model: str, domain: List, fields: List,
                     batch: int = 5000, max_total: int = 50000) -> List[dict]:
    """
    search_read paginado via ID-cursor (sem risco de truncar silenciosamente).

    Args:
        connection: OdooConnection autenticada
        model: nome do modelo Odoo
        domain: filtros (sem cursor — sera adicionado)
        fields: campos a buscar
        batch: tamanho do lote
        max_total: limite hard de seguranca (50k registros)

    Returns:
        Lista completa de records
    """
    todos = []
    last_id = 0
    while True:
        domain_cursor = list(domain) + [['id', '>', last_id]]
        lote = connection.execute_kw(
            model, 'search_read', [domain_cursor],
            {'fields': fields, 'limit': batch, 'order': 'id asc'},
            timeout_override=TIMEOUT_QUERY_SIMPLES,
        )
        if not lote:
            break
        todos.extend(lote)
        last_id = lote[-1]['id']
        if len(todos) >= max_total:
            logger.warning(
                f'[SPED ECD] Limite max_total {max_total} atingido em {model}: '
                f'pode estar truncado'
            )
            break
        if len(lote) < batch:
            break
    return todos


# ============================================================
# DADOS DA MATRIZ
# ============================================================

def buscar_dados_matriz(connection) -> dict:
    """
    Busca dados da matriz FB (company_id=1) para registro 0000.
    Returns dict com: name, razao_social, cnpj, ie, im, nire, cod_mun, uf.
    """
    co_list = connection.execute_kw(
        'res.company', 'read', [[COMPANY_MATRIZ_ID]],
        {'fields': [
            'name', 'l10n_br_cnpj', 'l10n_br_razao_social',
            'l10n_br_ie', 'l10n_br_im', 'l10n_br_nire',
            'l10n_br_municipio_id', 'partner_id',
        ]},
        timeout_override=TIMEOUT_QUERY_SIMPLES,
    )
    if not co_list:
        raise RuntimeError(f'Company matriz {COMPANY_MATRIZ_ID} nao encontrada no Odoo')

    co = co_list[0]

    # Buscar municipio (codigo IBGE) e UF
    cod_mun = ''
    uf = 'SP'  # default NACOM
    municipio_field = co.get('l10n_br_municipio_id')
    if municipio_field and isinstance(municipio_field, (list, tuple)) and municipio_field[0]:
        try:
            mun_list = connection.execute_kw(
                'l10n_br_base.municipio', 'read',
                [[municipio_field[0]]],
                {'fields': ['name', 'l10n_br_ibge_code', 'state_id']},
                timeout_override=TIMEOUT_QUERY_SIMPLES,
            )
            if mun_list:
                mun = mun_list[0]
                cod_mun = mun.get('l10n_br_ibge_code', '') or ''
                state_field = mun.get('state_id')
                if state_field and isinstance(state_field, (list, tuple)):
                    # state_id retorna [id, "Sao Paulo (SP)"] — extrair UF
                    nome_estado = state_field[1] or ''
                    if '(' in nome_estado:
                        uf = nome_estado.split('(')[-1].rstrip(')')[:2]
        except Exception as e:
            logger.warning(f'Erro ao buscar municipio matriz: {e}')

    # CNPJ sem mascara
    cnpj_raw = co.get('l10n_br_cnpj') or ''
    cnpj_limpo = ''.join(c for c in cnpj_raw if c.isdigit()) or CNPJ_MATRIZ

    return {
        'name': co.get('name', 'NACOM GOYA - FB'),
        'razao_social': co.get('l10n_br_razao_social') or co.get('name', ''),
        'cnpj': cnpj_limpo,
        'ie': co.get('l10n_br_ie') or '',
        'im': co.get('l10n_br_im') or '',
        'nire': co.get('l10n_br_nire') or '',
        'cod_mun': cod_mun,
        'uf': uf,
    }


# ============================================================
# PLANO DE CONTAS CONSOLIDADO (R12 + R5)
# ============================================================

def buscar_plano_contas_consolidado(connection) -> Tuple[List[dict], Dict[int, str]]:
    """
    Busca plano de contas das 3 companies, deduplica por code, gera hierarquia
    sintetica e mapa id_to_code para consolidacao.

    Mitigacao R12: busca FB primeiro (autoritativo para nomes), completa com SC/CD.
    Mitigacao R5: id_to_code mapeia TODOS os account_ids das 3 companies para 1 code.

    Returns:
        (plano_consolidado, id_to_code)
        - plano_consolidado: lista ordenada por code, com sinteticas + analiticas
        - id_to_code: dict {account_id: code} para consolidacao
    """
    plano_dedupe = {}  # code -> dados conta
    id_to_code = {}    # account_id -> code (consolidacao R5)

    # Campos consultados — incluindo mapeamento Odoo CIEL IT (V1.1):
    # - l10n_br_conta_referencial: codigo do plano referencial Receita (87% cobertura)
    # - l10n_br_cod_nat: codigo da natureza Receita (99% cobertura)
    CAMPOS_PLANO = [
        'id', 'code', 'name', 'account_type', 'company_id', 'create_date',
        'l10n_br_conta_referencial', 'l10n_br_cod_nat',
    ]

    # 1. Buscar FB primeiro (matriz, autoritativo para nomes)
    # Mitigacao code-review BLOCKER #4: paginacao ID-cursor (sem limite truncar)
    contas_fb = _buscar_paginado(
        connection, 'account.account',
        [['company_id', '=', COMPANY_MATRIZ_ID]],
        CAMPOS_PLANO,
    )

    for c in contas_fb:
        code = c.get('code')
        if not code:
            continue
        plano_dedupe[code] = {
            'code': code,
            'name': c.get('name', ''),
            'account_type': c.get('account_type', ''),
            'create_date': (c.get('create_date') or '2010-01-01')[:10],
            'company_id_origem': c.get('company_id', [None])[0] if isinstance(c.get('company_id'), (list, tuple)) else c.get('company_id'),
            # V1.1 — mapeamento direto Odoo CIEL IT
            'conta_referencial_odoo': (c.get('l10n_br_conta_referencial') or '').strip(),
            'cod_nat_odoo': (c.get('l10n_br_cod_nat') or '').strip(),
        }
        id_to_code[c['id']] = code

    # 2. Completar com SC e CD (apenas codes que NAO existem em FB)
    for cid in (3, 4):
        contas_extras = _buscar_paginado(
            connection, 'account.account',
            [['company_id', '=', cid]],
            CAMPOS_PLANO,
        )
        for c in contas_extras:
            code = c.get('code')
            if not code:
                continue
            # Sempre mapeia o ID para o code (consolidacao)
            id_to_code[c['id']] = code
            # So adiciona ao plano se nao existe
            if code not in plano_dedupe:
                plano_dedupe[code] = {
                    'code': code,
                    'name': c.get('name', ''),
                    'account_type': c.get('account_type', ''),
                    'create_date': (c.get('create_date') or '2010-01-01')[:10],
                    'company_id_origem': cid,
                    'conta_referencial_odoo': (c.get('l10n_br_conta_referencial') or '').strip(),
                    'cod_nat_odoo': (c.get('l10n_br_cod_nat') or '').strip(),
                }

    logger.info(
        f'[SPED ECD] Plano consolidado: {len(plano_dedupe)} codes unicos, '
        f'{len(id_to_code)} account_ids mapeados'
    )

    # 3. Gerar hierarquia sintetica (R2 mitigacao)
    plano_completo = _gerar_hierarquia_sintetica(plano_dedupe)

    return plano_completo, id_to_code


def _gerar_hierarquia_sintetica(plano_analiticas: Dict[str, dict]) -> List[dict]:
    """
    Para cada code analitica de N digitos, gera contas sinteticas em todos os
    niveis intermediarios (1 a N-1), garantindo cadeia hierarquica completa.

    Mitigacao R2: hierarquia monotonicamente crescente (NIVEL=1, 2, 3, ..., N).
    """
    sinteticas = {}  # code -> dados sintetica

    # Nomes default por classe nivel 1
    NOMES_CLASSE_NIVEL_1 = {
        '1': 'ATIVO',
        '2': 'PASSIVO E PATRIMONIO LIQUIDO',
        '3': 'CONTAS DE RESULTADO',
        '4': 'CONTAS DE COMPENSACAO',
        '5': 'CONTAS DE COMPENSACAO',
        '6': 'CONTAS DE COMPENSACAO',
        '7': 'OUTRAS',
        '8': 'OUTRAS',
        '9': 'OUTRAS',
    }

    for code, dados in plano_analiticas.items():
        if not code or not code[0].isdigit():
            continue
        n = len(code)
        # Para cada prefixo (do nivel 1 ate n-1), garantir sintetica existe
        for nivel in range(1, n):
            prefix = code[:nivel]
            if prefix in sinteticas:
                continue
            cod_sup = code[:nivel - 1] if nivel > 1 else ''
            if nivel == 1:
                nome = NOMES_CLASSE_NIVEL_1.get(prefix, f'GRUPO {prefix}')
            else:
                nome = f'GRUPO {prefix}'  # nome generico — pode ser ajustado V2
            sinteticas[prefix] = {
                'code': prefix,
                'nivel': nivel,
                'name': nome,
                'tipo': 'S',  # Sintetica
                'cod_sup': cod_sup,
                'account_type': dados.get('account_type', ''),  # herda do filho
                'create_date': '2010-01-01',
            }

    # Combinar sinteticas + analiticas
    todas = []
    # Sinteticas primeiro (em ordem hierarquica)
    for code in sorted(sinteticas.keys()):
        todas.append(sinteticas[code])

    # Analiticas (nivel = N do code)
    for code, dados in plano_analiticas.items():
        if not code or not code[0].isdigit():
            continue
        n = len(code)
        cod_sup = code[:n - 1] if n > 1 else ''
        # Garantir cod_sup esta nas sinteticas (deveria estar)
        todas.append({
            'code': code,
            'nivel': n,
            'name': dados.get('name', ''),
            'tipo': 'A',  # Analitica
            'cod_sup': cod_sup,
            'account_type': dados.get('account_type', ''),
            'create_date': dados.get('create_date', '2010-01-01'),
            # V1.1 — propagar mapeamento Odoo CIEL IT
            'conta_referencial_odoo': dados.get('conta_referencial_odoo', ''),
            'cod_nat_odoo': dados.get('cod_nat_odoo', ''),
        })

    # Ordenar por code para emissao SPED
    todas.sort(key=lambda x: (x['code'], x['nivel']))

    return todas


# ============================================================
# SALDOS PERIODICOS MENSAIS (R5 corrigido)
# ============================================================

def calcular_saldos_periodicos_mensais(
    connection,
    date_ini: date,
    date_fim: date,
    id_to_code: Dict[int, str],
) -> Dict[str, dict]:
    """
    Calcula saldos mensais (I150/I155) para o periodo, consolidando POR CODE.

    Returns:
        {
            'YYYY-MM': {
                'date_ini': date,
                'date_fim': date,
                'por_code': {code: {'saldo_inicial', 'debit', 'credit', 'saldo_final'}}
            }
        }
    """
    from dateutil.relativedelta import relativedelta

    resultado = {}

    cursor_mes = date(date_ini.year, date_ini.month, 1)
    while cursor_mes <= date_fim:
        # Calcular fim do mes
        prox_mes = cursor_mes + relativedelta(months=1)
        ult_dia_mes = prox_mes - timedelta(days=1)
        if ult_dia_mes > date_fim:
            ult_dia_mes = date_fim

        # Saldo inicial do mes (acumulado ate dia anterior ao cursor)
        saldos_iniciais_por_acc = _read_group_balance(
            connection,
            domain_extra=[['date', '<', cursor_mes.strftime('%Y-%m-%d')]],
        )

        # Movimento do mes (entre cursor e ult_dia_mes)
        movimentos_por_acc = _read_group_balance(
            connection,
            domain_extra=[
                ['date', '>=', cursor_mes.strftime('%Y-%m-%d')],
                ['date', '<=', ult_dia_mes.strftime('%Y-%m-%d')],
            ],
            with_debit_credit=True,
        )

        # Consolidar por code (R5)
        # Mitigacao code-review BLOCKER #5: rastreia acc_ids ja somados no inicial
        # para nao perder saldo inicial de acc_ids do mesmo code (multi-company)
        por_code = {}
        acc_ids_inicial_processados = set()

        for tupla in movimentos_por_acc:
            acc_id, debit_val, credit_val, balance_val = tupla
            code = id_to_code.get(acc_id)
            if not code:
                continue
            saldo_ini = saldos_iniciais_por_acc.get(acc_id, 0) or 0
            slot = por_code.setdefault(code, {
                'saldo_inicial': 0, 'debit': 0, 'credit': 0, 'saldo_final': 0
            })
            slot['saldo_inicial'] += saldo_ini
            slot['debit'] += debit_val
            slot['credit'] += credit_val
            slot['saldo_final'] += saldo_ini + balance_val
            acc_ids_inicial_processados.add(acc_id)

        # Adicionar saldo inicial de acc_ids que NAO entraram no movimento (mesmo code)
        # Isso cobre 2 casos:
        #   a) acc_id de OUTRA company que consolida no mesmo code, sem movimento no mes
        #   b) Conta com saldo inicial SEM movimento no mes (igual ao loop anterior)
        for acc_id, saldo_ini in saldos_iniciais_por_acc.items():
            if acc_id in acc_ids_inicial_processados:
                continue  # ja somado acima
            code = id_to_code.get(acc_id)
            if not code:
                continue
            slot = por_code.setdefault(code, {
                'saldo_inicial': 0, 'debit': 0, 'credit': 0, 'saldo_final': 0
            })
            slot['saldo_inicial'] += saldo_ini
            slot['saldo_final'] += saldo_ini  # sem movimento = saldo final = inicial
            acc_ids_inicial_processados.add(acc_id)

        resultado[cursor_mes.strftime('%Y-%m')] = {
            'date_ini': cursor_mes,
            'date_fim': ult_dia_mes,
            'por_code': por_code,
        }

        cursor_mes = prox_mes

    logger.info(
        f'[SPED ECD] Saldos periodicos mensais: {len(resultado)} meses processados'
    )
    return resultado


def _read_group_balance(
    connection,
    domain_extra: List = None,
    with_debit_credit: bool = False,
) -> Union[dict, list]:
    """
    Helper: read_group de account.move.line agrupado por account_id, com filtro
    multi-company COMPANIES_ECD.

    Returns:
        Se with_debit_credit=False: dict {account_id: balance_sum}
        Se with_debit_credit=True: list de tuplas (account_id, debit, credit, balance)
    """
    domain = [
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', COMPANIES_ECD],
    ]
    if domain_extra:
        domain.extend(domain_extra)

    fields = ['account_id', 'balance:sum']
    if with_debit_credit:
        fields = ['account_id', 'debit:sum', 'credit:sum', 'balance:sum']

    result = connection.execute_kw(
        'account.move.line', 'read_group',
        [domain],
        {'fields': fields, 'groupby': ['account_id'], 'lazy': False},
        timeout_override=TIMEOUT_QUERY_PESADA,
    )

    if with_debit_credit:
        out = []
        for grupo in result:
            acc = grupo.get('account_id')
            if not acc:
                continue
            acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
            out.append((
                acc_id,
                grupo.get('debit', 0) or 0,
                grupo.get('credit', 0) or 0,
                grupo.get('balance', 0) or 0,
            ))
        return out
    else:
        out = {}
        for grupo in result:
            acc = grupo.get('account_id')
            if not acc:
                continue
            acc_id = acc[0] if isinstance(acc, (list, tuple)) else acc
            out[acc_id] = grupo.get('balance', 0) or 0
        return out


# ============================================================
# BALANCO E DRE CONSOLIDADOS (R5 corrigido)
# ============================================================

def calcular_balanco_consolidado(
    connection,
    date_fim: date,
    plano_consolidado: List[dict],
    id_to_code: Dict[int, str],
) -> Dict[str, dict]:
    """
    Balanco Patrimonial consolidado das 3 companies.
    Soma POR CODE (mitigacao R5).

    Returns: {code: {'code', 'name', 'account_type', 'saldo'}}
    """
    # Acumulado ate date_fim para contas patrimoniais
    saldos_por_acc = _read_group_balance(
        connection,
        domain_extra=[['date', '<=', date_fim.strftime('%Y-%m-%d')]],
    )

    # Mapa code -> dados (filtrar so patrimoniais)
    code_to_dados = {
        c['code']: c for c in plano_consolidado
        if c.get('tipo') == 'A' and c.get('account_type') in ACCOUNT_TYPES_PATRIMONIAIS
    }

    # Consolidar por code
    balanco = {}
    for acc_id, balance in saldos_por_acc.items():
        code = id_to_code.get(acc_id)
        if not code or code not in code_to_dados:
            continue
        dados = code_to_dados[code]
        slot = balanco.setdefault(code, {
            'code': code,
            'name': dados['name'],
            'account_type': dados['account_type'],
            'saldo': 0,
        })
        slot['saldo'] += balance

    return balanco


def calcular_dre_consolidado(
    connection,
    date_ini: date,
    date_fim: date,
    plano_consolidado: List[dict],
    id_to_code: Dict[int, str],
) -> Dict[str, dict]:
    """
    DRE consolidado das 3 companies para o periodo.
    Soma POR CODE (mitigacao R5).
    """
    # Movimento do periodo para contas de resultado
    movs = _read_group_balance(
        connection,
        domain_extra=[
            ['date', '>=', date_ini.strftime('%Y-%m-%d')],
            ['date', '<=', date_fim.strftime('%Y-%m-%d')],
        ],
        with_debit_credit=True,
    )

    code_to_dados = {
        c['code']: c for c in plano_consolidado
        if c.get('tipo') == 'A' and c.get('account_type') in ACCOUNT_TYPES_RESULTADO
    }

    dre = {}
    for tupla in movs:
        acc_id, _debit, _credit, balance_val = tupla
        code = id_to_code.get(acc_id)
        if not code or code not in code_to_dados:
            continue
        dados = code_to_dados[code]
        slot = dre.setdefault(code, {
            'code': code,
            'name': dados['name'],
            'account_type': dados['account_type'],
            'saldo': 0,
        })
        slot['saldo'] += balance_val

    return dre


def calcular_saldos_resultado_encerramento(
    connection,
    date_fim: date,
    plano_consolidado: List[dict],
    id_to_code: Dict[int, str],
) -> Dict[str, dict]:
    """
    Saldos das contas de resultado ANTES do encerramento (I355).
    Apenas se date_fim = 31/12 (encerramento). Mitigacao R7.
    """
    if not (date_fim.month == 12 and date_fim.day == 31):
        return {}

    # Acumulado do exercicio (1/1 a 31/12) para contas de resultado
    date_ini_exercicio = date(date_fim.year, 1, 1)
    return calcular_dre_consolidado(connection, date_ini_exercicio, date_fim,
                                     plano_consolidado, id_to_code)


# ============================================================
# LANCAMENTOS (STREAMING — mitigacao R3)
# ============================================================

# NOTA: V1 stream_lancamentos_consolidados removido. Use stream_lancamentos_consolidados_v11
# que aceita id_to_code_ccus e partner_id_to_cod_part para CCUS e participantes (V1.1).


def _extrair_distribuicao_ccus(analytic_distribution, id_to_code_ccus: Dict[int, str]) -> List[Tuple[str, float]]:
    """
    Extrai TODA a distribuicao de CCUS de uma analytic_distribution.
    V1.2: respeita N-1 com % conforme dados Odoo.

    Formato Odoo: {'<analytic_id>': <percentual>}
    Ex: {'1186': 100.0} -> [('111041', 100.0)]
    Ex: {'1342': 50.0, '1343': 50.0} -> [('118005', 50.0), ('118105', 50.0)]
    Ex: 13 centros com 7.7% cada -> 13 tuplas

    Returns:
        Lista de tuplas [(cod_ccus, percentual), ...] ordenada por percentual desc
        Lista vazia se sem CCUS
    """
    if not analytic_distribution or not isinstance(analytic_distribution, dict):
        return []

    resultado = []
    for id_str, pct in analytic_distribution.items():
        try:
            aid = int(id_str)
            pct_num = float(pct or 0)
            if pct_num <= 0:
                continue
            cod_ccus = id_to_code_ccus.get(aid)
            if cod_ccus:
                resultado.append((cod_ccus, pct_num))
        except (ValueError, TypeError):
            continue

    # Ordenar por % desc (maior primeiro) para priorizar centros principais em logs/auditoria
    resultado.sort(key=lambda x: -x[1])
    return resultado


# ============================================================
# CENTROS DE CUSTO CONSOLIDADOS (V1.1 — mitigacao limitacao)
# ============================================================

def buscar_centros_custo_consolidados(connection) -> Tuple[List[dict], Dict[int, str]]:
    """
    Busca centros de custo (account.analytic.account) das 3 companies, deduplica
    por code, gera mapa id_to_code para consolidacao.

    Returns:
        (plano_ccus, id_to_code_ccus)
        - plano_ccus: lista de dicts {code, name, plan_name, dt_alt}
        - id_to_code_ccus: dict {analytic_id: code}
    """
    # Mitigacao code-review BLOCKER #4: paginado
    todos = _buscar_paginado(
        connection, 'account.analytic.account',
        [['company_id', 'in', COMPANIES_ECD]],
        ['id', 'code', 'name', 'plan_id', 'company_id', 'create_date'],
    )

    codes_dedupe = {}  # code -> dados
    id_to_code = {}    # analytic_id -> code

    for c in todos:
        code = c.get('code') or f'CCUS{c["id"]}'  # fallback se sem code
        id_to_code[c['id']] = code

        if code not in codes_dedupe:
            plan_name = ''
            if c.get('plan_id') and isinstance(c['plan_id'], (list, tuple)):
                plan_name = c['plan_id'][1] or ''
            codes_dedupe[code] = {
                'code': code,
                'name': c.get('name', ''),
                'plan_name': plan_name,
                'dt_alt': (c.get('create_date') or '2010-01-01')[:10],
            }

    plano_ccus = sorted(codes_dedupe.values(), key=lambda x: x['code'])
    logger.info(
        f'[SPED ECD] CCUS consolidado: {len(plano_ccus)} codes unicos, '
        f'{len(id_to_code)} analytic_ids mapeados'
    )
    return plano_ccus, id_to_code


# ============================================================
# PARTICIPANTES — RES.PARTNER ATIVOS NO PERIODO (V1.1)
# ============================================================

def buscar_participantes_periodo(
    connection,
    date_ini: date,
    date_fim: date,
) -> List[dict]:
    """
    Busca res.partner que tem lancamentos contabeis no periodo (para registro 0150).
    Filtra apenas partners com lines em account.move.line das 3 companies.

    Returns:
        Lista de dicts {id, name, cnpj_cpf, cod_pais, ie, im, suframa,
                       endereco, num, complemento, bairro, municipio, uf}
    """
    # 1. Buscar partner_ids que tem lines no periodo
    ids_set = set()
    last_id = 0
    BATCH = 5000

    while True:
        domain = [
            ['date', '>=', date_ini.strftime('%Y-%m-%d')],
            ['date', '<=', date_fim.strftime('%Y-%m-%d')],
            ['parent_state', '=', 'posted'],
            ['company_id', 'in', COMPANIES_ECD],
            ['partner_id', '!=', False],
            ['id', '>', last_id],
        ]
        lote = connection.execute_kw(
            'account.move.line', 'search_read', [domain],
            {'fields': ['id', 'partner_id'], 'limit': BATCH, 'order': 'id asc'},
            timeout_override=TIMEOUT_QUERY_PESADA,
        )
        if not lote:
            break
        for ln in lote:
            pid = ln['partner_id']
            if pid and isinstance(pid, (list, tuple)) and pid[0]:
                ids_set.add(pid[0])
            last_id = ln['id']
        if len(lote) < BATCH:
            break

    if not ids_set:
        logger.info('[SPED ECD] Nenhum partner com lancamentos no periodo')
        return []

    # 2. Buscar dados completos dos partners (paginado)
    partners = []
    ids_lista = list(ids_set)
    BATCH_PARTNER = 500
    for i in range(0, len(ids_lista), BATCH_PARTNER):
        sub_ids = ids_lista[i:i + BATCH_PARTNER]
        partners_lote = connection.execute_kw(
            'res.partner', 'read', [sub_ids],
            {'fields': [
                'id', 'name', 'is_company', 'l10n_br_cnpj', 'l10n_br_cpf', 'vat',
                'l10n_br_ie', 'l10n_br_im',
                'street', 'street2', 'l10n_br_endereco_numero', 'l10n_br_endereco_bairro',
                'city', 'state_id', 'country_id', 'zip',
                'l10n_br_municipio_id',
            ]},
            timeout_override=TIMEOUT_QUERY_SIMPLES,
        )
        partners.extend(partners_lote)

    # 2.5. Pre-carregar TODOS os municipios em 1 batch (mitigacao code-review HIGH #8)
    # Evita N+1 query de 1 leitura por partner
    mun_ids_set = set()
    for p in partners:
        mun = p.get('l10n_br_municipio_id')
        if mun and isinstance(mun, (list, tuple)) and mun[0]:
            mun_ids_set.add(mun[0])

    cod_mun_cache = {}
    if mun_ids_set:
        try:
            mun_lote = connection.execute_kw(
                'l10n_br_base.municipio', 'read', [list(mun_ids_set)],
                {'fields': ['id', 'l10n_br_ibge_code']},
                timeout_override=TIMEOUT_QUERY_SIMPLES,
            )
            cod_mun_cache = {m['id']: (m.get('l10n_br_ibge_code') or '') for m in mun_lote}
        except Exception as e:
            logger.warning(f'[SPED ECD] Erro batch read municipios: {e}')

    # 3. Normalizar dados para 0150
    resultado = []
    for p in partners:
        # CNPJ/CPF (limpo, so digitos)
        doc = (p.get('l10n_br_cnpj') or p.get('l10n_br_cpf') or p.get('vat') or '').strip()
        doc_limpo = ''.join(c for c in doc if c.isdigit())
        if not doc_limpo:
            continue  # 0150 exige doc

        # COD_PAIS: 1058 = BRASIL (default)
        country_id = p.get('country_id')
        cod_pais = '01058'  # default Brasil
        if country_id and isinstance(country_id, (list, tuple)) and country_id[0] != 31:
            cod_pais = ''  # exterior — opcional

        # COD_MUN (IBGE) — usa cache (sem N+1)
        cod_mun = ''
        mun = p.get('l10n_br_municipio_id')
        if mun and isinstance(mun, (list, tuple)) and mun[0]:
            cod_mun = cod_mun_cache.get(mun[0], '')

        resultado.append({
            'id': p['id'],
            'cod_part': doc_limpo,                          # COD_PART = CNPJ/CPF (sem mascara)
            'name': p.get('name', ''),
            'cod_pais': cod_pais,
            'cnpj_cpf': doc_limpo,
            'ie': (p.get('l10n_br_ie') or '').strip(),
            'cod_mun': cod_mun,
            'suframa': '',                                  # NACOM nao usa SUFRAMA
            'endereco': (p.get('street') or '')[:60],
            'num': (p.get('l10n_br_endereco_numero') or '')[:10],
            'complemento': (p.get('street2') or '')[:60],
            'bairro': (p.get('l10n_br_endereco_bairro') or '')[:60],
            'is_company': p.get('is_company', False),
        })

    logger.info(f'[SPED ECD] Participantes ativos no periodo: {len(resultado)}')
    return resultado


# ============================================================
# STREAM DE LANCAMENTOS COM CCUS (V1.1)
# ============================================================

def stream_lancamentos_consolidados_v11(
    connection,
    date_ini: date,
    date_fim: date,
    id_to_code: Dict[int, str],
    id_to_code_ccus: Dict[int, str],
    partner_id_to_cod_part: Dict[int, str],
    progresso_callback=None,
) -> Generator[dict, None, None]:
    """
    Generator V1.1: produz lancamentos com CCUS + partner_id resolvido para COD_PART.

    Inclui campo `analytic_distribution` na busca para extrair CCUS por linha.
    """
    domain = [
        ['date', '>=', date_ini.strftime('%Y-%m-%d')],
        ['date', '<=', date_fim.strftime('%Y-%m-%d')],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', COMPANIES_ECD],
    ]

    fields = [
        'id', 'date', 'move_id', 'move_name', 'account_id',
        'partner_id', 'debit', 'credit', 'name', 'ref',
        'analytic_distribution',  # V1.1: campo CCUS
    ]

    last_id = 0
    move_atual = None
    lines_acumulando = []
    num_lcto = 0
    total_lines = 0

    while True:
        domain_cursor = domain + [['id', '>', last_id]]

        lote = connection.execute_kw(
            'account.move.line', 'search_read',
            [domain_cursor],
            {
                'fields': fields,
                'limit': BATCH_SIZE_LANCAMENTOS,
                'order': 'move_id asc, id asc',
            },
            timeout_override=TIMEOUT_QUERY_PESADA,
        )

        if not lote:
            break

        for line in lote:
            move_field = line.get('move_id')
            mid = move_field[0] if isinstance(move_field, (list, tuple)) else move_field
            if not mid:
                continue

            if move_atual is None:
                move_atual = mid

            if mid != move_atual:
                if lines_acumulando:
                    num_lcto += 1
                    yield _construir_lancamento_v11(
                        num_lcto, lines_acumulando, id_to_code,
                        id_to_code_ccus, partner_id_to_cod_part
                    )
                lines_acumulando = []
                move_atual = mid

            lines_acumulando.append(line)
            last_id = line['id']
            total_lines += 1

        if progresso_callback and total_lines % 5000 == 0:
            progresso_callback({
                'lines_processadas': total_lines,
                'num_lcto_atual': num_lcto,
            })

        if len(lote) < BATCH_SIZE_LANCAMENTOS:
            break

    if lines_acumulando:
        num_lcto += 1
        yield _construir_lancamento_v11(
            num_lcto, lines_acumulando, id_to_code,
            id_to_code_ccus, partner_id_to_cod_part
        )

    logger.info(
        f'[SPED ECD V1.1] Stream lancamentos completo: {total_lines} lines, '
        f'{num_lcto} lancamentos consolidados'
    )


def _construir_lancamento_v11(
    num_lcto: int,
    lines: List[dict],
    id_to_code: Dict[int, str],
    id_to_code_ccus: Dict[int, str],
    partner_id_to_cod_part: Dict[int, str],
) -> dict:
    """
    Versao V1.2: inclui ccus_distribuicao COMPLETA (lista) + cod_part.

    Cada line traz `ccus_distribuicao` como lista de tuplas (cod_ccus, percentual).
    construir_I200_I250 ira gerar N partidas I250 conforme split.
    """
    primeira = lines[0]
    return {
        'num': num_lcto,
        'date': primeira.get('date'),
        'move_name': primeira.get('move_name', ''),
        'lines': [
            {
                'code': id_to_code.get(
                    ln['account_id'][0] if isinstance(ln.get('account_id'), (list, tuple)) else ln.get('account_id'),
                    '999'
                ),
                # V1.2: distribuicao COMPLETA (lista de tuplas)
                'ccus_distribuicao': _extrair_distribuicao_ccus(
                    ln.get('analytic_distribution'), id_to_code_ccus
                ),
                'cod_part': partner_id_to_cod_part.get(
                    ln['partner_id'][0] if isinstance(ln.get('partner_id'), (list, tuple)) else None,
                    ''
                ) if ln.get('partner_id') else '',
                'debit': float(ln.get('debit') or 0),
                'credit': float(ln.get('credit') or 0),
                'name': ln.get('name') or '',
                'ref': ln.get('ref') or '',
                'partner_name': (
                    ln['partner_id'][1] if ln.get('partner_id') and isinstance(ln['partner_id'], (list, tuple))
                    else ''
                ),
            }
            for ln in lines
        ],
    }
