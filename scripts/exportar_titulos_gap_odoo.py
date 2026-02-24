#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exportar Titulos Odoo Nao Importados — Gap Analysis
=====================================================

Gera Excel com todos os titulos do Odoo (posted, company 1/3/4) que NAO
existem no banco local, enriquecidos com dados de pagamento e extrato.

Estrategia resiliente:
1. search() no Odoo → so IDs (evita display_name crash)
2. db.session.close() → fresh SSL connection
3. Query local → set difference
4. read() em batches de 500 → dados completos
5. Partner info via read() separado em res.partner
6. Filtrar (sem NF-e, intercompany, empresa invalida)
7. Categorizar motivo de nao importacao
8. Enriquecer com dados de pagamento/extrato (partial reconcile)
9. Exportar via pipe para exportar.py → Excel

Bugs evitados:
- SSL drop: db.session.close() antes de cada query local
- display_name crash: read() com campos explicitos, sem partner_id
- Timeout: batches de 500, timeout_override para search() grande

Uso:
    python scripts/exportar_titulos_gap_odoo.py
    python scripts/exportar_titulos_gap_odoo.py --tipo pagar
    python scripts/exportar_titulos_gap_odoo.py --tipo receber
    python scripts/exportar_titulos_gap_odoo.py --limite 100

Autor: Sistema de Fretes
Data: 2026-02-23
"""

import argparse
import json
import logging
import subprocess
import sys
import os
from datetime import datetime

# Setup path para imports do app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.utils.timezone import agora_utc_naive
from app.odoo.utils.connection import get_odoo_connection
from app.financeiro.models import ContasAReceber, ContasAPagar

logger = logging.getLogger(__name__)

# ===================================================================
# CONSTANTES
# ===================================================================

# Odoo company_ids elegiveis para sincronizacao
# FONTE: .claude/references/odoo/IDS_FIXOS.md:10-15
ODOO_COMPANY_IDS_ELEGIVEIS = [1, 3, 4]

# Mapeamento company_id → sigla
# FONTE: amostra_titulos_odoo_faltantes.py:56
COMPANY_SIGLA = {1: 'FB', 3: 'SC', 4: 'CD'}

# CNPJs raiz do grupo Nacom (para detectar intercompany)
# FONTE: sincronizacao_contas_pagar_service.py:35
CNPJS_RAIZ_GRUPO = ['61.724.241', '18.467.441']

# Batch sizes
SEARCH_BATCH = 500     # IDs por pagina no search()
READ_BATCH = 500       # registros por batch no read()
PARTNER_BATCH = 500    # partners por batch

# Campos para read() no account.move.line
# partner_id NAO incluido — busca separada em res.partner (evita display_name crash)
CAMPOS_TITULO = [
    'id', 'name', 'ref',
    'x_studio_nf_e', 'l10n_br_cobranca_parcela',
    'company_id', 'move_id',
    'date', 'date_maturity',
    'credit', 'balance', 'amount_residual',
    'l10n_br_paga', 'reconciled',
    'matched_debit_ids', 'matched_credit_ids',
    'full_reconcile_id',
    'account_type', 'parent_state',
    'write_date', 'create_date',
]

# Campos com partner_id (tentativa com fallback)
CAMPOS_TITULO_COM_PARTNER = CAMPOS_TITULO + ['partner_id']

# Campos para res.partner
CAMPOS_PARTNER = ['id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social']

# Campos para account.partial.reconcile
CAMPOS_PARTIAL = ['id', 'amount', 'max_date', 'credit_move_id', 'debit_move_id']


def configurar_logging(verbose=False):
    """Configura logging para o script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


# ===================================================================
# PHASE 1-3: COLETAR GAP IDS
# ===================================================================

