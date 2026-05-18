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
    saldo_natural_dc,
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
    nome_municipio = ''
    municipio_field = co.get('l10n_br_municipio_id')
    if municipio_field and isinstance(municipio_field, (list, tuple)) and municipio_field[0]:
        # Many2one retorna [id, "Nome (UF)"] — extrair direto, sem read separado.
        # Ex: [5570, "Sao Paulo (SP)"]. Modelo l10n_br_base.municipio nao existe
        # no Odoo CIEL IT — IBGE vem de outro caminho.
        if len(municipio_field) > 1 and municipio_field[1]:
            display = municipio_field[1] or ''
            # Separar "Nome" de "(UF)"
            if '(' in display:
                nome_municipio = display.split('(')[0].strip()
                uf_extraida = display.split('(')[-1].rstrip(')')[:2].strip()
                if uf_extraida:
                    uf = uf_extraida
            else:
                nome_municipio = display.strip()

        # Buscar codigo IBGE no modelo CIEL IT (l10n_br_ciel_it_account.res.municipio)
        try:
            mun_list = connection.execute_kw(
                'l10n_br_ciel_it_account.res.municipio', 'read',
                [[municipio_field[0]]],
                {'fields': ['codigo_ibge']},
                timeout_override=TIMEOUT_QUERY_SIMPLES,
            )
            if mun_list:
                cod_mun = str(mun_list[0].get('codigo_ibge', '') or '')
        except Exception as e:
            logger.warning(f'Erro ao buscar IBGE matriz: {e}')

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
        'nome_municipio': nome_municipio,
        'uf': uf,
    }


# ============================================================
# PLANO DE CONTAS CONSOLIDADO (R12 + R5)
# ============================================================

def buscar_plano_contas_consolidado(
    connection, companies: List[int] = None
) -> Tuple[List[dict], Dict[int, str]]:
    """
    Busca plano de contas das companies passadas (default = COMPANIES_ECD),
    deduplica por code, gera hierarquia sintetica e mapa id_to_code para consolidacao.

    Mitigacao R12: busca FB primeiro (autoritativo para nomes), completa com SC/CD.
    Mitigacao R5: id_to_code mapeia TODOS os account_ids das companies passadas para 1 code.

    Args:
        companies: lista de company_ids; default = COMPANIES_ECD.

    Returns:
        (plano_consolidado, id_to_code)
        - plano_consolidado: lista ordenada por code, com sinteticas + analiticas
        - id_to_code: dict {account_id: code} para consolidacao
    """
    comps = companies if companies is not None else COMPANIES_ECD

    plano_dedupe = {}  # code -> dados conta
    id_to_code = {}    # account_id -> code (consolidacao R5)

    # Campos consultados — incluindo mapeamento Odoo CIEL IT (V1.1):
    # - l10n_br_conta_referencial: codigo do plano referencial Receita (87% cobertura)
    # - l10n_br_cod_nat: codigo da natureza Receita (99% cobertura)
    CAMPOS_PLANO = [
        'id', 'code', 'name', 'account_type', 'company_id', 'create_date',
        'l10n_br_conta_referencial', 'l10n_br_cod_nat',
    ]

    # 1. Buscar FB (matriz) primeiro SE estiver nas companies passadas.
    # Mitigacao code-review BLOCKER #4: paginacao ID-cursor (sem limite truncar)
    matriz_in_scope = COMPANY_MATRIZ_ID in comps
    if matriz_in_scope:
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

    # 2. Completar com demais companies (apenas codes que NAO existem em FB ou
    # quando FB nao esta no escopo)
    demais = [cid for cid in comps if cid != COMPANY_MATRIZ_ID]
    for cid in demais:
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


