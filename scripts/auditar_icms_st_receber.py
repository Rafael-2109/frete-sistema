#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auditoria ICMS-ST — Contas a Receber Odoo
==========================================

Script read-only que identifica faturas no Odoo criadas SEM considerar
o ICMS-ST incluso na NF-e, e rastreia as consequências:

1. Faturas com valor menor que a NF real (falta ST)
2. Write-offs incorretos como "juros" (conta contábil de juros) quando cliente
   paga o valor REAL da NF (com ST) — detectados por account_id, não journal
3. Parcelas-fantasma com vencimento 01/01/2000 (bug de desconto Odoo)

Pipeline de 8 fases:
  1. Buscar move.lines a receber (TODOS — inclui pagos)
  2. Buscar totais fiscais da NF (account.move)
  3. Identificar faturas sem ICMS-ST
  4. Rastrear reconciliações e write-offs (apenas com ST faltante)
  5. Identificar phantoms ano 2000
  6. Cruzar com tabela local contas_a_receber
  7. Gerar Excel
  8. Resumo estatístico

Uso:
    # Auditoria completa (dry-run, sem Excel)
    python scripts/auditar_icms_st_receber.py --dry-run

    # Auditoria com Excel
    python scripts/auditar_icms_st_receber.py

    # Apenas empresa FB
    python scripts/auditar_icms_st_receber.py --empresa 1

    # Teste rápido (100 registros)
    python scripts/auditar_icms_st_receber.py --limite 100 --dry-run -v

Autor: Sistema de Fretes
Data: 2026-02-23
"""

import argparse
import json
import logging
import subprocess
import sys
import os

# Setup path para imports do app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.utils.timezone import agora_utc_naive
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# ===================================================================
# CONSTANTES
# ===================================================================

# Odoo company_ids elegíveis para sincronização
# FONTE: .claude/references/odoo/IDS_FIXOS.md:10-15
ODOO_COMPANY_IDS_ELEGIVEIS = [1, 3, 4]

# Mapeamento company_id → sigla
# FONTE: exportar_titulos_gap_odoo.py:64
COMPANY_SIGLA = {1: 'FB', 3: 'SC', 4: 'CD'}

# CNPJs raiz do grupo Nacom (para detectar intercompany)
# FONTE: .claude/references/odoo/IDS_FIXOS.md:18-25
CNPJS_RAIZ_GRUPO = ['61.724.241', '18.467.441']

# Journal JUROS RECEBIDOS (referência — NÃO usado para detecção)
# NOTA: Write-offs de juros NÃO ficam no journal 1066. Ficam no journal do
#       pagamento (ex: GRAFENO 883). São identificados pela CONTA CONTÁBIL.
# FONTE: app/financeiro/routes/baixas.py:82 + IDS_FIXOS.md:96
JOURNAL_JUROS_ID = 1066

# Contas contábeis de JUROS DE RECEBIMENTOS por company_id
# Write-offs "de juros" são linhas no payment move com account_id nestes IDs
# FONTE: app/financeiro/constants.py — CONTA_JUROS_RECEBIMENTOS_POR_COMPANY
CONTAS_JUROS_RECEBIMENTOS = {22778, 24061, 25345, 26629}
CONTA_JUROS_POR_COMPANY = {1: 22778, 3: 24061, 4: 25345, 5: 26629}

# Data de vencimento "fantasma" gerada pelo bug Odoo
# FONTE: app/financeiro/services/extrato_matching_service.py:49
DATA_PHANTOM = '2000-01-01'

# Tolerância para comparação de valores monetários
TOLERANCIA_VALOR = 0.01

# Batch sizes
SEARCH_BATCH = 1000    # IDs por página no search()
READ_BATCH = 500       # registros por batch no read()
PARTNER_BATCH = 500    # partners por batch
MOVE_BATCH = 200       # invoices por batch
PARTIAL_BATCH = 500    # partial reconcile por batch
LOCAL_BATCH = 500      # IDs por batch na query local

# Campos para read() no account.move.line
# partner_id NÃO incluído — busca separada em res.partner (evita display_name crash)
# FONTE: exportar_titulos_gap_odoo.py:77-88 (padrão do projeto)
CAMPOS_MOVE_LINE = [
    'id', 'name', 'ref',
    'x_studio_nf_e', 'l10n_br_cobranca_parcela',
    'company_id', 'move_id', 'partner_id',
    'date', 'date_maturity',
    'balance', 'amount_residual',
    'desconto_concedido', 'desconto_concedido_percentual',
    'matched_debit_ids', 'matched_credit_ids',
    'l10n_br_paga', 'reconciled',
]

# Campos para res.partner
# FONTE: exportar_titulos_gap_odoo.py:94
CAMPOS_PARTNER = ['id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social']

# Campos fiscais para account.move (NF-e)
# NOTA: Os campos nfe_infnfe_* são do l10n_br_fiscal.document (DFe), NÃO do account.move.
#       No account.move, os campos corretos são l10n_br_*.
# FONTE: fields_get('account.move') executado em 2026-02-23
CAMPOS_INVOICE = [
    'id', 'name',
    'amount_total',                          # Valor da fatura como criada
    'l10n_br_total_nfe',                     # Valor REAL da NF (inclui ST)
    'l10n_br_icmsst_valor',                  # Valor do ICMS-ST
    'l10n_br_icmsst_base',                   # Base do ICMS-ST
    'l10n_br_icms_valor',                    # Valor ICMS normal
    'l10n_br_icms_base',                     # Base ICMS normal
    'l10n_br_fcp_st_valor',                  # FCP-ST (Fundo Combate Pobreza ST)
    'company_id',
]

# Campos para account.partial.reconcile
# FONTE: exportar_titulos_gap_odoo.py:97
CAMPOS_PARTIAL = [
    'id', 'amount', 'max_date',
    'credit_move_id', 'debit_move_id',
]

# Campos para account.move.line (contrapartida e linhas-irmãs do payment move)
# account_id identifica write-offs de juros (CONTAS_JUROS_RECEBIMENTOS)
# credit/debit para saber o valor alocado
CAMPOS_CONTRAPARTIDA = [
    'id', 'journal_id', 'move_id', 'name', 'ref',
    'balance', 'credit', 'debit', 'account_id', 'account_type',
]


def configurar_logging(verbose=False):
    """Configura logging para o script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


# ===================================================================
# HELPERS
# ===================================================================

def extrair_id_numerico(campo):
    """
    Extrai ID numérico de um campo Odoo many2one.

    Odoo retorna [id, 'display_name'] ou int ou False.
    """
    if campo and isinstance(campo, (list, tuple)):
        return campo[0]
    elif campo and isinstance(campo, int):
        return campo
    return None


def safe_float(valor):
    """Converte valor Odoo para float, tratando False/None."""
    if valor is None or valor is False:
        return 0.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _is_intercompany(cnpj):
    """Verifica se o CNPJ pertence ao grupo Nacom (transação intercompany)."""
    if not cnpj:
        return False
    return any(cnpj.startswith(raiz) for raiz in CNPJS_RAIZ_GRUPO)


# ===================================================================
# FASE 1: BUSCAR MOVE.LINES A RECEBER
# ===================================================================