def coletar_ids_locais(tipo, production_ids_dir=None):
    """
    Phase 1: Coletar todos os odoo_line_ids locais.

    Se production_ids_dir for fornecido, le IDs de arquivo JSON pre-exportado
    do Render (producao) em vez de consultar o DB local.

    Args:
        tipo: 'pagar' ou 'receber'
        production_ids_dir: diretorio com render_pagar_ids.json / render_receber_ids.json

    Returns:
        set[int]: Conjunto de odoo_line_ids existentes no banco (producao ou local)
    """
    tipo_label = tipo.upper()
    logger.info(f"[Phase 1] Coletando odoo_line_ids locais ({tipo_label})...")

    if production_ids_dir:
        # Ler IDs pre-exportados do Render (producao)
        ids_file = os.path.join(production_ids_dir, f'render_{tipo}_ids.json')
        logger.info(f"  Lendo IDs de producao de: {ids_file}")
        with open(ids_file, 'r') as f:
            ids_list = json.load(f)
        ids_locais = set(ids_list)
        logger.info(f"  {len(ids_locais)} IDs de PRODUCAO ({tipo_label})")
    else:
        # Query no DB local/conectado
        from sqlalchemy import text
        tabela = 'contas_a_pagar' if tipo == 'pagar' else 'contas_a_receber'
        rows = db.session.execute(
            text(f"SELECT odoo_line_id FROM {tabela} WHERE odoo_line_id IS NOT NULL")
        ).fetchall()
        ids_locais = {r[0] for r in rows}
        logger.info(f"  {len(ids_locais)} IDs locais ({tipo_label})")
        # Prevenir SSL drop antes de queries Odoo longas
        db.session.close()

    return ids_locais


def coletar_ids_odoo(connection, tipo):
    """
    Phase 2: search() no Odoo → todos IDs posted.
    Usa search() (nao search_read) para evitar display_name crash.

    Args:
        connection: OdooConnection autenticada
        tipo: 'pagar' ou 'receber'

    Returns:
        list[int]: Lista de IDs do Odoo
    """
    account_type = 'liability_payable' if tipo == 'pagar' else 'asset_receivable'
    tipo_label = tipo.upper()

    domain = [
        ['account_type', '=', account_type],
        ['parent_state', '=', 'posted'],
        ['company_id', 'in', ODOO_COMPANY_IDS_ELEGIVEIS],
    ]

    # Receber tambem filtra date_maturity != False (alinhado com sync)
    if tipo == 'receber':
        domain.append(['date_maturity', '!=', False])

    logger.info(f"[Phase 2] search() no Odoo ({tipo_label})...")
    logger.info(f"  Domain: {domain}")

    # search() retorna todos IDs como lista (sem paginacao necessaria)
    # Usar timeout_override para queries grandes
    all_ids = connection.execute_kw(
        'account.move.line', 'search', [domain],
        timeout_override=180,
    )

    logger.info(f"  {len(all_ids)} IDs no Odoo ({tipo_label})")
    return all_ids


def calcular_gap(ids_locais, ids_odoo):
    """
    Phase 3: Set difference → gap_ids.

    Args:
        ids_locais: set de IDs locais
        ids_odoo: list de IDs do Odoo

    Returns:
        list[int]: IDs que estao no Odoo mas nao localmente
    """
    gap = [id_ for id_ in ids_odoo if id_ not in ids_locais]
    logger.info(f"[Phase 3] Gap: {len(gap)} titulos no Odoo que nao existem localmente")
    return gap


# ===================================================================
# PHASE 4-5: BUSCAR DADOS COMPLETOS
# ===================================================================