def filtrar_plano_por_movimento(plano_consolidado: List[dict],
                                  saldos_mensais: dict) -> List[dict]:
    """
    V25 (CAT 25) — Filtra o plano para emitir SO contas utilizadas no periodo.

    Manual ECD Leiaute 9 (Registro I050): "Devem ser informadas as contas
    analiticas UTILIZADAS pela escrituracao no periodo."

    Utilizada = em algum mes do periodo:
        - saldo_inicial != 0, OU
        - debit > 0, OU
        - credit > 0, OU
        - saldo_final != 0

    Sinteticas: mantidas SO se tiverem alguma analitica descendente utilizada
    (propagacao via cod_sup ate raiz).

    Reduz ruido PVA: contas zeradas/inativas com cadastro Odoo errado (cod_ref,
    cod_nat conflitante) deixam de gerar erros CAT 2, 19, 21, 22.

    Comparativo (Odoo NACOM 2024 Jul-Dez):
        Total codes plano: 692
        Codes COM movimento: 293 (similar ao SPED da contadora: 291 analiticas)
        Codes SEM movimento (filtrados): 399

    Args:
        plano_consolidado: plano completo (analiticas + sinteticas geradas)
        saldos_mensais: dict {YYYY-MM: {'por_code': {code: {saldo_inicial, debit, credit, saldo_final}}}}

    Returns:
        plano filtrado (mesma estrutura, com analiticas utilizadas + sinteticas necessarias)
    """
    if not saldos_mensais:
        return plano_consolidado

    # 1. Identificar codes ANALITICOS utilizados
    codes_utilizados = set()
    for mes in saldos_mensais.values():
        for code, sd in (mes.get('por_code') or {}).items():
            if (abs(sd.get('saldo_inicial', 0) or 0) > 0.01 or
                abs(sd.get('debit', 0) or 0) > 0.01 or
                abs(sd.get('credit', 0) or 0) > 0.01 or
                abs(sd.get('saldo_final', 0) or 0) > 0.01):
                codes_utilizados.add(code)

    plano_by_code = {c['code']: c for c in plano_consolidado}

    # 2. Propagar para sinteticas ancestrais (qualquer code ancestral de analitica utilizada)
    sinteticas_validas = set()
    for code in codes_utilizados:
        c = plano_by_code.get(code, {})
        cur = c.get('cod_sup', '')
        visitados = set()
        while cur and cur not in visitados:
            visitados.add(cur)
            sinteticas_validas.add(cur)
            sup = plano_by_code.get(cur, {})
            cur = sup.get('cod_sup', '')

    # 3. Filtrar plano: analiticas utilizadas + sinteticas com filhas utilizadas
    plano_filtrado = [
        c for c in plano_consolidado
        if (c.get('tipo') == 'A' and c['code'] in codes_utilizados) or
           (c.get('tipo') == 'S' and c['code'] in sinteticas_validas)
    ]

    n_anal_total = sum(1 for c in plano_consolidado if c.get('tipo') == 'A')
    n_anal_filtrado = sum(1 for c in plano_filtrado if c.get('tipo') == 'A')
    n_sint_total = sum(1 for c in plano_consolidado if c.get('tipo') == 'S')
    n_sint_filtrado = sum(1 for c in plano_filtrado if c.get('tipo') == 'S')
    logger.info(
        f'[SPED ECD V25] Plano filtrado por movimento: '
        f'analiticas {n_anal_total} -> {n_anal_filtrado} (-{n_anal_total - n_anal_filtrado}), '
        f'sinteticas {n_sint_total} -> {n_sint_filtrado} (-{n_sint_total - n_sint_filtrado})'
    )

    return plano_filtrado


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
    companies: List[int] = None,
) -> Dict[str, dict]:
    """
    Calcula saldos mensais (I150/I155) para o periodo, consolidando POR CODE.

    Args:
        companies: lista de company_ids; default = COMPANIES_ECD.

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
            companies=companies,
        )

        # Movimento do mes (entre cursor e ult_dia_mes)
        movimentos_por_acc = _read_group_balance(
            connection,
            domain_extra=[
                ['date', '>=', cursor_mes.strftime('%Y-%m-%d')],
                ['date', '<=', ult_dia_mes.strftime('%Y-%m-%d')],
            ],
            with_debit_credit=True,
            companies=companies,
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
    companies: List[int] = None,
) -> Union[dict, list]:
    """
    Helper: read_group de account.move.line agrupado por account_id, com filtro
    multi-company.

    Args:
        companies: lista de company_ids; default = COMPANIES_ECD (3 companies).

    Returns:
        Se with_debit_credit=False: dict {account_id: balance_sum}
        Se with_debit_credit=True: list de tuplas (account_id, debit, credit, balance)
    """
    comps = companies if companies is not None else COMPANIES_ECD
    domain = [
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', comps],
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
    companies: List[int] = None,
    date_ini: date = None,
) -> Dict[str, dict]:
    """
    Balanco Patrimonial consolidado das companies passadas (default = 3 companies).
    Soma POR CODE (mitigacao R5).

    V1.6: agora retorna SALDO INICIAL e FINAL.
        - saldo_inicial: acumulado ate date_ini - 1 (saldo de abertura do periodo)
        - saldo: acumulado ate date_fim (saldo de encerramento — mantido para compat)
        - saldo_final: alias de saldo

    Args:
        date_ini: data inicio do periodo. Se omitida, saldo_inicial sera 0
                  (comportamento legado).

    Returns: {code: {'code', 'name', 'account_type', 'saldo', 'saldo_inicial', 'saldo_final'}}
    """
    # Acumulado ate date_fim (saldo final do periodo)
    saldos_final_por_acc = _read_group_balance(
        connection,
        domain_extra=[['date', '<=', date_fim.strftime('%Y-%m-%d')]],
        companies=companies,
    )

    # V1.6: Acumulado ate date_ini - 1 (saldo inicial do periodo)
    saldos_inicial_por_acc = {}
    if date_ini is not None:
        date_anterior = date_ini - timedelta(days=1)
        saldos_inicial_por_acc = _read_group_balance(
            connection,
            domain_extra=[['date', '<=', date_anterior.strftime('%Y-%m-%d')]],
            companies=companies,
        )

    # Mapa code -> dados (filtrar so patrimoniais)
    code_to_dados = {
        c['code']: c for c in plano_consolidado
        if c.get('tipo') == 'A' and c.get('account_type') in ACCOUNT_TYPES_PATRIMONIAIS
    }

    # Consolidar por code
    balanco = {}
    # 1. Saldo final
    for acc_id, balance in saldos_final_por_acc.items():
        code = id_to_code.get(acc_id)
        if not code or code not in code_to_dados:
            continue
        dados = code_to_dados[code]
        slot = balanco.setdefault(code, {
            'code': code,
            'name': dados['name'],
            'account_type': dados['account_type'],
            'saldo': 0,
            'saldo_inicial': 0,
            'saldo_final': 0,
        })
        slot['saldo'] += balance
        slot['saldo_final'] += balance

    # 2. Saldo inicial (V1.6)
    for acc_id, balance in saldos_inicial_por_acc.items():
        code = id_to_code.get(acc_id)
        if not code or code not in code_to_dados:
            continue
        dados = code_to_dados[code]
        slot = balanco.setdefault(code, {
            'code': code,
            'name': dados['name'],
            'account_type': dados['account_type'],
            'saldo': 0,
            'saldo_inicial': 0,
            'saldo_final': 0,
        })
        slot['saldo_inicial'] += balance

    return balanco


def calcular_dre_consolidado(
    connection,
    date_ini: date,
    date_fim: date,
    plano_consolidado: List[dict],
    id_to_code: Dict[int, str],
    companies: List[int] = None,
) -> Dict[str, dict]:
    """
    DRE consolidado das companies passadas (default = 3 companies) para o periodo.
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
        companies=companies,
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
    date_fim: date,
    plano_consolidado: List[dict],
    saldos_mensais: Dict,
) -> Dict[str, dict]:
    """
    Saldos das contas de resultado ANTES do encerramento (I355).
    Apenas se date_fim = 31/12 (encerramento). Mitigacao R7.

    V32 (CAT 26 fix 2026-05-16) — Manual ECD Leiaute 9 oficial (pag 157):
    "O registro I355 traz os detalhes das contas de resultado antes do
    encerramento, isto e, o valor do saldo final de cada conta ANTES dos
    lancamentos de encerramento."

    PVA REGRA_VALIDA_SALDO_COM_DRE (J150): "Linhas D: VL_CTA_FIN = soma I355
    calculada via COD_AGL no I052" — exige I355 com saldo real ANTES do
    encerramento (e nao zero pos-encerramento).

    HISTORICO de erros nesta funcao:
    - V31: filtro cod_nat='04' (Manual oficial) — 12 contas 5101* sairam OK.
      MAS contas reais 3xxx Receita/Despesa ficaram com VL_CTA=0 porque
      `_read_group_balance` retornava balance_val do exercicio inteiro,
      que JA INCLUI lancamento de encerramento Odoo (zerando a conta).
      PVA V31 reportou 4 erros CAT 26 (J150|9.1.1, 9.1.2, 9.2.1, 9.2.2
      != soma I355).

    - V32: refatora para derivar I355 do `saldos_mensais` (I155 ja calculado).
      Premissa observada na NACOM: encerramento Odoo e lancamento UNICO em
      31/12 no lado OPOSTO ao saldo natural da conta. Logo:
          Receita (natural C): encerramento e DEB.
              saldo_antes_enc = saldo_inicial(mes12) + credito(mes12)
          Despesa (natural D): encerramento e CRED.
              saldo_antes_enc = saldo_inicial(mes12) + debito(mes12)

    Validado contra contadora (ground truth aceito RFB) e contra I155:
      - 3101010001 VENDA (C): 175.910.143,40 + 17.949.846,03 = 193.859.989,43
        (contadora I355: 193.859.989,43 C — exato)
      - 3201000001 CMV (D):     49.602.366,61 +  1.268.021,32 =  50.870.387,93
        (I155 cred dez = 50.870.387,93 que e o valor do lcto encerramento)
      - 3102010001 DEVOL (D):  10.232.785,93 +  1.293.057,19 =  11.525.843,12
        (I155 cred dez = 11.525.843,12 que e o lcto encerramento)

    Filtro Manual ECD pag 159 REGRA_CONTA_RESULTADO: cod_nat='04' exclusivo.

    Args:
        date_fim: data fim do periodo. Deve ser 31/12 para emitir I355.
        plano_consolidado: plano de contas consolidado (3 companies).
        saldos_mensais: dict {YYYY-MM: {por_code: {code: {saldo_inicial, debit,
                        credit, saldo_final}}}} ja calculado em
                        `calcular_saldos_periodicos_mensais`.

    Returns:
        dict {code: {'code', 'name', 'account_type', 'cod_nat_odoo', 'saldo'}}
        onde 'saldo' e sempre POSITIVO (sinal vem do account_type via
        construir_I350_I355 → saldo_natural_dc).
    """
    if not (date_fim.month == 12 and date_fim.day == 31):
        return {}

    mes12_key = date_fim.strftime('%Y-%m')
    if mes12_key not in saldos_mensais:
        logger.warning(
            f'[SPED ECD V32] I355: mes {mes12_key} ausente em saldos_mensais — '
            f'I355 nao sera emitido (esperado saldos_mensais do mes 12).'
        )
        return {}

    por_code_dez = saldos_mensais[mes12_key].get('por_code', {})

    # Filtro Manual ECD pag 159 REGRA_CONTA_RESULTADO: cod_nat='04' exclusivo
    code_to_dados = {
        c['code']: c for c in plano_consolidado
        if c.get('tipo') == 'A'
        and (c.get('cod_nat_odoo') or '').strip() == '04'
    }

    saldos = {}
    for code, dados in code_to_dados.items():
        sd_dez = por_code_dez.get(code, {})
        saldo_ini = float(sd_dez.get('saldo_inicial', 0) or 0)
        deb = float(sd_dez.get('debit', 0) or 0)
        cred = float(sd_dez.get('credit', 0) or 0)

        # V32: saldo ANTES encerramento via I155 mes 12 (Manual ECD pag 157)
        # Premissa: encerramento Odoo em 31/12 sempre no lado OPOSTO ao natural.
        # Para receita (natural C): encerramento e DEB. saldo_antes = saldo_ini + cred.
        # Para despesa (natural D): encerramento e CRED. saldo_antes = saldo_ini + deb.
        natural = saldo_natural_dc(dados.get('account_type', ''))
        if natural == 'C':
            saldo_antes_enc = abs(saldo_ini) + cred
        else:
            saldo_antes_enc = abs(saldo_ini) + deb

        # Pular contas com saldo zero (sem movimento no exercicio)
        if abs(saldo_antes_enc) < 0.01:
            continue

        saldos[code] = {
            'code': code,
            'name': dados['name'],
            'account_type': dados['account_type'],
            'cod_nat_odoo': dados.get('cod_nat_odoo', ''),
            'saldo': saldo_antes_enc,  # sempre positivo (sinal via construir_I350_I355)
        }

    logger.info(
        f'[SPED ECD V32] I355: {len(code_to_dados)} codes elegiveis (cod_nat=04), '
        f'{len(saldos)} com saldo > 0 ANTES encerramento (derivado de I155 mes 12)'
    )
    return saldos


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