def fase1_buscar_move_lines(connection, empresa_filtro=None, limite=None):
    """
    Fase 1: Buscar TODOS os move.lines a receber (incluindo pagos).

    SEM filtro de balance > 0 — inclui títulos já pagos para
    detectar write-offs incorretos vinculados.

    Args:
        connection: OdooConnection autenticada
        empresa_filtro: Odoo company_id para filtrar (None = todas)
        limite: Limite de registros (para teste)

    Returns:
        tuple: (records, partner_map)
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 1] Buscando move.lines a receber (TODOS)")
    logger.info("=" * 60)

    # Montar domain
    company_ids = [empresa_filtro] if empresa_filtro else ODOO_COMPANY_IDS_ELEGIVEIS
    domain = [
        ['account_type', '=', 'asset_receivable'],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', company_ids],
    ]

    logger.info(f"  Domain: {domain}")

    # search() paginado → todos os IDs
    logger.info("  Buscando IDs (search paginado)...")
    all_ids = []
    offset = 0
    while True:
        ids = connection.execute_kw(
            'account.move.line', 'search', [domain],
            {'limit': SEARCH_BATCH, 'offset': offset},
        )
        if not ids:
            break
        all_ids.extend(ids)
        offset += SEARCH_BATCH
        logger.info(f"    Página {offset // SEARCH_BATCH}: +{len(ids)} (total: {len(all_ids)})")

    logger.info(f"  Total IDs no Odoo: {len(all_ids)}")

    if limite and len(all_ids) > limite:
        all_ids = all_ids[:limite]
        logger.info(f"  Limitado a {limite} IDs (--limite)")

    if not all_ids:
        logger.warning("  Nenhum ID encontrado!")
        return [], {}

    # read() em batches
    logger.info(f"  Lendo {len(all_ids)} registros em batches de {READ_BATCH}...")
    all_records = []
    n_batches = (len(all_ids) + READ_BATCH - 1) // READ_BATCH

    for i in range(0, len(all_ids), READ_BATCH):
        batch_ids = all_ids[i:i + READ_BATCH]
        batch_num = i // READ_BATCH + 1

        try:
            records = connection.read(
                'account.move.line', batch_ids, CAMPOS_MOVE_LINE,
            )
            all_records.extend(records)
            if batch_num % 10 == 0 or batch_num == n_batches:
                logger.info(f"    Batch {batch_num}/{n_batches}: {len(all_records)} lidos")
        except Exception as e:
            logger.error(f"    Erro no batch {batch_num}: {e}")
            continue

    logger.info(f"  Total lidos: {len(all_records)}")

    # Buscar partners separadamente (evita display_name crash)
    # FONTE: exportar_titulos_gap_odoo.py:279-319
    logger.info("  Buscando parceiros...")
    partner_ids = set()
    for r in all_records:
        pid = extrair_id_numerico(r.get('partner_id'))
        if pid:
            partner_ids.add(pid)

    partner_map = {}
    if partner_ids:
        partner_list = list(partner_ids)
        for i in range(0, len(partner_list), PARTNER_BATCH):
            batch = partner_list[i:i + PARTNER_BATCH]
            try:
                partners = connection.read('res.partner', batch, CAMPOS_PARTNER)
                for p in partners:
                    partner_map[p['id']] = p
            except Exception as e:
                logger.warning(f"    Falha ao buscar partners: {e}")

    logger.info(f"  {len(partner_map)} parceiros obtidos")
    return all_records, partner_map


# ===================================================================
# FASE 2: BUSCAR TOTAIS FISCAIS DA NF (account.move)
# ===================================================================

def fase2_buscar_invoices(connection, records):
    """
    Fase 2: Buscar totais fiscais da NF (account.move).

    Extrai move_id únicos da Fase 1 e faz read() em batches.

    Campos-chave:
    - amount_total: valor da fatura como criada
    - nfe_infnfe_total_icmstot_vnf: valor REAL da NF (inclui ST)
    - nfe_infnfe_total_icms_vst: valor do ICMS-ST

    Args:
        connection: OdooConnection autenticada
        records: lista de move.line records da Fase 1

    Returns:
        dict: {move_id: {campos fiscais}} para lookup O(1)
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 2] Buscando totais fiscais da NF (account.move)")
    logger.info("=" * 60)

    # Extrair move_ids únicos
    move_ids = set()
    for r in records:
        mid = extrair_id_numerico(r.get('move_id'))
        if mid:
            move_ids.add(mid)

    logger.info(f"  {len(move_ids)} invoices únicos para buscar")

    if not move_ids:
        return {}

    # read() em batches
    invoice_map = {}
    move_list = list(move_ids)
    n_batches = (len(move_list) + MOVE_BATCH - 1) // MOVE_BATCH

    for i in range(0, len(move_list), MOVE_BATCH):
        batch = move_list[i:i + MOVE_BATCH]
        batch_num = i // MOVE_BATCH + 1

        try:
            invoices = connection.read('account.move', batch, CAMPOS_INVOICE)
            for inv in invoices:
                invoice_map[inv['id']] = inv
            if batch_num % 10 == 0 or batch_num == n_batches:
                logger.info(
                    f"    Batch {batch_num}/{n_batches}: "
                    f"{len(invoice_map)} invoices lidos"
                )
        except Exception as e:
            logger.error(f"    Erro no batch {batch_num}: {e}")
            continue

    logger.info(f"  {len(invoice_map)} invoices obtidos")

    # Estatística rápida: quantos têm ST > 0?
    com_st = sum(
        1 for inv in invoice_map.values()
        if safe_float(inv.get('l10n_br_icmsst_valor')) > TOLERANCIA_VALOR
    )
    logger.info(f"  {com_st} invoices com ICMS-ST > R$ 0.01")

    return invoice_map


# ===================================================================
# FASE 3: IDENTIFICAR FATURAS SEM ICMS-ST
# ===================================================================