def buscar_dados_titulos(connection, gap_ids, limite=None):
    """
    Phase 4: read() em batches nos gap_ids.
    Tenta com partner_id primeiro, fallback sem ele.

    Args:
        connection: OdooConnection autenticada
        gap_ids: lista de IDs faltantes
        limite: limite de IDs a processar (para teste)

    Returns:
        tuple: (records, usou_partner_id)
    """
    ids_to_read = gap_ids[:limite] if limite else gap_ids
    total = len(ids_to_read)
    n_batches = (total + READ_BATCH - 1) // READ_BATCH

    logger.info(f"[Phase 4] read() de {total} titulos em {n_batches} batches...")

    # Tentar com partner_id primeiro
    usou_partner = True
    campos = CAMPOS_TITULO_COM_PARTNER

    all_records = []
    for i in range(0, total, READ_BATCH):
        batch_ids = ids_to_read[i:i + READ_BATCH]
        batch_num = i // READ_BATCH + 1

        try:
            records = connection.read(
                'account.move.line', batch_ids, campos,
            )
            all_records.extend(records)
            logger.info(f"  Batch {batch_num}/{n_batches}: {len(records)} registros")

        except Exception as e:
            if usou_partner and batch_num == 1:
                # Primeira falha — tentar sem partner_id
                logger.warning(f"  read() com partner_id falhou: {e}")
                logger.info("  Tentando sem partner_id...")
                usou_partner = False
                campos = CAMPOS_TITULO

                try:
                    records = connection.read(
                        'account.move.line', batch_ids, campos,
                    )
                    all_records.extend(records)
                    logger.info(
                        f"  Batch {batch_num}/{n_batches}: {len(records)} registros (sem partner)"
                    )
                except Exception as e2:
                    logger.error(f"  Falha total no batch {batch_num}: {e2}")
                    continue
            else:
                logger.error(f"  Erro no batch {batch_num}: {e}")
                continue

        # A cada 10 batches, log de progresso
        if batch_num % 10 == 0:
            logger.info(f"  Progresso: {len(all_records)}/{total}")

    logger.info(f"  Total lidos: {len(all_records)} de {total}")
    return all_records, usou_partner


def buscar_partners(connection, records):
    """
    Phase 5: Coletar partner_ids unicos → batch read() res.partner.

    Args:
        connection: OdooConnection autenticada
        records: lista de dicts do Odoo

    Returns:
        dict: {partner_id: {name, l10n_br_cnpj, l10n_br_razao_social}}
    """
    logger.info(f"[Phase 5] Buscando dados de parceiros...")

    partner_ids = set()
    for r in records:
        pid = r.get('partner_id')
        if pid and isinstance(pid, (list, tuple)):
            partner_ids.add(pid[0])
        elif pid and isinstance(pid, int):
            partner_ids.add(pid)

    if not partner_ids:
        logger.info("  Nenhum partner_id encontrado nos registros")
        return {}

    logger.info(f"  {len(partner_ids)} partners unicos para buscar")

    partner_map = {}
    partner_list = list(partner_ids)

    for i in range(0, len(partner_list), PARTNER_BATCH):
        batch = partner_list[i:i + PARTNER_BATCH]
        try:
            partners = connection.read('res.partner', batch, CAMPOS_PARTNER)
            for p in partners:
                partner_map[p['id']] = p
        except Exception as e:
            logger.warning(f"  Falha ao buscar partners batch {i // PARTNER_BATCH + 1}: {e}")

    logger.info(f"  {len(partner_map)} parceiros obtidos")
    return partner_map


# ===================================================================
# PHASE 6-7: FILTRAR E CATEGORIZAR
# ===================================================================

def extrair_company_id(record):
    """Extrai company_id numerico de um record Odoo."""
    company = record.get('company_id', [None, None])
    if isinstance(company, (list, tuple)):
        return company[0]
    return company


def extrair_partner_id(record):
    """Extrai partner_id numerico de um record Odoo."""
    pid = record.get('partner_id')
    if pid and isinstance(pid, (list, tuple)):
        return pid[0]
    elif pid and isinstance(pid, int):
        return pid
    return None