def buscar_centros_custo_consolidados(
    connection, companies: List[int] = None
) -> Tuple[List[dict], Dict[int, str]]:
    """
    Busca centros de custo (account.analytic.account) das 3 companies, deduplica
    por code, gera mapa id_to_code para consolidacao.

    Returns:
        (plano_ccus, id_to_code_ccus)
        - plano_ccus: lista de dicts {code, name, plan_name, dt_alt}
        - id_to_code_ccus: dict {analytic_id: code}
    """
    comps = companies if companies is not None else COMPANIES_ECD
    # Mitigacao code-review BLOCKER #4: paginado
    todos = _buscar_paginado(
        connection, 'account.analytic.account',
        [['company_id', 'in', comps]],
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
    # 1. Buscar partner_ids distintos que tem lines no periodo via read_group.
    # OTIMIZACAO: substitui search_read paginado (que trafegava centenas de milhares
    # de linhas via XML-RPC so para extrair partner_ids unicos) por UMA chamada
    # read_group que agrupa direto no PostgreSQL do Odoo.
    # Antes: ~213s para 6 meses (~82% do tempo total do job).
    # Depois esperado: ~3-10s.
    domain = [
        ['date', '>=', date_ini.strftime('%Y-%m-%d')],
        ['date', '<=', date_fim.strftime('%Y-%m-%d')],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', COMPANIES_ECD],
        ['partner_id', '!=', False],
    ]
    grupos = connection.execute_kw(
        'account.move.line', 'read_group',
        [domain],
        {'fields': ['partner_id'], 'groupby': ['partner_id'], 'lazy': False},
        timeout_override=TIMEOUT_QUERY_PESADA,
    )
    ids_set = {
        g['partner_id'][0]
        for g in grupos
        if g.get('partner_id') and isinstance(g['partner_id'], (list, tuple)) and g['partner_id'][0]
    }

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
                'l10n_br_ciel_it_account.res.municipio', 'read', [list(mun_ids_set)],
                {'fields': ['id', 'codigo_ibge']},
                timeout_override=TIMEOUT_QUERY_SIMPLES,
            )
            cod_mun_cache = {m['id']: str(m.get('codigo_ibge') or '') for m in mun_lote}
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
    company_ids: List[int] = None,
) -> Generator[dict, None, None]:
    """
    Generator V1.6: produz lancamentos INDIVIDUAIS (1 yield por account.move)
    com CCUS + partner_id resolvido para COD_PART.

    BUG HISTORICO CORRIGIDO (2026-05-14):
    A versao anterior usava cursor 'id > last_id' com ORDER BY 'move_id asc, id asc'.
    Como o id da line NAO e crescente quando ordenado por move_id, batches subsequentes
    PULAVAM lines com id baixo mas move_id alto. Resultado: ~98% dos lancamentos eram
    perdidos (gerava 2049 I200 quando deveria gerar 60000+).

    Nova estrategia:
    1. Listar TODOS os move_ids do periodo (1 query search com order='id asc')
    2. Iterar em chunks de N moves
    3. Para cada chunk, ler todas as account.move.line dos moves (em 1 query)
    4. Agrupar por move_id e emitir 1 lancamento por move (mantem ordem cronologica)

    Sem cursor problematico — paginacao por chunks de move_ids garante completude.

    Args:
        company_ids: lista de company_ids; default = COMPANIES_ECD (3 companies).
                     Para gerar so FB use [1]; para SC use [3]; para CD use [4].
    """
    companies = company_ids if company_ids is not None else COMPANIES_ECD

    fields = [
        'id', 'date', 'move_id', 'move_name', 'account_id',
        'partner_id', 'debit', 'credit', 'name', 'ref',
        'analytic_distribution',
    ]

    # ============================================================
    # Step 1: listar TODOS os move_ids no periodo (1 query search)
    # ============================================================
    domain_moves = [
        ['date', '>=', date_ini.strftime('%Y-%m-%d')],
        ['date', '<=', date_fim.strftime('%Y-%m-%d')],
        ['state', '=', 'posted'],
        ['company_id', 'in', companies],
    ]
    move_ids = connection.execute_kw(
        'account.move', 'search',
        [domain_moves],
        {'order': 'id asc'},
        timeout_override=TIMEOUT_QUERY_PESADA,
    )
    total_moves = len(move_ids)
    logger.info(f'[SPED ECD V1.6] {total_moves} account.move no periodo (companies={companies})')

    if not move_ids:
        return

    # ============================================================
    # Step 2: iterar em chunks de moves
    # ============================================================
    CHUNK_MOVES = 500  # ~2500 lines avg por chunk
    num_lcto = 0
    total_lines = 0

    for i in range(0, total_moves, CHUNK_MOVES):
        chunk_move_ids = move_ids[i:i + CHUNK_MOVES]

        # Buscar TODAS as lines dos moves do chunk de uma vez
        lote = connection.execute_kw(
            'account.move.line', 'search_read',
            [[['move_id', 'in', chunk_move_ids],
              ['parent_state', '=', 'posted']]],
            {
                'fields': fields,
                'order': 'move_id asc, id asc',
            },
            timeout_override=TIMEOUT_QUERY_PESADA,
        )

        # Agrupar por move_id (preserva ordem dos moves)
        from collections import defaultdict
        lines_por_move = defaultdict(list)
        for line in lote:
            mf = line.get('move_id')
            mid = mf[0] if isinstance(mf, (list, tuple)) else mf
            if mid:
                lines_por_move[mid].append(line)

        # Emitir 1 lancamento por move (mantem ordem cronologica de move_ids)
        for mid in chunk_move_ids:
            lines_do_move = lines_por_move.get(mid, [])
            if not lines_do_move:
                continue
            num_lcto += 1
            total_lines += len(lines_do_move)
            yield _construir_lancamento_v11(
                num_lcto, lines_do_move, id_to_code,
                id_to_code_ccus, partner_id_to_cod_part
            )

        if progresso_callback:
            progresso_callback({
                'lines_processadas': total_lines,
                'num_lcto_atual': num_lcto,
                'progresso_chunk': f'{i + len(chunk_move_ids)}/{total_moves} moves',
            })

    logger.info(
        f'[SPED ECD V1.6] Stream completo: {total_lines} lines, '
        f'{num_lcto} lancamentos (esperado ~{total_moves})'
    )