def fase3_identificar_st_faltante(records, invoice_map, partner_map):
    """
    Fase 3: Identificar faturas onde o ICMS-ST não foi considerado.

    Para cada move.line, compara nfe_total vs amount_total do invoice pai.
    Se nfe_total - amount_total > R$ 0.01 E icms_st > R$ 0.01 → fatura sem ST.

    Marca TODAS as parcelas do mesmo invoice.

    Args:
        records: lista de move.line records
        invoice_map: {move_id: {campos fiscais}}
        partner_map: {partner_id: {name, cnpj, ...}}

    Returns:
        list[dict]: registros enriquecidos com diagnóstico ST
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 3] Identificando faturas sem ICMS-ST")
    logger.info("=" * 60)

    # Primeiro: identificar quais move_ids têm problema de ST
    # (comparação por invoice, não por parcela)
    moves_com_problema_st = {}  # {move_id: {diferenca, icms_st, nfe_total, ...}}

    for move_id, inv in invoice_map.items():
        amount_total = safe_float(inv.get('amount_total'))
        nfe_total = safe_float(inv.get('l10n_br_total_nfe'))
        icms_st = safe_float(inv.get('l10n_br_icmsst_valor'))

        # Pular invoices sem dados fiscais da NF-e
        if nfe_total < TOLERANCIA_VALOR:
            continue

        diferenca = nfe_total - amount_total

        if diferenca > TOLERANCIA_VALOR and icms_st > TOLERANCIA_VALOR:
            moves_com_problema_st[move_id] = {
                'diferenca_st': round(diferenca, 2),
                'icms_st_nfe': round(icms_st, 2),
                'nfe_total': round(nfe_total, 2),
                'amount_total': round(amount_total, 2),
                'icms_valor': round(safe_float(inv.get('l10n_br_icms_valor')), 2),
                'icms_base': round(safe_float(inv.get('l10n_br_icms_base')), 2),
                'icmsst_base': round(safe_float(inv.get('l10n_br_icmsst_base')), 2),
                'fcp_st': round(safe_float(inv.get('l10n_br_fcp_st_valor')), 2),
                'invoice_name': inv.get('name') or '',
            }

    logger.info(f"  {len(moves_com_problema_st)} invoices com ST faltante detectado")

    # Agora, enriquecer TODOS os records com diagnóstico
    resultados = []
    stats = {
        'total': len(records),
        'com_problema_st': 0,
        'sem_problema_st': 0,
        'sem_dados_fiscais': 0,
        'excluido_sem_nfe': 0,
        'excluido_intercompany': 0,
    }

    for r in records:
        move_id = extrair_id_numerico(r.get('move_id'))
        company_id = extrair_id_numerico(r.get('company_id'))
        partner_id_num = extrair_id_numerico(r.get('partner_id'))

        # Dados do parceiro
        p_info = partner_map.get(partner_id_num, {})
        partner_cnpj = p_info.get('l10n_br_cnpj') or ''
        partner_nome = p_info.get('name') or ''
        partner_razao = p_info.get('l10n_br_razao_social') or ''

        # Filtrar intercompany
        if _is_intercompany(partner_cnpj):
            stats['excluido_intercompany'] += 1
            continue

        # NF-e
        nfe = r.get('x_studio_nf_e')
        if not nfe or nfe is False or str(nfe).strip() in ('', '0'):
            stats['excluido_sem_nfe'] += 1
            continue

        # Dados do invoice
        inv = invoice_map.get(move_id, {})
        inv_name = inv.get('name') or ''

        # Dados da move.line
        balance = safe_float(r.get('balance'))
        amount_residual = safe_float(r.get('amount_residual'))
        desconto_pct = safe_float(r.get('desconto_concedido_percentual'))
        desconto_val = safe_float(r.get('desconto_concedido'))
        vencimento = r.get('date_maturity') or ''

        # Diagnóstico ST
        problema_st = move_id in moves_com_problema_st
        st_info = moves_com_problema_st.get(move_id, {})

        if problema_st:
            stats['com_problema_st'] += 1
        elif safe_float(inv.get('l10n_br_total_nfe')) < TOLERANCIA_VALOR:
            stats['sem_dados_fiscais'] += 1
        else:
            stats['sem_problema_st'] += 1

        resultados.append({
            # Identificação
            'odoo_line_id': r.get('id'),
            'move_id': move_id,
            'invoice_name': inv_name,
            'nfe': str(nfe).strip(),
            'parcela': r.get('l10n_br_cobranca_parcela') or '',
            'empresa': COMPANY_SIGLA.get(company_id, '?'),
            'company_id': company_id,

            # Parceiro
            'partner_cnpj': partner_cnpj,
            'partner_nome': partner_nome,
            'partner_razao': partner_razao,

            # Datas
            'emissao': r.get('date') or '',
            'vencimento': vencimento,

            # Valores do título
            'balance': round(balance, 2),
            'amount_residual': round(amount_residual, 2),
            'desconto_pct': round(desconto_pct, 2),
            'desconto_val': round(desconto_val, 2),

            # Valores do invoice (NF-e)
            'amount_total_fatura': round(safe_float(inv.get('amount_total')), 2),
            'nfe_total': round(safe_float(inv.get('l10n_br_total_nfe')), 2),
            'icms_st_valor': round(safe_float(inv.get('l10n_br_icmsst_valor')), 2),
            'icms_st_bc': round(safe_float(inv.get('l10n_br_icmsst_base')), 2),
            'icms_valor': round(safe_float(inv.get('l10n_br_icms_valor')), 2),
            'icms_base': round(safe_float(inv.get('l10n_br_icms_base')), 2),

            # Diagnóstico ST
            'problema_st': problema_st,
            'diferenca_st': st_info.get('diferenca_st', 0.0),

            # Status pagamento
            'paga': bool(r.get('l10n_br_paga')),
            'reconciliado': bool(r.get('reconciled')),

            # IDs de reconciliação (para Fase 4)
            'matched_debit_ids': r.get('matched_debit_ids') or [],
            'matched_credit_ids': r.get('matched_credit_ids') or [],

            # Campos preenchidos nas fases seguintes
            'writeoff_juros': False,
            'writeoff_juros_valor': 0.0,
            'writeoff_juros_refs': '',
            'phantom_2000': False,
            'existe_local': False,
            'local_parcela_paga': None,
            'local_valor_residual': None,
            'local_metodo_baixa': '',
            'local_inconsistencia': '',

            # Campos do extrato (preenchidos na Fase 4b)
            'valor_pago_titulo': 0.0,
            'extrato_qtd': 0,
            'extrato_valor_total': 0.0,
            'extrato_data': '',
            'extrato_refs': '',
            'extrato_banco': '',
        })

    logger.info(f"  Total registros: {stats['total']}")
    logger.info(f"  Excluído sem NF-e: {stats['excluido_sem_nfe']}")
    logger.info(f"  Excluído intercompany: {stats['excluido_intercompany']}")
    logger.info(f"  Resultado: {len(resultados)} linhas")
    logger.info(f"    Com problema ST: {stats['com_problema_st']}")
    logger.info(f"    Sem problema ST: {stats['sem_problema_st']}")
    logger.info(f"    Sem dados fiscais: {stats['sem_dados_fiscais']}")

    return resultados


# ===================================================================
# FASE 4: RASTREAR RECONCILIAÇÕES E WRITE-OFFS
# ===================================================================

def fase4_rastrear_writeoffs(connection, resultados):
    """
    Fase 4: Rastrear reconciliações e write-offs incorretos de JUROS.

    Escopo: APENAS linhas com problema_st=True.

    LÓGICA CORRIGIDA (2026-02-23):
    Write-offs de juros NÃO ficam em partial.reconcile separado e NÃO usam journal 1066.
    São linhas-irmãs dentro do MESMO payment move, identificadas pela CONTA CONTÁBIL
    (account_id em CONTAS_JUROS_RECEBIMENTOS = {22778, 24061, 25345, 26629}).

    Exemplo real — Invoice 187542 (NF 131664):
      Payment move 479407 tem 3 linhas:
        Line A: account=26868 (PAGAMENTOS PENDENTES)  balance=+8732.71  ← entrada
        Line B: account=24801 (CLIENTES NACIONAIS)     balance=-7847.33  ← baixa do título
        Line C: account=25345 (JUROS RECEBIMENTOS)     balance=-885.38   ← WRITE-OFF

    Fluxo:
    1. Coletar matched_debit_ids + matched_credit_ids das linhas com ST
    2. Buscar account.partial.reconcile em batches
    3. Extrair move.line IDs contrapartida (o lado oposto)
    4. Ler contrapartidas para obter o move_id do pagamento
    5. Buscar TODAS as linhas desses payment moves
    6. Identificar linhas com account_id em CONTAS_JUROS_RECEBIMENTOS

    Args:
        connection: OdooConnection autenticada
        resultados: lista de dicts da Fase 3

    Returns:
        resultados atualizados in-place
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 4] Rastreando reconciliações e write-offs")
    logger.info("=" * 60)

    # Filtrar apenas linhas com problema ST
    linhas_st = [r for r in resultados if r['problema_st']]
    logger.info(f"  {len(linhas_st)} linhas com problema ST para rastrear")

    if not linhas_st:
        logger.info("  Nenhuma linha para rastrear — pulando")
        return resultados

    # ---------------------------------------------------------------
    # PASSO 1: Coletar partial reconcile IDs
    # ---------------------------------------------------------------
    all_partial_ids = set()
    line_to_partials = {}  # {odoo_line_id: [partial_ids]}

    for item in linhas_st:
        line_id = item['odoo_line_id']
        partials = (
            item.get('matched_debit_ids', [])
            + item.get('matched_credit_ids', [])
        )
        if partials:
            all_partial_ids.update(partials)
            line_to_partials[line_id] = partials

    if not all_partial_ids:
        logger.info("  Nenhuma reconciliação encontrada nas linhas com ST")
        return resultados

    logger.info(f"  Passo 1: {len(all_partial_ids)} partial reconcile IDs para buscar")

    # ---------------------------------------------------------------
    # PASSO 2: Batch read em account.partial.reconcile
    # ---------------------------------------------------------------
    partial_map = {}
    partial_list = list(all_partial_ids)

    for i in range(0, len(partial_list), PARTIAL_BATCH):
        batch = partial_list[i:i + PARTIAL_BATCH]
        try:
            partials = connection.read(
                'account.partial.reconcile', batch, CAMPOS_PARTIAL,
            )
            for p in partials:
                partial_map[p['id']] = p
        except Exception as e:
            logger.warning(f"    Falha ao buscar partials batch {i // PARTIAL_BATCH + 1}: {e}")

    logger.info(f"  Passo 2: {len(partial_map)} partials obtidos")

    # ---------------------------------------------------------------
    # PASSO 3: Extrair move.line IDs contrapartida
    # ---------------------------------------------------------------
    contrapartida_ids = set()
    # Mapear: line_id do título → set de contrapartida line IDs
    titulo_to_contrapartidas = {}

    for item in linhas_st:
        line_id = item['odoo_line_id']
        cps = set()
        for pid in line_to_partials.get(line_id, []):
            partial = partial_map.get(pid)
            if not partial:
                continue
            credit_ref = extrair_id_numerico(partial.get('credit_move_id'))
            debit_ref = extrair_id_numerico(partial.get('debit_move_id'))
            for ref_id in [credit_ref, debit_ref]:
                if ref_id and ref_id != line_id:
                    cps.add(ref_id)
                    contrapartida_ids.add(ref_id)
        if cps:
            titulo_to_contrapartidas[line_id] = cps

    logger.info(f"  Passo 3: {len(contrapartida_ids)} move.lines contrapartida")

    if not contrapartida_ids:
        return resultados

    # ---------------------------------------------------------------
    # PASSO 4: Ler contrapartidas para obter move_id (payment move)
    # ---------------------------------------------------------------
    contrapartida_map = {}
    cp_list = list(contrapartida_ids)

    for i in range(0, len(cp_list), READ_BATCH):
        batch = cp_list[i:i + READ_BATCH]
        try:
            lines = connection.read(
                'account.move.line', batch, CAMPOS_CONTRAPARTIDA,
            )
            for line in lines:
                contrapartida_map[line['id']] = line
        except Exception as e:
            logger.warning(f"    Falha ao buscar contrapartidas batch: {e}")

    logger.info(f"  Passo 4: {len(contrapartida_map)} contrapartidas lidas")

    # ---------------------------------------------------------------
    # PASSO 5: Coletar move_ids dos pagamentos e mapear título → move_ids
    # ---------------------------------------------------------------
    # Extrair move_id de cada contrapartida
    payment_move_ids = set()
    # Mapear: line_id do título → set de payment move_ids
    titulo_to_payment_moves = {}

    for titulo_line_id, cp_ids in titulo_to_contrapartidas.items():
        pmoves = set()
        for cp_id in cp_ids:
            cp = contrapartida_map.get(cp_id)
            if not cp:
                continue
            move_id = extrair_id_numerico(cp.get('move_id'))
            if move_id:
                pmoves.add(move_id)
                payment_move_ids.add(move_id)
        if pmoves:
            titulo_to_payment_moves[titulo_line_id] = pmoves

    logger.info(f"  Passo 5: {len(payment_move_ids)} payment moves únicos")

    if not payment_move_ids:
        return resultados

    # ---------------------------------------------------------------
    # PASSO 6: Buscar TODAS as linhas dos payment moves
    # ---------------------------------------------------------------
    # search_read com filtro move_id in (...) e account_id em CONTAS_JUROS
    # Isso busca APENAS as linhas de juros, o que é muito mais eficiente
    # do que buscar todas as linhas de todos os payment moves
    juros_fields = [
        'id', 'move_id', 'account_id', 'name', 'ref',
        'balance', 'credit', 'debit',
    ]

    juros_por_move = {}  # {move_id: [{line_data}, ...]}
    pmove_list = list(payment_move_ids)

    for i in range(0, len(pmove_list), READ_BATCH):
        batch = pmove_list[i:i + READ_BATCH]
        try:
            domain = [
                ('move_id', 'in', batch),
                ('account_id', 'in', list(CONTAS_JUROS_RECEBIMENTOS)),
            ]
            juros_lines = connection.search_read(
                'account.move.line', domain, juros_fields,
            )
            for jl in juros_lines:
                mid = extrair_id_numerico(jl.get('move_id'))
                if mid:
                    juros_por_move.setdefault(mid, []).append(jl)
        except Exception as e:
            logger.warning(f"    Falha ao buscar juros lines batch: {e}")

    total_juros_lines = sum(len(v) for v in juros_por_move.values())
    logger.info(f"  Passo 6: {total_juros_lines} linhas de juros em {len(juros_por_move)} moves")

    # ---------------------------------------------------------------
    # PASSO 7: Enriquecer resultados com write-offs encontrados
    # ---------------------------------------------------------------
    writeoff_count = 0
    writeoff_total = 0.0

    # Lookup rápido: odoo_line_id → índice no resultados
    idx_by_line_id = {}
    for idx, item in enumerate(resultados):
        idx_by_line_id[item['odoo_line_id']] = idx

    for item in linhas_st:
        line_id = item['odoo_line_id']
        item_idx = idx_by_line_id.get(line_id)
        if item_idx is None:
            continue

        juros_refs = []
        juros_total = 0.0

        # Para cada payment move vinculado a este título
        for pmove_id in titulo_to_payment_moves.get(line_id, set()):
            juros_lines = juros_por_move.get(pmove_id, [])
            for jl in juros_lines:
                # Valor do write-off: credit para recebimento (crédito = saída da conta juros)
                # balance é negativo para créditos em contas de receita
                valor = abs(safe_float(jl.get('balance')))
                if valor > TOLERANCIA_VALOR:
                    juros_total += valor
                    jl_ref = jl.get('ref') or jl.get('name') or str(jl.get('id', ''))
                    account_name = ''
                    acc = jl.get('account_id')
                    if acc and isinstance(acc, (list, tuple)) and len(acc) > 1:
                        account_name = f" ({acc[1]})"
                    juros_refs.append(f"move:{pmove_id} {jl_ref}{account_name}")

        if juros_total > TOLERANCIA_VALOR:
            resultados[item_idx]['writeoff_juros'] = True
            resultados[item_idx]['writeoff_juros_valor'] = round(juros_total, 2)
            resultados[item_idx]['writeoff_juros_refs'] = ' | '.join(juros_refs)
            writeoff_count += 1
            writeoff_total += juros_total

    logger.info(f"  Write-offs JUROS detectados: {writeoff_count} linhas")
    logger.info(f"  Valor total write-off JUROS: R$ {writeoff_total:,.2f}")

    return resultados