def filtrar_e_categorizar(records, partner_map, tipo):
    """
    Phase 6-7: Filtrar registros validos e categorizar motivo.

    Exclui:
    - Sem NF-e (x_studio_nf_e vazio/zero/False)
    - Intercompany (CNPJ do parceiro pertence ao grupo Nacom)
    - Empresa nao mapeada (company_id nao em 1/3/4)

    Categoriza:
    - "Quitado (saldo zero)" — amount_residual >= 0 (pagar) ou balance <= 0 (receber)
    - "Vencimento fora da janela (>90d)" — date_maturity muito antigo
    - "Elegivel — gap de timing" — deveria ter sido importado

    Args:
        records: lista de dicts do Odoo
        partner_map: {partner_id: {name, cnpj, ...}}
        tipo: 'pagar' ou 'receber'

    Returns:
        tuple: (filtrados, stats)
            filtrados: lista de dicts com dados + motivo
            stats: dict com contagens de exclusao
    """
    logger.info(f"[Phase 6-7] Filtrando e categorizando ({tipo.upper()})...")

    agora = agora_utc_naive()
    filtrados = []
    stats = {
        'total_input': len(records),
        'excluido_sem_nfe': 0,
        'excluido_intercompany': 0,
        'excluido_empresa': 0,
        'cat_quitado': 0,
        'cat_vencimento_antigo': 0,
        'cat_elegivel': 0,
    }

    for r in records:
        # --- FILTROS DE EXCLUSAO ---

        # Filtro 1: Sem NF-e
        nfe = r.get('x_studio_nf_e')
        if not nfe or nfe is False or str(nfe).strip() in ('', '0'):
            stats['excluido_sem_nfe'] += 1
            continue

        # Filtro 2: Empresa nao mapeada
        company_id = extrair_company_id(r)
        if company_id not in ODOO_COMPANY_IDS_ELEGIVEIS:
            stats['excluido_empresa'] += 1
            continue

        # Filtro 3: Intercompany
        partner_id_num = extrair_partner_id(r)
        p_info = partner_map.get(partner_id_num, {})
        partner_cnpj = p_info.get('l10n_br_cnpj') or ''
        if partner_cnpj and any(
            partner_cnpj.startswith(raiz) for raiz in CNPJS_RAIZ_GRUPO
        ):
            stats['excluido_intercompany'] += 1
            continue

        # --- CATEGORIZACAO ---

        amount_residual = float(r.get('amount_residual', 0) or 0)
        balance = float(r.get('balance', 0) or 0)
        vencimento = r.get('date_maturity')

        motivo = ""
        elegivel = False

        # Check quitado
        if tipo == 'pagar':
            quitado = amount_residual >= 0
        else:
            quitado = balance <= 0

        if quitado:
            motivo = "Quitado (saldo zero)"
            stats['cat_quitado'] += 1
        else:
            # Check janela de vencimento (D-90 para pagar)
            vencimento_antigo = False
            if tipo == 'pagar' and vencimento and vencimento is not False:
                try:
                    dt_venc = datetime.strptime(str(vencimento), '%Y-%m-%d')
                    dias_atras = (agora - dt_venc).days
                    if dias_atras > 90:
                        motivo = f"Vencimento fora da janela (>{dias_atras}d)"
                        vencimento_antigo = True
                        stats['cat_vencimento_antigo'] += 1
                except (ValueError, TypeError):
                    pass

            if not vencimento_antigo:
                motivo = "Elegivel — gap de timing"
                elegivel = True
                stats['cat_elegivel'] += 1

        # Valor original depende do tipo
        # PAGAR: credit = valor original (positivo)
        # RECEBER: balance = valor original
        if tipo == 'pagar':
            valor_original = float(r.get('credit', 0) or 0)
        else:
            valor_original = balance

        # Move info
        move = r.get('move_id', [None, None])
        move_nome = (
            move[1] if isinstance(move, (list, tuple)) and len(move) > 1
            else str(move)
        )

        filtrados.append({
            'record': r,
            'tipo': 'Pagar' if tipo == 'pagar' else 'Receber',
            'odoo_line_id': r.get('id'),
            'nfe': str(nfe).strip(),
            'parcela': r.get('l10n_br_cobranca_parcela') or '',
            'empresa': COMPANY_SIGLA.get(company_id, '?'),
            'move': move_nome,
            'emissao': r.get('date') or '',
            'vencimento': vencimento or '',
            'valor_original': valor_original,
            'valor_residual': abs(amount_residual),
            'partner_nome': p_info.get('name') or '',
            'partner_cnpj': partner_cnpj,
            'paga_l10n': bool(r.get('l10n_br_paga')),
            'reconciliado': bool(r.get('reconciled')),
            'motivo': motivo,
            'elegivel': elegivel,
            'matched_debit_ids': r.get('matched_debit_ids') or [],
            'matched_credit_ids': r.get('matched_credit_ids') or [],
            'full_reconcile_id': r.get('full_reconcile_id'),
        })

    # Log stats
    logger.info(f"  Input: {stats['total_input']}")
    logger.info(f"  Excluido sem NF-e: {stats['excluido_sem_nfe']}")
    logger.info(f"  Excluido intercompany: {stats['excluido_intercompany']}")
    logger.info(f"  Excluido empresa: {stats['excluido_empresa']}")
    logger.info(f"  Resultado: {len(filtrados)} titulos")
    logger.info(f"    Quitados: {stats['cat_quitado']}")
    logger.info(f"    Vencimento antigo: {stats['cat_vencimento_antigo']}")
    logger.info(f"    Elegiveis: {stats['cat_elegivel']}")

    return filtrados, stats