def _construir_lancamento_v11(
    num_lcto: int,
    lines: List[dict],
    id_to_code: Dict[int, str],
    id_to_code_ccus: Dict[int, str],
    partner_id_to_cod_part: Dict[int, str],
) -> dict:
    """
    Versao V1.6: usa account.move.id REAL como NUM_LCTO (rastreavel no Odoo).
    Inclui move_name no inicio do HIST de cada partida (padrao do Odoo CIEL IT).

    Cada line traz `ccus_distribuicao` como lista de tuplas (cod_ccus, percentual).
    construir_I200_I250 ira gerar N partidas I250 conforme split.

    Mudancas V1.6:
    - num agora e o account.move.id real (ex: 440234) em vez de sequencial.
    - Cada line.name e prefixada por move_name (ex: "SIC/2024/04571: ...").
    """
    primeira = lines[0]
    # Extrair move_id real (rastreavel no Odoo)
    move_field = primeira.get('move_id')
    move_id_real = (
        move_field[0] if isinstance(move_field, (list, tuple)) else move_field
    ) or num_lcto  # fallback ao sequencial
    move_name = primeira.get('move_name', '') or ''

    return {
        'num': move_id_real,                    # V1.6: account.move.id real
        '_num_seq': num_lcto,                   # mantem sequencial p/ debug
        'date': primeira.get('date'),
        'move_name': move_name,
        'lines': [
            {
                'code': id_to_code.get(
                    ln['account_id'][0] if isinstance(ln.get('account_id'), (list, tuple)) else ln.get('account_id'),
                    '999'
                ),
                'ccus_distribuicao': _extrair_distribuicao_ccus(
                    ln.get('analytic_distribution'), id_to_code_ccus
                ),
                'cod_part': partner_id_to_cod_part.get(
                    ln['partner_id'][0] if isinstance(ln.get('partner_id'), (list, tuple)) else None,
                    ''
                ) if ln.get('partner_id') else '',
                'debit': float(ln.get('debit') or 0),
                'credit': float(ln.get('credit') or 0),
                # V1.6: HIST com move_name no prefixo (padrao Odoo)
                'name': ln.get('name') or '',
                'ref': ln.get('ref') or '',
                'move_name': move_name,
                'partner_name': (
                    ln['partner_id'][1] if ln.get('partner_id') and isinstance(ln['partner_id'], (list, tuple))
                    else ''
                ),
            }
            for ln in lines
        ],
    }