# ===================================================================
# FASE 4b: EXTRAIR EXTRATOS VINCULADOS
# ===================================================================

# Campos para account.bank.statement.line
CAMPOS_STATEMENT_LINE = [
    'id', 'date', 'amount', 'payment_ref',
    'journal_id', 'is_reconciled', 'move_id',
]

# Contas PENDENTES por company_id (ponte pagamento ↔ extrato)
# FONTE: app/financeiro/constants.py — CONTA_PENDENTES_POR_COMPANY
# + .claude/references/odoo/IDS_FIXOS.md:102-105
CONTAS_PENDENTES = {22199, 26868, 24060, 25344, 26628}


def fase4b_extrair_extratos(connection, resultados):
    """
    Fase 4b: Extrair extratos bancários vinculados aos títulos.

    O vínculo título → extrato no Odoo requer 2 saltos de partial.reconcile:

    1. Título (receivable) → partial → Payment move (linha CLIENTES NACIONAIS)
    2. Payment move (linha PENDENTES) → partial → Statement move (linha PENDENTES)
       → account.bank.statement.line (o extrato)

    Isso revela o que o cliente EFETIVAMENTE pagou no banco,
    permitindo confrontar: valor da fatura (sem ST) vs valor pago (com ST).

    Caso de referência validado:
      NF 131664 → título 1339464 (balance=7847.33)
        → partial 50749 → payment 479407 (line PENDENTES 3010897, balance=+8732.71)
        → partial 57134 → statement move 438323
        → statement line 22948 (amount=8732.71, "Recebimento de boletos - SAITO")

    Escopo: TODOS os títulos com reconciliação (não apenas ST).

    Args:
        connection: OdooConnection autenticada
        resultados: lista de dicts da Fase 3/4

    Returns:
        resultados atualizados in-place
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 4b] Extraindo extratos vinculados aos títulos")
    logger.info("=" * 60)

    # ---------------------------------------------------------------
    # PASSO 1: Coletar partial reconcile IDs de TODOS os títulos
    # ---------------------------------------------------------------
    all_partial_ids = set()
    line_to_partials = {}  # {odoo_line_id: [partial_ids]}

    for item in resultados:
        line_id = item['odoo_line_id']
        partials = (
            item.get('matched_debit_ids', [])
            + item.get('matched_credit_ids', [])
        )
        if partials:
            all_partial_ids.update(partials)
            line_to_partials[line_id] = partials

    titulos_com_reconciliacao = len(line_to_partials)
    logger.info(f"  Passo 1: {titulos_com_reconciliacao} títulos com reconciliações")
    logger.info(f"  {len(all_partial_ids)} partial reconcile IDs (salto 1)")

    if not all_partial_ids:
        logger.info("  Nenhuma reconciliação encontrada — pulando")
        return resultados

    # ---------------------------------------------------------------
    # PASSO 2: Ler partials (salto 1: título → payment)
    # ---------------------------------------------------------------
    partial_map = {}
    partial_list = list(all_partial_ids)

    for i in range(0, len(partial_list), PARTIAL_BATCH):
        batch = partial_list[i:i + PARTIAL_BATCH]
        try:
            partials = connection.read(
                'account.partial.reconcile', batch, CAMPOS_PARTIAL,
            )
            for p in partials:
                partial_map[p['id']] = p
        except Exception as e:
            logger.warning(f"    Falha partials batch {i // PARTIAL_BATCH + 1}: {e}")

    logger.info(f"  Passo 2: {len(partial_map)} partials obtidos")

    # ---------------------------------------------------------------
    # PASSO 3: Extrair contrapartida line IDs (payment move lines)
    # ---------------------------------------------------------------
    contrapartida_ids = set()
    titulo_to_cp_ids = {}  # {titulo_line_id: set(cp_line_ids)}
    titulo_to_partial_amounts = {}  # {titulo_line_id: total pago}

    for item in resultados:
        line_id = item['odoo_line_id']
        cps = set()
        total_pago = 0.0

        for pid in line_to_partials.get(line_id, []):
            partial = partial_map.get(pid)
            if not partial:
                continue

            total_pago += safe_float(partial.get('amount'))
            credit_ref = extrair_id_numerico(partial.get('credit_move_id'))
            debit_ref = extrair_id_numerico(partial.get('debit_move_id'))

            for ref_id in [credit_ref, debit_ref]:
                if ref_id and ref_id != line_id:
                    cps.add(ref_id)
                    contrapartida_ids.add(ref_id)

        if cps:
            titulo_to_cp_ids[line_id] = cps
            titulo_to_partial_amounts[line_id] = total_pago

    logger.info(f"  Passo 3: {len(contrapartida_ids)} contrapartida line IDs")

    if not contrapartida_ids:
        return resultados

    # ---------------------------------------------------------------
    # PASSO 4: Ler contrapartidas para obter move_id do pagamento
    # ---------------------------------------------------------------
    cp_map = {}  # {cp_line_id: {move_id, account_id}}
    cp_list = list(contrapartida_ids)

    for i in range(0, len(cp_list), READ_BATCH):
        batch = cp_list[i:i + READ_BATCH]
        try:
            lines = connection.read(
                'account.move.line', batch,
                ['id', 'move_id', 'account_id'],
            )
            for line in lines:
                cp_map[line['id']] = {
                    'move_id': extrair_id_numerico(line.get('move_id')),
                    'account_id': extrair_id_numerico(line.get('account_id')),
                }
        except Exception as e:
            logger.warning(f"    Falha contrapartidas batch: {e}")

    logger.info(f"  Passo 4: {len(cp_map)} contrapartidas lidas")

    # Coletar payment move IDs únicos
    payment_move_ids = set()
    titulo_to_payment_moves = {}  # {titulo_line_id: set(move_ids)}

    for titulo_id, cp_ids in titulo_to_cp_ids.items():
        moves = set()
        for cp_id in cp_ids:
            cp = cp_map.get(cp_id)
            if cp and cp['move_id']:
                moves.add(cp['move_id'])
                payment_move_ids.add(cp['move_id'])
        if moves:
            titulo_to_payment_moves[titulo_id] = moves

    logger.info(f"  {len(payment_move_ids)} payment moves únicos")

    # ---------------------------------------------------------------
    # PASSO 5: Buscar linhas PENDENTES dos payment moves
    # (para fazer o salto 2: payment → statement)
    # ---------------------------------------------------------------
    pendentes_fields = [
        'id', 'move_id', 'account_id', 'balance',
        'matched_debit_ids', 'matched_credit_ids',
    ]
    pendentes_lines = []  # todas as linhas PENDENTES dos payment moves
    pmove_list = list(payment_move_ids)

    for i in range(0, len(pmove_list), READ_BATCH):
        batch = pmove_list[i:i + READ_BATCH]
        try:
            lines = connection.search_read(
                'account.move.line', [
                    ('move_id', 'in', batch),
                    ('account_id', 'in', list(CONTAS_PENDENTES)),
                ],
                pendentes_fields,
            )
            pendentes_lines.extend(lines)
        except Exception as e:
            logger.warning(f"    Falha pendentes batch: {e}")

    logger.info(f"  Passo 5: {len(pendentes_lines)} linhas PENDENTES nos payment moves")

    # Mapear: payment_move_id → [pendentes_line, ...]
    pendentes_por_move = {}
    for pl in pendentes_lines:
        mid = extrair_id_numerico(pl.get('move_id'))
        if mid:
            pendentes_por_move.setdefault(mid, []).append(pl)

    # Coletar partial IDs do salto 2
    salto2_partial_ids = set()
    for pl in pendentes_lines:
        salto2_partial_ids.update(pl.get('matched_debit_ids') or [])
        salto2_partial_ids.update(pl.get('matched_credit_ids') or [])

    # Remover partials já lidos no salto 1
    salto2_partial_ids -= set(partial_map.keys())

    logger.info(f"  {len(salto2_partial_ids)} partial IDs adicionais (salto 2)")

    if not salto2_partial_ids:
        # Sem salto 2 = sem link para extratos
        logger.info("  Nenhum partial de salto 2 — títulos sem extrato vinculado")
        # Ainda enriquece com valor_pago_titulo
        idx_by_line_id = {item['odoo_line_id']: idx for idx, item in enumerate(resultados)}
        for titulo_id, total in titulo_to_partial_amounts.items():
            idx = idx_by_line_id.get(titulo_id)
            if idx is not None:
                resultados[idx]['valor_pago_titulo'] = round(total, 2)
        return resultados

    # ---------------------------------------------------------------
    # PASSO 6: Ler partials do salto 2
    # ---------------------------------------------------------------
    salto2_list = list(salto2_partial_ids)

    for i in range(0, len(salto2_list), PARTIAL_BATCH):
        batch = salto2_list[i:i + PARTIAL_BATCH]
        try:
            partials = connection.read(
                'account.partial.reconcile', batch, CAMPOS_PARTIAL,
            )
            for p in partials:
                partial_map[p['id']] = p  # add to same map
        except Exception as e:
            logger.warning(f"    Falha partials salto 2 batch: {e}")

    logger.info(f"  Passo 6: {len(partial_map)} partials total (ambos saltos)")

    # ---------------------------------------------------------------
    # PASSO 7: Extrair statement move IDs (contrapartida do salto 2)
    # ---------------------------------------------------------------
    statement_move_ids = set()
    # payment_move_id → set(statement_move_ids)
    payment_to_stmt_moves = {}

    for pl in pendentes_lines:
        pl_id = pl['id']
        pl_move_id = extrair_id_numerico(pl.get('move_id'))
        all_pids = (pl.get('matched_debit_ids') or []) + (pl.get('matched_credit_ids') or [])

        for pid in all_pids:
            p = partial_map.get(pid)
            if not p:
                continue

            credit_ref = extrair_id_numerico(p.get('credit_move_id'))
            debit_ref = extrair_id_numerico(p.get('debit_move_id'))

            for ref_id in [credit_ref, debit_ref]:
                if ref_id and ref_id != pl_id:
                    # Precisamos do move_id dessa line — ler se não temos
                    # Para não explodir em API calls, coletamos IDs e lemos em batch
                    statement_move_ids.add(ref_id)

    logger.info(f"  Passo 7: {len(statement_move_ids)} statement line IDs candidatos")

    # Ler essas lines para obter move_id
    stmt_line_move_map = {}  # {line_id: move_id}
    stmt_list = list(statement_move_ids)

    for i in range(0, len(stmt_list), READ_BATCH):
        batch = stmt_list[i:i + READ_BATCH]
        try:
            lines = connection.read(
                'account.move.line', batch, ['id', 'move_id'],
            )
            for line in lines:
                mid = extrair_id_numerico(line.get('move_id'))
                if mid:
                    stmt_line_move_map[line['id']] = mid
        except Exception as e:
            logger.warning(f"    Falha statement lines batch: {e}")

    # Agora mapear payment_move → statement_move_ids
    all_stmt_move_ids = set()
    for pl in pendentes_lines:
        pl_id = pl['id']
        pl_move_id = extrair_id_numerico(pl.get('move_id'))
        all_pids = (pl.get('matched_debit_ids') or []) + (pl.get('matched_credit_ids') or [])

        for pid in all_pids:
            p = partial_map.get(pid)
            if not p:
                continue
            credit_ref = extrair_id_numerico(p.get('credit_move_id'))
            debit_ref = extrair_id_numerico(p.get('debit_move_id'))
            for ref_id in [credit_ref, debit_ref]:
                if ref_id and ref_id != pl_id:
                    smid = stmt_line_move_map.get(ref_id)
                    if smid:
                        all_stmt_move_ids.add(smid)
                        payment_to_stmt_moves.setdefault(pl_move_id, set()).add(smid)

    logger.info(f"  {len(all_stmt_move_ids)} statement move IDs únicos")

    # ---------------------------------------------------------------
    # PASSO 8: Buscar account.bank.statement.line por move_id
    # ---------------------------------------------------------------
    stmt_por_move = {}  # {move_id: statement_line_data}
    stmt_move_list = list(all_stmt_move_ids)

    for i in range(0, len(stmt_move_list), READ_BATCH):
        batch = stmt_move_list[i:i + READ_BATCH]
        try:
            stmts = connection.search_read(
                'account.bank.statement.line',
                [('move_id', 'in', batch)],
                CAMPOS_STATEMENT_LINE,
            )
            for st in stmts:
                mid = extrair_id_numerico(st.get('move_id'))
                if mid:
                    stmt_por_move[mid] = st
        except Exception as e:
            logger.warning(f"    Falha statement line search batch: {e}")

    logger.info(f"  Passo 8: {len(stmt_por_move)} statement lines encontradas")

    # ---------------------------------------------------------------
    # PASSO 9: Enriquecer resultados
    # ---------------------------------------------------------------
    idx_by_line_id = {item['odoo_line_id']: idx for idx, item in enumerate(resultados)}

    titulos_com_extrato = 0
    titulos_com_pagamento = 0
    valor_total_extratos = 0.0

    for item in resultados:
        line_id = item['odoo_line_id']
        idx = idx_by_line_id.get(line_id)
        if idx is None:
            continue

        # Valor pago (do partial reconcile — salto 1)
        total_pago = titulo_to_partial_amounts.get(line_id, 0.0)
        if total_pago > TOLERANCIA_VALOR:
            resultados[idx]['valor_pago_titulo'] = round(total_pago, 2)
            titulos_com_pagamento += 1

        # Coletar extratos via cadeia: título → payment moves → statement moves
        extrato_data_list = []
        extrato_refs = []
        extrato_journals = []
        extrato_amounts = []

        for pmove_id in titulo_to_payment_moves.get(line_id, set()):
            for smove_id in payment_to_stmt_moves.get(pmove_id, set()):
                stmt = stmt_por_move.get(smove_id)
                if stmt:
                    extrato_amounts.append(safe_float(stmt.get('amount')))
                    extrato_data_list.append(str(stmt.get('date', '')))
                    ref = stmt.get('payment_ref') or ''
                    if ref:
                        # Truncar refs longas
                        extrato_refs.append(ref[:80])
                    jnl = stmt.get('journal_id')
                    if jnl and isinstance(jnl, (list, tuple)) and len(jnl) > 1:
                        extrato_journals.append(jnl[1])

        if extrato_amounts:
            resultados[idx]['extrato_qtd'] = len(extrato_amounts)
            resultados[idx]['extrato_valor_total'] = round(sum(extrato_amounts), 2)
            resultados[idx]['extrato_data'] = ' | '.join(sorted(set(extrato_data_list)))
            resultados[idx]['extrato_refs'] = ' | '.join(extrato_refs[:3])
            resultados[idx]['extrato_banco'] = ' | '.join(sorted(set(extrato_journals)))
            titulos_com_extrato += 1
            valor_total_extratos += sum(extrato_amounts)

    logger.info(f"  {titulos_com_pagamento} títulos com pagamento (partial reconcile)")
    logger.info(f"  {titulos_com_extrato} títulos vinculados a extratos bancários")
    logger.info(f"  Valor total nos extratos: R$ {valor_total_extratos:,.2f}")

    return resultados


# ===================================================================
# FASE 5: IDENTIFICAR PHANTOMS ANO 2000
# ===================================================================

def fase5_identificar_phantoms(resultados):
    """
    Fase 5: Identificar parcelas-fantasma com vencimento 01/01/2000.

    Bug do Odoo que gera parcelas duplicadas de desconto.
    FONTE: app/financeiro/services/extrato_matching_service.py:49

    Args:
        resultados: lista de dicts da Fase 3/4

    Returns:
        resultados atualizados in-place
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 5] Identificando phantoms ano 2000")
    logger.info("=" * 60)

    phantom_count = 0
    phantom_by_nf = {}

    for item in resultados:
        vencimento = str(item.get('vencimento', ''))
        if vencimento == DATA_PHANTOM:
            item['phantom_2000'] = True
            phantom_count += 1

            nfe = item['nfe']
            if nfe not in phantom_by_nf:
                phantom_by_nf[nfe] = []
            phantom_by_nf[nfe].append(item['odoo_line_id'])

    logger.info(f"  Phantoms 2000-01-01: {phantom_count} parcelas")
    logger.info(f"  Em {len(phantom_by_nf)} NFs distintas")

    if phantom_by_nf and logger.isEnabledFor(logging.DEBUG):
        for nfe, ids in list(phantom_by_nf.items())[:5]:
            logger.debug(f"    NF {nfe}: {len(ids)} phantom(s)")

    return resultados