# ===================================================================
# PHASE 8: ENRIQUECER COM PAGAMENTO/EXTRATO
# ===================================================================

def enriquecer_com_pagamento(connection, filtrados):
    """
    Phase 8: Enriquecer com dados de pagamento (partial reconcile).

    Coletar TODOS matched_debit_ids + matched_credit_ids → batch read
    em account.partial.reconcile.

    Args:
        connection: OdooConnection autenticada
        filtrados: lista de dicts com matched_*_ids

    Returns:
        lista atualizada (in-place com campos pagamento/data_reconciliacao)
    """
    logger.info(f"[Phase 8] Enriquecendo com dados de pagamento...")

    # Coletar todos os partial reconcile IDs
    all_partial_ids = set()
    for item in filtrados:
        all_partial_ids.update(item.get('matched_debit_ids', []))
        all_partial_ids.update(item.get('matched_credit_ids', []))

    if not all_partial_ids:
        logger.info("  Nenhum partial reconcile encontrado")
        for item in filtrados:
            item['pagamento'] = ''
            item['valor_pagamento'] = ''
            item['data_reconciliacao'] = ''
        return filtrados

    logger.info(f"  {len(all_partial_ids)} partial reconcile IDs para buscar")

    # Batch read em account.partial.reconcile
    partial_map = {}
    partial_list = list(all_partial_ids)

    for i in range(0, len(partial_list), READ_BATCH):
        batch = partial_list[i:i + READ_BATCH]
        try:
            partials = connection.read(
                'account.partial.reconcile', batch, CAMPOS_PARTIAL,
            )
            for p in partials:
                partial_map[p['id']] = p
        except Exception as e:
            logger.warning(f"  Falha ao buscar partials batch {i // READ_BATCH + 1}: {e}")

    logger.info(f"  {len(partial_map)} partials obtidos")

    # Enriquecer cada item
    for item in filtrados:
        partial_ids = (
            item.get('matched_debit_ids', [])
            + item.get('matched_credit_ids', [])
        )

        pagamentos = []
        valor_total_pago = 0.0
        data_mais_recente = ''

        for pid in partial_ids:
            partial = partial_map.get(pid)
            if not partial:
                continue

            amount = float(partial.get('amount', 0) or 0)
            max_date = partial.get('max_date') or ''

            valor_total_pago += amount
            if max_date and max_date > data_mais_recente:
                data_mais_recente = max_date

            # credit_move_id e debit_move_id sao [id, name]
            credit_move = partial.get('credit_move_id')
            debit_move = partial.get('debit_move_id')

            # O move que NAO e o titulo e o pagamento/extrato
            titulo_id = item['odoo_line_id']
            for move_ref in [credit_move, debit_move]:
                if move_ref and isinstance(move_ref, (list, tuple)):
                    if move_ref[0] != titulo_id:
                        nome = move_ref[1] if len(move_ref) > 1 else str(move_ref[0])
                        pagamentos.append(nome)

        item['pagamento'] = ' | '.join(pagamentos) if pagamentos else ''
        item['valor_pagamento'] = round(valor_total_pago, 2) if valor_total_pago else ''
        item['data_reconciliacao'] = data_mais_recente

    return filtrados


# ===================================================================
# PHASE 9: EXPORTAR PARA EXCEL
# ===================================================================