# ===================================================================
# FASE 6: CRUZAR COM TABELA LOCAL
# ===================================================================

def fase6_cruzar_local(resultados):
    """
    Fase 6: Cruzar com tabela local contas_a_receber.

    Query por odoo_line_id IN (...) em batches.
    Enriquecer com: parcela_paga, valor_residual, metodo_baixa, inconsistencia_odoo.

    FONTE: schema contas_a_receber.json — campos verificados

    Args:
        resultados: lista de dicts

    Returns:
        resultados atualizados in-place
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 6] Cruzando com tabela local contas_a_receber")
    logger.info("=" * 60)

    from sqlalchemy import text

    # Coletar todos odoo_line_ids
    all_line_ids = [r['odoo_line_id'] for r in resultados if r.get('odoo_line_id')]

    if not all_line_ids:
        logger.info("  Nenhum line_id para cruzar")
        return resultados

    logger.info(f"  {len(all_line_ids)} IDs para buscar localmente")

    # Prevenir SSL drop antes de queries locais
    # FONTE: reconciliar_titulos_odoo.py:587
    db.session.close()

    # Query em batches
    local_map = {}

    for i in range(0, len(all_line_ids), LOCAL_BATCH):
        batch = all_line_ids[i:i + LOCAL_BATCH]
        placeholders = ','.join(str(x) for x in batch)

        try:
            rows = db.session.execute(text(
                f"SELECT odoo_line_id, parcela_paga, valor_residual, "
                f"metodo_baixa, inconsistencia_odoo "
                f"FROM contas_a_receber "
                f"WHERE odoo_line_id IN ({placeholders})"
            )).fetchall()

            for row in rows:
                local_map[row[0]] = {
                    'parcela_paga': row[1],
                    'valor_residual': row[2],
                    'metodo_baixa': row[3] or '',
                    'inconsistencia_odoo': row[4] or '',
                }
        except Exception as e:
            logger.error(f"    Erro na query local batch {i // LOCAL_BATCH + 1}: {e}")
            db.session.close()
            continue

    logger.info(f"  {len(local_map)} registros encontrados localmente")

    # Enriquecer resultados
    encontrados = 0
    for item in resultados:
        line_id = item['odoo_line_id']
        local = local_map.get(line_id)
        if local:
            item['existe_local'] = True
            item['local_parcela_paga'] = local['parcela_paga']
            item['local_valor_residual'] = local['valor_residual']
            item['local_metodo_baixa'] = local['metodo_baixa']
            item['local_inconsistencia'] = local['inconsistencia_odoo']
            encontrados += 1

    logger.info(f"  {encontrados} linhas enriquecidas com dados locais")
    logger.info(f"  {len(resultados) - encontrados} sem correspondência local")

    return resultados


# ===================================================================
# FASE 7: GERAR EXCEL
# ===================================================================

def classificar_acao(item):
    """
    Classifica a ação recomendada para cada linha.

    Returns:
        tuple: (acao, problema_descricao)
    """
    problemas = []
    acoes = []

    if item['phantom_2000']:
        problemas.append('Phantom 2000-01-01')
        acoes.append('CORRIGIR_ANO2000')

    if item['problema_st']:
        problemas.append(f"ST faltante (diff R$ {item['diferenca_st']:,.2f})")
        acoes.append('CORRIGIR_FATURA')

        if item['writeoff_juros']:
            problemas.append(
                f"Write-off JUROS incorreto R$ {item['writeoff_juros_valor']:,.2f}"
            )
            acoes.append('AJUSTAR_WRITEOFF')

    if not problemas:
        return 'OK', ''

    # Prioridade: CORRIGIR_FATURA > AJUSTAR_WRITEOFF > CORRIGIR_ANO2000
    if 'CORRIGIR_FATURA' in acoes:
        acao_principal = 'CORRIGIR_FATURA'
    elif 'AJUSTAR_WRITEOFF' in acoes:
        acao_principal = 'AJUSTAR_WRITEOFF'
    else:
        acao_principal = 'CORRIGIR_ANO2000'

    return acao_principal, ' + '.join(problemas)


def fase7_gerar_excel(resultados, dry_run=False):
    """
    Fase 7: Gerar Excel via pipe para exportar.py.

    Args:
        resultados: lista de dicts enriquecidos
        dry_run: Se True, não gera Excel

    Returns:
        dict: resultado do exportar.py (ou None se dry_run)
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 7] Gerando Excel")
    logger.info("=" * 60)

    if dry_run:
        logger.info("  DRY-RUN: Excel não será gerado")
        return None

    # Formatar dados para Excel
    dados = []
    for item in resultados:
        acao, problema_desc = classificar_acao(item)

        # Pular linhas OK (sem problema)
        # Se quiser incluir tudo, remover este filtro
        # Mantemos TODAS as linhas para auditoria completa

        dados.append({
            'NF': item['nfe'],
            'Parcela': item['parcela'],
            'Empresa': item['empresa'],
            'CNPJ': item['partner_cnpj'],
            'Razao Social': item['partner_razao'] or item['partner_nome'],
            'Vencimento': item['vencimento'],
            'Fatura (amount_total)': item['amount_total_fatura'],
            'NF Real (l10n_br_total_nfe)': item['nfe_total'],
            'ICMS-ST Valor': item['icms_st_valor'],
            'ICMS-ST BC': item['icms_st_bc'],
            'ICMS Valor': item.get('icms_valor', 0),
            'Diferenca ST': item['diferenca_st'],
            'Desconto %': item['desconto_pct'],
            'Desconto Valor': item['desconto_val'],
            'Balance': item['balance'],
            'Residual': item['amount_residual'],
            'Paga Odoo': item['paga'],
            'Reconciliado': item['reconciliado'],
            'Valor Pago (partial)': item['valor_pago_titulo'],
            'Extrato Qtd': item['extrato_qtd'],
            'Extrato Valor Total': item['extrato_valor_total'],
            'Extrato Data': item['extrato_data'],
            'Extrato Ref': item['extrato_refs'],
            'Extrato Banco': item['extrato_banco'],
            'Write-off JUROS': item['writeoff_juros'],
            'Valor Write-off': item['writeoff_juros_valor'],
            'Refs Write-off': item['writeoff_juros_refs'],
            'Phantom 2000': item['phantom_2000'],
            'Existe Local': item['existe_local'],
            'Paga Local': item['local_parcela_paga'],
            'Metodo Baixa': item['local_metodo_baixa'],
            'Inconsistencia': item['local_inconsistencia'],
            'Problema': problema_desc,
            'Acao Recomendada': acao,
            'Odoo Line ID': item['odoo_line_id'],
            'Move ID': item['move_id'],
            'Invoice': item['invoice_name'],
        })

    logger.info(f"  {len(dados)} linhas para exportar")

    # Pipe para exportar.py
    # FONTE: exportar_titulos_gap_odoo.py:630-683
    json_input = json.dumps({'dados': dados}, ensure_ascii=False, default=str)

    base_dir = os.path.join(os.path.dirname(__file__), '..')
    exportar_script = os.path.join(
        base_dir,
        '.claude', 'skills', 'exportando-arquivos', 'scripts', 'exportar.py',
    )

    cmd = [
        sys.executable, exportar_script,
        '--formato', 'excel',
        '--nome', 'auditoria_icms_st_receber',
        '--titulo', 'Auditoria ICMS-ST - Contas a Receber Odoo',
    ]

    try:
        result = subprocess.run(
            cmd,
            input=json_input,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"  exportar.py falhou: {result.stderr}")
            return None

        output = json.loads(result.stdout)
        logger.info(f"  Excel gerado: {output.get('arquivo', {}).get('url_completa', '?')}")
        return output

    except subprocess.TimeoutExpired:
        logger.error("  Timeout ao gerar Excel (>120s)")
        return None
    except json.JSONDecodeError:
        logger.error(f"  Retorno inválido do exportar.py: {result.stdout[:200]}")
        return None
    except Exception as e:
        logger.error(f"  Erro ao chamar exportar.py: {e}")
        return None


# ===================================================================
# FASE 8: RESUMO ESTATÍSTICO
# ===================================================================

def fase8_resumo(resultados):
    """
    Fase 8: Resumo estatístico em box formatado.

    FONTE: reconciliar_titulos_odoo.py:633-655 (padrão do projeto)

    Args:
        resultados: lista de dicts enriquecidos

    Returns:
        dict: estatísticas para JSON
    """
    logger.info("\n" + "=" * 60)
    logger.info("[FASE 8] Resumo Estatístico")
    logger.info("=" * 60)

    # Contadores gerais
    total = len(resultados)
    com_problema_st = sum(1 for r in resultados if r['problema_st'])
    com_writeoff_juros = sum(1 for r in resultados if r['writeoff_juros'])
    phantoms = sum(1 for r in resultados if r['phantom_2000'])
    com_qualquer_problema = sum(
        1 for r in resultados
        if r['problema_st'] or r['phantom_2000']
    )

    # Valores
    valor_st_faltante = sum(r['diferenca_st'] for r in resultados if r['problema_st'])
    valor_writeoff_juros = sum(r['writeoff_juros_valor'] for r in resultados if r['writeoff_juros'])

    # NFs únicas afetadas
    nfs_com_st = set(r['nfe'] for r in resultados if r['problema_st'])
    nfs_com_writeoff = set(r['nfe'] for r in resultados if r['writeoff_juros'])
    nfs_com_phantom = set(r['nfe'] for r in resultados if r['phantom_2000'])

    # Invoices únicos (move_id)
    moves_com_st = set(r['move_id'] for r in resultados if r['problema_st'])

    # Por empresa
    por_empresa = {}
    for r in resultados:
        emp = r['empresa']
        if emp not in por_empresa:
            por_empresa[emp] = {
                'total': 0, 'problema_st': 0, 'writeoff': 0,
                'phantom': 0, 'valor_st': 0.0, 'valor_wo': 0.0,
            }
        por_empresa[emp]['total'] += 1
        if r['problema_st']:
            por_empresa[emp]['problema_st'] += 1
            por_empresa[emp]['valor_st'] += r['diferenca_st']
        if r['writeoff_juros']:
            por_empresa[emp]['writeoff'] += 1
            por_empresa[emp]['valor_wo'] += r['writeoff_juros_valor']
        if r['phantom_2000']:
            por_empresa[emp]['phantom'] += 1

    # Extratos
    com_extrato = sum(1 for r in resultados if r['extrato_qtd'] > 0)
    com_pagamento = sum(1 for r in resultados if r['valor_pago_titulo'] > TOLERANCIA_VALOR)
    valor_total_extratos = sum(r['extrato_valor_total'] for r in resultados if r['extrato_qtd'] > 0)

    # Classificação de ações
    acoes = {}
    for r in resultados:
        acao, _ = classificar_acao(r)
        acoes[acao] = acoes.get(acao, 0) + 1

    # Box formatado
    logger.info("")
    logger.info("+" + "=" * 62 + "+")
    logger.info("|  AUDITORIA ICMS-ST — CONTAS A RECEBER ODOO" + " " * 19 + "|")
    logger.info("+" + "=" * 62 + "+")
    logger.info(f"|  Total de linhas analisadas:          {total:>10,}             |")
    logger.info(f"|  Linhas com problema:                 {com_qualquer_problema:>10,}             |")
    logger.info("+" + "-" * 62 + "+")
    logger.info("|  ICMS-ST FALTANTE:" + " " * 43 + "|")
    logger.info(f"|    Parcelas afetadas:                 {com_problema_st:>10,}             |")
    logger.info(f"|    Faturas (invoices) únicas:         {len(moves_com_st):>10,}             |")
    logger.info(f"|    NFs únicas:                        {len(nfs_com_st):>10,}             |")
    logger.info(f"|    Valor ST faltante total:      R$ {valor_st_faltante:>12,.2f}           |")
    logger.info("+" + "-" * 62 + "+")
    logger.info("|  WRITE-OFFS INCORRETOS (journal JUROS 1066):" + " " * 17 + "|")
    logger.info(f"|    Parcelas com write-off JUROS:      {com_writeoff_juros:>10,}             |")
    logger.info(f"|    NFs únicas:                        {len(nfs_com_writeoff):>10,}             |")
    logger.info(f"|    Valor total write-off:        R$ {valor_writeoff_juros:>12,.2f}           |")
    logger.info("+" + "-" * 62 + "+")
    logger.info("|  EXTRATOS BANCÁRIOS VINCULADOS:" + " " * 30 + "|")
    logger.info(f"|    Títulos com pagamento (partial):     {com_pagamento:>10,}             |")
    logger.info(f"|    Títulos com extrato bancário:        {com_extrato:>10,}             |")
    logger.info(f"|    Valor total nos extratos:       R$ {valor_total_extratos:>12,.2f}           |")
    logger.info("+" + "-" * 62 + "+")
    logger.info("|  PHANTOMS ANO 2000:" + " " * 42 + "|")
    logger.info(f"|    Parcelas phantom:                  {phantoms:>10,}             |")
    logger.info(f"|    NFs únicas:                        {len(nfs_com_phantom):>10,}             |")
    logger.info("+" + "-" * 62 + "+")
    logger.info("|  POR EMPRESA:" + " " * 48 + "|")
    for emp in sorted(por_empresa.keys()):
        e = por_empresa[emp]
        logger.info(
            f"|    {emp}: {e['total']:,} linhas | "
            f"ST: {e['problema_st']:,} (R$ {e['valor_st']:,.2f}) | "
            f"WO: {e['writeoff']:,} | "
            f"Ph: {e['phantom']:,}"
            + " " * max(0, 62 - len(
                f"    {emp}: {e['total']:,} linhas | "
                f"ST: {e['problema_st']:,} (R$ {e['valor_st']:,.2f}) | "
                f"WO: {e['writeoff']:,} | "
                f"Ph: {e['phantom']:,}"
            )) + "|"
        )
    logger.info("+" + "-" * 62 + "+")
    logger.info("|  ACAO RECOMENDADA:" + " " * 43 + "|")
    for acao, count in sorted(acoes.items()):
        logger.info(f"|    {acao:30s} {count:>10,}             |")
    logger.info("+" + "=" * 62 + "+")

    return {
        'total_linhas': total,
        'com_problema_st': com_problema_st,
        'faturas_com_st': len(moves_com_st),
        'nfs_com_st': len(nfs_com_st),
        'valor_st_faltante': round(valor_st_faltante, 2),
        'writeoffs_juros': com_writeoff_juros,
        'valor_writeoff_juros': round(valor_writeoff_juros, 2),
        'titulos_com_pagamento': com_pagamento,
        'titulos_com_extrato': com_extrato,
        'valor_total_extratos': round(valor_total_extratos, 2),
        'phantoms_2000': phantoms,
        'por_empresa': por_empresa,
        'acoes': acoes,
    }