def formatar_para_excel(filtrados):
    """
    Formata dados para o formato JSON esperado pelo exportar.py.

    Returns:
        list[dict]: Lista de dicts com colunas do Excel
    """
    logger.info(f"[Phase 9] Formatando {len(filtrados)} registros para Excel...")

    dados = []
    for item in filtrados:
        dados.append({
            'Tipo': item['tipo'],
            'Odoo Line ID': item['odoo_line_id'],
            'NF-e': item['nfe'],
            'Parcela': item['parcela'],
            'Empresa': item['empresa'],
            'Move': item['move'],
            'Emissao': item['emissao'],
            'Vencimento': item['vencimento'],
            'Valor Original': round(item['valor_original'], 2),
            'Valor Residual': round(item['valor_residual'], 2),
            'Parceiro Nome': item['partner_nome'],
            'Parceiro CNPJ': item['partner_cnpj'],
            'Paga (l10n_br)': item['paga_l10n'],
            'Reconciliado': item['reconciliado'],
            'Motivo Nao Importado': item['motivo'],
            'Elegivel': item['elegivel'],
            'Pagamento': item['pagamento'],
            'Valor Pagamento': item['valor_pagamento'],
            'Data Reconciliacao': item['data_reconciliacao'],
        })

    return dados


def exportar_excel(dados):
    """
    Exporta dados via pipe para exportar.py → Excel.

    Args:
        dados: lista de dicts com colunas do Excel

    Returns:
        dict: resultado do exportar.py
    """
    logger.info(f"  Exportando {len(dados)} registros para Excel...")

    json_input = json.dumps({'dados': dados}, ensure_ascii=False, default=str)

    # Caminho do exportar.py
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    exportar_script = os.path.join(
        base_dir,
        '.claude', 'skills', 'exportando-arquivos', 'scripts', 'exportar.py',
    )

    cmd = [
        sys.executable, exportar_script,
        '--formato', 'excel',
        '--nome', 'titulos_gap_odoo',
        '--titulo', 'Titulos Odoo Nao Importados - Gap Analysis',
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
        logger.error(f"  Retorno invalido do exportar.py: {result.stdout[:200]}")
        return None
    except Exception as e:
        logger.error(f"  Erro ao chamar exportar.py: {e}")
        return None


# ===================================================================
# ORQUESTRADOR
# ===================================================================

def processar_tipo(connection, tipo, limite=None, production_ids_dir=None):
    """
    Processa um tipo (pagar ou receber) completo.

    Args:
        connection: OdooConnection autenticada
        tipo: 'pagar' ou 'receber'
        limite: limite de gap_ids a processar (para teste)
        production_ids_dir: diretorio com IDs de producao pre-exportados

    Returns:
        tuple: (filtrados, stats)
    """
    tipo_label = tipo.upper()
    logger.info(f"\n{'=' * 60}")
    logger.info(f"PROCESSANDO: CONTAS A {tipo_label}")
    logger.info(f"{'=' * 60}")

    # Phase 1: IDs locais (producao ou local)
    ids_locais = coletar_ids_locais(tipo, production_ids_dir)

    # Phase 2: IDs Odoo
    ids_odoo = coletar_ids_odoo(connection, tipo)

    # Phase 3: Gap
    gap_ids = calcular_gap(ids_locais, ids_odoo)

    if not gap_ids:
        logger.info("  Nenhum gap encontrado!")
        return [], {}

    # Phase 4: Dados completos
    records, _usou_partner = buscar_dados_titulos(connection, gap_ids, limite)

    if not records:
        logger.error("  Nenhum registro retornado pelo read()!")
        return [], {}

    # Phase 5: Partners
    partner_map = buscar_partners(connection, records)

    # Phase 6-7: Filtrar e categorizar
    filtrados, stats = filtrar_e_categorizar(records, partner_map, tipo)

    # Phase 8: Enriquecer com pagamento
    if filtrados:
        # db.session.close() antes de queries Odoo longas
        db.session.close()
        filtrados = enriquecer_com_pagamento(connection, filtrados)

    return filtrados, stats


def main():
    parser = argparse.ArgumentParser(
        description='Exportar titulos Odoo faltantes para Excel (gap analysis)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Completo (pagar + receber)
  python scripts/exportar_titulos_gap_odoo.py

  # Apenas pagar
  python scripts/exportar_titulos_gap_odoo.py --tipo pagar

  # Apenas receber
  python scripts/exportar_titulos_gap_odoo.py --tipo receber

  # Limitar para teste (100 registros de gap por tipo)
  python scripts/exportar_titulos_gap_odoo.py --limite 100

  # Usar IDs de producao pre-exportados do Render
  python scripts/exportar_titulos_gap_odoo.py --production /tmp
        """,
    )
    parser.add_argument(
        '--tipo', choices=['pagar', 'receber'],
        help='Tipo de titulos (default: ambos)',
    )
    parser.add_argument(
        '--limite', type=int, default=None,
        help='Limite de gap IDs por tipo (para teste)',
    )
    parser.add_argument(
        '--production', type=str, default=None,
        metavar='DIR',
        help='Diretorio com render_pagar_ids.json e render_receber_ids.json '
             '(IDs de producao pre-exportados do Render via MCP)',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Logging detalhado (DEBUG)',
    )

    args = parser.parse_args()
    configurar_logging(args.verbose)

    inicio = agora_utc_naive()

    logger.info("=" * 60)
    logger.info("EXPORTAR TITULOS ODOO NAO IMPORTADOS — GAP ANALYSIS")
    logger.info(f"Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Tipo: {args.tipo or 'ambos'}")
    if args.production:
        logger.info(f"MODO PRODUCAO: IDs de {args.production}")
    if args.limite:
        logger.info(f"Limite: {args.limite} gap IDs por tipo")
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

        # Processar tipos
        todos_filtrados = []
        todos_stats = {}

        tipos = [args.tipo] if args.tipo else ['pagar', 'receber']

        for tipo in tipos:
            filtrados, stats = processar_tipo(
                connection, tipo, args.limite, args.production,
            )
            todos_filtrados.extend(filtrados)
            todos_stats[tipo] = stats

        if not todos_filtrados:
            logger.info("\nNenhum titulo faltante encontrado apos filtros!")
            sys.exit(0)

        # Phase 9: Exportar para Excel
        logger.info(f"\n{'=' * 60}")
        logger.info(f"EXPORTANDO {len(todos_filtrados)} TITULOS PARA EXCEL")
        logger.info(f"{'=' * 60}")

        dados_excel = formatar_para_excel(todos_filtrados)
        resultado = exportar_excel(dados_excel)

        if resultado and resultado.get('sucesso'):
            arquivo = resultado.get('arquivo', {})
            print(f"\n{'=' * 60}")
            print(f"EXCEL GERADO COM SUCESSO!")
            print(f"{'=' * 60}")
            print(f"  Arquivo: {arquivo.get('nome_original', '?')}")
            print(f"  Registros: {arquivo.get('registros', '?')}")
            print(f"  Tamanho: {arquivo.get('tamanho_formatado', '?')}")
            print(f"  URL: {arquivo.get('url_completa', '?')}")

            # Resumo por tipo
            for tipo, stats in todos_stats.items():
                print(f"\n  {tipo.upper()}:")
                print(f"    Total Odoo: {stats.get('total_input', 0)}")
                print(f"    Sem NF-e: -{stats.get('excluido_sem_nfe', 0)}")
                print(f"    Intercompany: -{stats.get('excluido_intercompany', 0)}")
                print(f"    Empresa invalida: -{stats.get('excluido_empresa', 0)}")
                print(f"    Quitados: {stats.get('cat_quitado', 0)}")
                print(f"    Vencimento antigo: {stats.get('cat_vencimento_antigo', 0)}")
                print(f"    Elegiveis: {stats.get('cat_elegivel', 0)}")

            print(f"{'=' * 60}")
        else:
            logger.error("Falha ao gerar Excel!")
            # Fallback: salvar JSON
            fallback_path = '/tmp/titulos_gap_odoo.json'
            with open(fallback_path, 'w', encoding='utf-8') as f:
                json.dump(dados_excel, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"  JSON fallback salvo em: {fallback_path}")

        # Tempo total
        fim = agora_utc_naive()
        duracao = (fim - inicio).total_seconds()
        logger.info(
            f"\nConcluido em {duracao:.0f}s "
            f"({fim.strftime('%Y-%m-%d %H:%M:%S')})"
        )


if __name__ == '__main__':
    main()