# ===================================================================
# ORQUESTRADOR PRINCIPAL
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Auditoria ICMS-ST — Contas a Receber Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Auditoria completa (dry-run, sem Excel)
  python scripts/auditar_icms_st_receber.py --dry-run

  # Auditoria com Excel
  python scripts/auditar_icms_st_receber.py

  # Apenas empresa FB
  python scripts/auditar_icms_st_receber.py --empresa 1

  # Teste rápido (100 registros)
  python scripts/auditar_icms_st_receber.py --limite 100 --dry-run -v
        """,
    )
    parser.add_argument(
        '--empresa', type=int, choices=[1, 3, 4],
        help='Odoo company_id: 1=FB, 3=SC, 4=CD (default: todas)',
    )
    parser.add_argument(
        '--limite', type=int, default=None,
        help='Limite de registros da Fase 1 (para teste)',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Apenas diagnóstico, sem gerar Excel',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Logging detalhado (DEBUG)',
    )

    args = parser.parse_args()
    configurar_logging(args.verbose)

    inicio = agora_utc_naive()

    logger.info("=" * 60)
    logger.info("AUDITORIA ICMS-ST — CONTAS A RECEBER ODOO")
    logger.info(f"Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Empresa: {COMPANY_SIGLA.get(args.empresa, 'Todas')}")
    if args.limite:
        logger.info(f"Limite: {args.limite} registros")
    logger.info(f"Dry-run: {'Sim' if args.dry_run else 'Nao'}")
    logger.info("=" * 60)

    # Criar app Flask
    app = create_app()

    with app.app_context():
        # Conectar ao Odoo
        logger.info("\nConectando ao Odoo...")
        connection = get_odoo_connection()
        if not connection.authenticate():
            logger.error("Falha na autenticacao com Odoo")
            sys.exit(1)
        logger.info("Conectado ao Odoo")

        # FASE 1: Buscar move.lines a receber
        records, partner_map = fase1_buscar_move_lines(
            connection, args.empresa, args.limite,
        )

        if not records:
            logger.info("\nNenhum registro encontrado!")
            sys.exit(0)

        # FASE 2: Buscar totais fiscais da NF
        # Fix SSL: reconectar DB após queries Odoo longas (Fase 1 pode levar minutos)
        # FONTE: reconciliar_titulos_odoo.py:587
        db.session.close()
        invoice_map = fase2_buscar_invoices(connection, records)

        # FASE 3: Identificar faturas sem ICMS-ST
        resultados = fase3_identificar_st_faltante(records, invoice_map, partner_map)

        if not resultados:
            logger.info("\nNenhum resultado após filtragem!")
            sys.exit(0)

        # FASE 4: Rastrear reconciliações e write-offs
        db.session.close()
        resultados = fase4_rastrear_writeoffs(connection, resultados)

        # FASE 4b: Extrair extratos vinculados
        db.session.close()
        resultados = fase4b_extrair_extratos(connection, resultados)

        # FASE 5: Identificar phantoms ano 2000
        resultados = fase5_identificar_phantoms(resultados)

        # FASE 6: Cruzar com tabela local
        resultados = fase6_cruzar_local(resultados)

        # FASE 7: Gerar Excel
        resultado_excel = fase7_gerar_excel(resultados, dry_run=args.dry_run)

        if resultado_excel and resultado_excel.get('sucesso'):
            arquivo = resultado_excel.get('arquivo', {})
            print(f"\nExcel gerado: {arquivo.get('url_completa', '?')}")

        # FASE 8: Resumo estatístico
        stats = fase8_resumo(resultados)

        # Salvar JSON de resumo em /tmp para referência
        resumo_path = '/tmp/auditoria_icms_st_resumo.json'
        with open(resumo_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"\nResumo JSON salvo em: {resumo_path}")

        # Tempo total
        fim = agora_utc_naive()
        duracao = (fim - inicio).total_seconds()
        logger.info(
            f"\nConcluido em {duracao:.0f}s "
            f"({fim.strftime('%Y-%m-%d %H:%M:%S')})"
        )


if __name__ == '__main__':
    main()
