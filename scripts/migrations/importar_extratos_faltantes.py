#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importação em Massa de Extratos Faltantes do Odoo
==================================================

Diagnóstico PRODUÇÃO (2026-02-19):
- 33.598 linhas no Odoo, 19.455 na produção (Render) = 57.9% cobertura
- ~14.143 linhas faltantes distribuídas em 8 journals bancários
- Journals com gap: SIC/10 (7.372), GRA1/883 (3.693), SIC/386 (2.213), BRAD/388 (747)
- Journals 100% sincronizados: AGISG/1046, CAIXA/389
- Journals nunca importados: SIC/386 (LF), SANT/1030 (LF)

EXECUTAR NO RENDER SHELL (não localmente).

Estratégia:
1. Para cada journal_id, buscar TODOS os IDs de statement_line no Odoo
2. Comparar com IDs na produção (extrato_item.statement_line_id)
3. Buscar linhas faltantes em batches de 200 por ['id', 'in', batch_ids]
4. Processar via ExtratoService._processar_linha() (reutiliza lógica existente)
5. Para conciliados sem título: enriquecer via reconciliação do Odoo (move lines)
6. Commit a cada batch com rollback em caso de falha + retry

Resiliência:
- Commit por batch (200 linhas) — queda de conexão perde no máximo 1 batch
- Retry 3x com backoff exponencial em falhas de conexão Odoo
- db.session.rollback() antes de retry em falhas DB
- _processar_linha() já faz deduplicação por statement_line_id
- Idempotente: pode ser executado múltiplas vezes
- Sem operações destrutivas

Conciliação:
- Itens is_reconciled=True no Odoo → status=CONCILIADO no sistema
- Passo 1: Tenta vincular via ComprovantePagamentoBoleto local (comprovantes recentes)
- Passo 2: Se sem título, enriquece via Odoo: busca move_lines reconciliados → invoice
  → extrai NF/parceiro → vincula ContasAPagar/ContasAReceber local
- NÃO modifica títulos (a "baixa" é feita por outros processos)

Uso:
    python scripts/migrations/importar_extratos_faltantes.py [--dry-run] [--journal-id 10] [--batch-size 200]
"""

import sys
import os
import argparse
import logging
import time
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Journals bancários com dados no Odoo (diagnosticados em 2026-02-19)
JOURNALS_CONHECIDOS = [
    {'journal_id': 10,   'code': 'SIC',   'name': 'SICOOB (FB)',         'company': 'NACOM GOYA - FB'},
    {'journal_id': 883,  'code': 'GRA1',  'name': 'GRAFENO',             'company': 'NACOM GOYA - FB'},
    {'journal_id': 386,  'code': 'SIC',   'name': 'SICOOB (LF)',         'company': 'LA FAMIGLIA - LF'},
    {'journal_id': 388,  'code': 'BRAD',  'name': 'BRADESCO (FB)',       'company': 'NACOM GOYA - FB'},
    {'journal_id': 1046, 'code': 'AGISG', 'name': 'AGIS GARANTIDA',     'company': 'NACOM GOYA - FB'},
    {'journal_id': 1030, 'code': 'SANT',  'name': 'SANTANDER',           'company': 'LA FAMIGLIA - LF'},
    {'journal_id': 1054, 'code': 'VORTX', 'name': 'BRADESCO (cópia)',    'company': 'NACOM GOYA - FB'},
    {'journal_id': 389,  'code': 'CAIXA', 'name': 'CAIXA ECONÔMICA (FB)','company': 'NACOM GOYA - FB'},
]

# Batch sizes
ODOO_BATCH_SIZE = 200
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # segundos

# Campos necessários do Odoo
ODOO_FIELDS = [
    'id', 'date', 'payment_ref', 'amount', 'amount_residual',
    'partner_id', 'partner_name', 'account_number',
    'journal_id', 'statement_id', 'move_id',
    'is_reconciled', 'transaction_type', 'company_id'
]

# Regex para extrair NF de refs do Odoo
REGEX_NF_NUMBER = re.compile(r'(?:NF|NFe?|NOTA)\s*(?:FISCAL)?\s*[:\-]?\s*(\d{3,9})', re.IGNORECASE)
REGEX_NF_SLASH = re.compile(r'(\d{3,9})\s*/\s*(\d{1,3})')  # NF/parcela


def get_odoo_connection():
    """Cria e autentica conexão Odoo."""
    from app.odoo.utils.connection import get_odoo_connection
    conn = get_odoo_connection()
    if not conn.authenticate():
        raise Exception("Falha na autenticação com Odoo")
    return conn


def odoo_call_with_retry(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """
    Executa chamada Odoo com retry + backoff exponencial.

    Em caso de falha de conexão (timeout, XML-RPC error), aguarda e tenta novamente.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            # Erros recuperáveis: timeout, conexão, XML-RPC
            is_retryable = any(term in error_msg for term in [
                'timeout', 'connection', 'refused', 'reset',
                'broken pipe', 'eof', 'xmlrpc', 'socket',
                'transport', 'http', 'ssl'
            ])
            if not is_retryable or attempt == max_retries:
                raise
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                f"  Retry {attempt}/{max_retries} após erro: {e}. "
                f"Aguardando {wait}s..."
            )
            time.sleep(wait)
    raise last_error


def buscar_ids_odoo(conn, journal_id: int) -> list:
    """Busca TODOS os IDs de statement_line de um journal no Odoo."""
    ids = odoo_call_with_retry(
        conn.execute_kw,
        'account.bank.statement.line',
        'search',
        [[['journal_id', '=', journal_id]]],
        {'limit': 0}
    )
    return ids or []


def buscar_ids_locais(journal_id: int) -> set:
    """Busca todos os statement_line_id já importados para um journal_id."""
    from app.financeiro.models import ExtratoItem

    rows = db.session.query(
        ExtratoItem.statement_line_id
    ).filter(
        ExtratoItem.journal_id == journal_id,
        ExtratoItem.statement_line_id.isnot(None)
    ).all()

    return {r[0] for r in rows}


def buscar_linhas_por_ids(conn, ids: list) -> list:
    """Busca linhas de extrato por IDs específicos (com retry)."""
    return odoo_call_with_retry(
        conn.search_read,
        'account.bank.statement.line',
        [['id', 'in', ids]],
        fields=ODOO_FIELDS,
        limit=0
    )


def enriquecer_conciliados_batch(conn, items_conciliados: list, _svc=None) -> dict:
    """
    Para itens CONCILIADO sem título vinculado, busca dados de
    reconciliação no Odoo e tenta vincular ao título local.

    Fluxo:
    1. Filtra itens sem titulo_pagar_id e sem titulo_receber_id
    2. Busca move_lines com full_reconcile_id para os move_ids
    3. Busca contrapartida (invoice move_lines) via reconcile_ids
    4. Extrai NF/parceiro das invoices
    5. Match contra ContasAPagar/ContasAReceber local

    Returns:
        Dict com stats do enriquecimento
    """
    stats = {'tentativas': 0, 'vinculados_pagar': 0, 'vinculados_receber': 0, 'sem_match': 0, 'erros': 0}

    # 1. Filtrar itens sem título
    items_sem_titulo = [
        i for i in items_conciliados
        if i.titulo_pagar_id is None and i.titulo_receber_id is None and i.move_id
    ]

    if not items_sem_titulo:
        return stats

    stats['tentativas'] = len(items_sem_titulo)
    move_ids = [i.move_id for i in items_sem_titulo]
    item_por_move = {i.move_id: i for i in items_sem_titulo}

    try:
        # 2. Buscar move_lines com full_reconcile_id para esses moves
        rec_lines = odoo_call_with_retry(
            conn.search_read,
            'account.move.line',
            [
                ['move_id', 'in', move_ids],
                ['full_reconcile_id', '!=', False]
            ],
            fields=['id', 'move_id', 'full_reconcile_id'],
            limit=0
        )

        if not rec_lines:
            stats['sem_match'] = len(items_sem_titulo)
            return stats

        # Mapear move_id → reconcile_id(s)
        move_to_reconcile = {}
        reconcile_ids_set = set()
        for rl in rec_lines:
            mid = rl['move_id'][0] if isinstance(rl['move_id'], (list, tuple)) else rl['move_id']
            rid = rl['full_reconcile_id'][0] if isinstance(rl['full_reconcile_id'], (list, tuple)) else rl['full_reconcile_id']
            move_to_reconcile.setdefault(mid, set()).add(rid)
            reconcile_ids_set.add(rid)

        reconcile_ids = list(reconcile_ids_set)

        # 3. Buscar TODAS as move_lines com esses reconcile_ids (contrapartida)
        counterpart_lines = odoo_call_with_retry(
            conn.search_read,
            'account.move.line',
            [
                ['full_reconcile_id', 'in', reconcile_ids],
                ['move_id', 'not in', move_ids]  # Excluir as linhas do próprio statement
            ],
            fields=['id', 'move_id', 'full_reconcile_id', 'name', 'ref', 'partner_id'],
            limit=0
        )

        if not counterpart_lines:
            stats['sem_match'] = len(items_sem_titulo)
            return stats

        # 4. Mapear reconcile_id → counterpart move info
        reconcile_to_info = {}
        counterpart_move_ids = set()
        for cl in counterpart_lines:
            rid = cl['full_reconcile_id'][0] if isinstance(cl['full_reconcile_id'], (list, tuple)) else cl['full_reconcile_id']
            cmid = cl['move_id'][0] if isinstance(cl['move_id'], (list, tuple)) else cl['move_id']
            counterpart_move_ids.add(cmid)
            if rid not in reconcile_to_info:
                partner_id = cl['partner_id'][0] if isinstance(cl['partner_id'], (list, tuple)) and cl['partner_id'] else None
                partner_name = cl['partner_id'][1] if isinstance(cl['partner_id'], (list, tuple)) and len(cl['partner_id']) > 1 else None
                reconcile_to_info[rid] = {
                    'counterpart_move_id': cmid,
                    'ref': cl.get('ref') or '',
                    'name': cl.get('name') or '',
                    'partner_id': partner_id,
                    'partner_name': partner_name,
                }

        # 5. Buscar refs dos moves de contrapartida (invoices)
        if counterpart_move_ids:
            invoice_moves = odoo_call_with_retry(
                conn.search_read,
                'account.move',
                [['id', 'in', list(counterpart_move_ids)]],
                fields=['id', 'name', 'ref', 'partner_id', 'move_type'],
                limit=0
            )
            invoice_map = {m['id']: m for m in invoice_moves}

            # Enriquecer reconcile_to_info com dados da invoice
            for rid, info in reconcile_to_info.items():
                inv = invoice_map.get(info['counterpart_move_id'])
                if inv:
                    info['invoice_name'] = inv.get('name') or ''
                    info['invoice_ref'] = inv.get('ref') or ''
                    info['move_type'] = inv.get('move_type') or ''
                    if not info['partner_id'] and inv.get('partner_id'):
                        pid = inv['partner_id']
                        info['partner_id'] = pid[0] if isinstance(pid, (list, tuple)) else pid
                        info['partner_name'] = pid[1] if isinstance(pid, (list, tuple)) and len(pid) > 1 else None

        # 6. Para cada item, tentar vincular título local
        for move_id, item in item_por_move.items():
            try:
                rids = move_to_reconcile.get(move_id, set())
                if not rids:
                    stats['sem_match'] += 1
                    continue

                # Pegar a primeira reconciliação
                rid = next(iter(rids))
                info = reconcile_to_info.get(rid)
                if not info:
                    stats['sem_match'] += 1
                    continue

                # Combinar todas as refs para busca de NF
                refs_combined = ' '.join(filter(None, [
                    info.get('ref', ''),
                    info.get('name', ''),
                    info.get('invoice_name', ''),
                    info.get('invoice_ref', ''),
                    item.payment_ref or '',
                ]))

                # Tentar extrair NF da ref
                nf_match = REGEX_NF_SLASH.search(refs_combined) or REGEX_NF_NUMBER.search(refs_combined)
                nf_numero = nf_match.group(1) if nf_match else None

                # Atualizar partner no item se não tinha
                if info.get('partner_id') and not item.odoo_partner_id:
                    item.odoo_partner_id = info['partner_id']
                    item.odoo_partner_name = info.get('partner_name')

                vinculado = False

                if item.valor < 0:
                    # SAÍDA → ContasAPagar
                    titulo = _buscar_titulo_pagar(nf_numero, info, item)
                    if titulo:
                        item.titulo_pagar_id = titulo.id
                        item.titulo_nf = nf_numero or titulo.titulo_nf
                        item.titulo_valor = titulo.valor_residual
                        item.titulo_vencimento = titulo.vencimento
                        item.titulo_cliente = titulo.raz_social_red or titulo.raz_social
                        item.titulo_cnpj = titulo.cnpj
                        item.status_match = 'MATCH_ENCONTRADO'
                        stats['vinculados_pagar'] += 1
                        vinculado = True
                else:
                    # ENTRADA → ContasAReceber
                    titulo = _buscar_titulo_receber(nf_numero, info, item)
                    if titulo:
                        item.titulo_receber_id = titulo.id
                        item.titulo_nf = nf_numero or titulo.titulo_nf
                        item.titulo_valor = titulo.valor_titulo
                        item.titulo_vencimento = titulo.vencimento
                        item.titulo_cliente = titulo.cliente
                        item.titulo_cnpj = titulo.cnpj_cpf
                        item.status_match = 'MATCH_ENCONTRADO'
                        stats['vinculados_receber'] += 1
                        vinculado = True

                if not vinculado:
                    stats['sem_match'] += 1
                    # Enriquecer mensagem com dados disponíveis do Odoo
                    detalhes = []
                    if info.get('partner_name'):
                        detalhes.append(f"parceiro={info['partner_name']}")
                    if info.get('invoice_ref'):
                        detalhes.append(f"ref={info['invoice_ref']}")
                    if nf_numero:
                        detalhes.append(f"NF={nf_numero}")
                    if detalhes:
                        item.mensagem = (
                            f"Conciliado no Odoo (sem título local). "
                            f"Dados Odoo: {', '.join(detalhes)}"
                        )

            except Exception as e:
                logger.warning(f"    Erro ao enriquecer item move_id={move_id}: {e}")
                stats['erros'] += 1

    except Exception as e:
        logger.warning(f"  Erro no enriquecimento batch via Odoo: {e}")
        stats['erros'] += len(items_sem_titulo)

    return stats


def _buscar_titulo_pagar(nf_numero, odoo_info, item):
    """Tenta encontrar ContasAPagar pelo NF ou CNPJ + valor."""
    from app.financeiro.models import ContasAPagar

    valor_abs = abs(item.valor)

    # Estratégia 1: NF número exato
    if nf_numero:
        titulo = ContasAPagar.query.filter_by(titulo_nf=nf_numero).first()
        if titulo:
            return titulo

    # Estratégia 2: CNPJ + valor aproximado (tolerância de 1%)
    cnpj = item.cnpj_pagador
    if not cnpj and odoo_info.get('partner_name'):
        # Tentar extrair CNPJ do nome do parceiro Odoo (fallback)
        pass
    if cnpj:
        titulos = ContasAPagar.query.filter_by(cnpj=cnpj).all()
        for t in titulos:
            if t.valor_residual and abs(t.valor_residual - valor_abs) < valor_abs * 0.01:
                return t

    return None


def _buscar_titulo_receber(nf_numero, odoo_info, item):
    """Tenta encontrar ContasAReceber pelo NF ou CNPJ + valor."""
    from app.financeiro.models import ContasAReceber

    valor_abs = abs(item.valor)

    # Estratégia 1: NF número exato
    if nf_numero:
        titulo = ContasAReceber.query.filter_by(titulo_nf=nf_numero).first()
        if titulo:
            return titulo

    # Estratégia 2: CNPJ + valor aproximado
    cnpj = item.cnpj_pagador
    if not cnpj and odoo_info.get('partner_name'):
        # Tentar extrair CNPJ do nome do parceiro Odoo (fallback)
        pass
    if cnpj:
        titulos = ContasAReceber.query.filter_by(cnpj_cpf=cnpj).all()
        for t in titulos:
            if t.valor_titulo and abs(t.valor_titulo - valor_abs) < valor_abs * 0.01:
                return t

    return None


def importar_journal(conn, journal_info: dict, batch_size: int, dry_run: bool) -> dict:
    """
    Importa todas as linhas faltantes de um journal com:
    - Retry + backoff em falhas Odoo
    - Rollback DB em falhas de batch
    - Enriquecimento de conciliados via reconciliação Odoo
    """
    from app.financeiro.models import ExtratoLote
    from app.financeiro.services.extrato_service import ExtratoService
    from app.utils.timezone import agora_utc_naive

    journal_id = journal_info['journal_id']
    journal_code = journal_info['code']
    journal_name = journal_info['name']
    company = journal_info['company']

    stats = {
        'journal_id': journal_id,
        'journal_code': journal_code,
        'company': company,
        'odoo_total': 0,
        'local_total': 0,
        'faltantes': 0,
        'importados': 0,
        'ja_conciliados': 0,
        'enriquecidos_pagar': 0,
        'enriquecidos_receber': 0,
        'sem_match_titulo': 0,
        'erros': 0,
        'batches_ok': 0,
        'batches_falha': 0,
        'tempo_s': 0,
    }

    logger.info(f"{'='*60}")
    logger.info(f"JOURNAL: {journal_code} (id={journal_id}) — {journal_name} [{company}]")
    logger.info(f"{'='*60}")

    t0 = time.time()

    # 1. Buscar IDs no Odoo
    logger.info("Buscando IDs no Odoo...")
    ids_odoo = buscar_ids_odoo(conn, journal_id)
    stats['odoo_total'] = len(ids_odoo)
    logger.info(f"  Odoo: {len(ids_odoo)} linhas")

    if not ids_odoo:
        logger.info("  Nenhuma linha no Odoo, pulando.")
        return stats

    # 2. Buscar IDs locais
    ids_locais = buscar_ids_locais(journal_id)
    stats['local_total'] = len(ids_locais)
    logger.info(f"  Local: {len(ids_locais)} linhas")

    # 3. Calcular faltantes
    ids_faltantes = sorted(set(ids_odoo) - ids_locais)
    stats['faltantes'] = len(ids_faltantes)
    logger.info(f"  Faltantes: {len(ids_faltantes)} linhas")

    if not ids_faltantes:
        logger.info("  Nenhuma linha faltante, journal sincronizado!")
        stats['tempo_s'] = round(time.time() - t0, 1)
        return stats

    if dry_run:
        logger.info(f"  [DRY-RUN] Não importando. IDs faltantes: {ids_faltantes[:10]}...")
        stats['tempo_s'] = round(time.time() - t0, 1)
        return stats

    # 4. Criar lote de importação
    code_label = f"{journal_code}_{journal_id}"
    nome_lote = (
        f"Bulk Import {code_label} ({journal_name}) "
        f"{agora_utc_naive().strftime('%Y-%m-%d %H:%M')}"
    )
    lote = ExtratoLote(
        nome=nome_lote,
        journal_code=journal_code,
        journal_id=journal_id,
        status='IMPORTADO',
        tipo_transacao='ambos',
        criado_por='bulk_import'
    )
    db.session.add(lote)
    db.session.flush()
    db.session.commit()  # Commit lote antes dos batches
    logger.info(f"  Lote criado: #{lote.id}")

    # 5. Importar em batches com retry e rollback
    svc = ExtratoService(connection=conn)
    valor_total = 0
    total_batches = (len(ids_faltantes) + batch_size - 1) // batch_size

    for i in range(0, len(ids_faltantes), batch_size):
        batch_ids = ids_faltantes[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        logger.info(
            f"  Batch {batch_num}/{total_batches}: "
            f"{len(batch_ids)} linhas (IDs {batch_ids[0]}..{batch_ids[-1]})"
        )

        batch_ok = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Buscar dados completos do Odoo (com retry interno)
                linhas = buscar_linhas_por_ids(conn, batch_ids)

                # Buscar linhas de crédito em batch (otimização, com retry)
                move_ids = []
                for linha in linhas:
                    mid = svc._extrair_id(linha.get('move_id'))
                    if mid:
                        move_ids.append(mid)

                credit_cache = {}
                if move_ids:
                    credit_cache = odoo_call_with_retry(
                        svc._buscar_linhas_credito_batch, move_ids
                    )

                # Processar cada linha
                batch_importados = 0
                batch_conciliados = 0
                items_conciliados_batch = []

                for linha in linhas:
                    try:
                        item = svc._processar_linha(
                            lote.id, linha, journal_code, journal_name,
                            credit_lines_cache=credit_cache
                        )
                        if item:
                            valor_total += item.valor
                            batch_importados += 1
                            if item.status == 'CONCILIADO':
                                batch_conciliados += 1
                                items_conciliados_batch.append(item)
                    except Exception as e:
                        logger.error(f"    Erro ao processar linha {linha.get('id')}: {e}")
                        stats['erros'] += 1

                # Flush antes do enriquecimento (itens precisam estar no session)
                db.session.flush()

                # Enriquecer conciliados sem título via Odoo
                enrich_stats = {'vinculados_pagar': 0, 'vinculados_receber': 0, 'sem_match': 0}
                if items_conciliados_batch:
                    enrich_stats = enriquecer_conciliados_batch(
                        conn, items_conciliados_batch
                    )

                # COMMIT do batch inteiro
                db.session.commit()

                stats['importados'] += batch_importados
                stats['ja_conciliados'] += batch_conciliados
                stats['enriquecidos_pagar'] += enrich_stats.get('vinculados_pagar', 0)
                stats['enriquecidos_receber'] += enrich_stats.get('vinculados_receber', 0)
                stats['sem_match_titulo'] += enrich_stats.get('sem_match', 0)
                stats['batches_ok'] += 1

                logger.info(
                    f"    OK: {batch_importados} importados "
                    f"({batch_conciliados} conciliados, "
                    f"{enrich_stats.get('vinculados_pagar', 0)+enrich_stats.get('vinculados_receber', 0)} com título)"
                )

                batch_ok = True
                break  # Batch bem-sucedido, sair do retry loop

            except Exception as e:
                # Rollback da transação corrompida
                db.session.rollback()

                error_msg = str(e).lower()
                is_retryable = any(term in error_msg for term in [
                    'timeout', 'connection', 'refused', 'reset',
                    'broken pipe', 'eof', 'closed', 'ssl',
                    'operationalerror', 'interfaceerror'
                ])

                if not is_retryable or attempt == MAX_RETRIES:
                    logger.error(
                        f"    FALHA batch {batch_num} (tentativa {attempt}/{MAX_RETRIES}): {e}"
                    )
                    stats['erros'] += len(batch_ids)
                    stats['batches_falha'] += 1
                    break

                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"    Retry batch {batch_num} ({attempt}/{MAX_RETRIES}): {e}. "
                    f"Aguardando {wait}s..."
                )
                time.sleep(wait)

                # Reconectar DB após rollback
                try:
                    db.session.close()
                except Exception:
                    pass

        if not batch_ok:
            logger.warning(f"    Batch {batch_num} falhou após {MAX_RETRIES} tentativas")

    # 6. Atualizar totais do lote
    try:
        lote.total_linhas = stats['importados']
        lote.valor_total = valor_total
        db.session.commit()
    except Exception as e:
        logger.error(f"  Erro ao atualizar lote: {e}")
        db.session.rollback()

    stats['tempo_s'] = round(time.time() - t0, 1)

    logger.info(
        f"  CONCLUÍDO: {stats['importados']}/{stats['faltantes']} importados "
        f"({stats['ja_conciliados']} conciliados, "
        f"{stats['enriquecidos_pagar']+stats['enriquecidos_receber']} com título), "
        f"{stats['batches_ok']}/{stats['batches_ok']+stats['batches_falha']} batches OK, "
        f"{stats['erros']} erros, {stats['tempo_s']}s"
    )

    return stats


def main():
    parser = argparse.ArgumentParser(description='Importar extratos faltantes do Odoo')
    parser.add_argument('--dry-run', action='store_true', help='Apenas diagnosticar, não importar')
    parser.add_argument('--journal-id', type=int, help='Importar apenas journal específico')
    parser.add_argument('--batch-size', type=int, default=ODOO_BATCH_SIZE,
                        help=f'Batch size (default: {ODOO_BATCH_SIZE})')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        logger.info("=" * 60)
        logger.info("IMPORTAÇÃO EM MASSA DE EXTRATOS FALTANTES")
        logger.info(f"Modo: {'DRY-RUN' if args.dry_run else 'PRODUÇÃO'}")
        logger.info(f"Batch size: {args.batch_size}")
        logger.info(f"Retry: {MAX_RETRIES}x com backoff {RETRY_BACKOFF_BASE}s")
        logger.info("=" * 60)

        conn = get_odoo_connection()

        # Filtrar journals se especificado
        journals = JOURNALS_CONHECIDOS
        if args.journal_id:
            journals = [j for j in journals if j['journal_id'] == args.journal_id]
            if not journals:
                logger.error(f"Journal ID {args.journal_id} não encontrado na lista conhecida")
                sys.exit(1)

        # Importar cada journal
        resultados = []
        t0_global = time.time()

        for journal_info in journals:
            try:
                stats = importar_journal(conn, journal_info, args.batch_size, args.dry_run)
                resultados.append(stats)
            except Exception as e:
                logger.error(
                    f"ERRO FATAL no journal {journal_info['code']} "
                    f"(id={journal_info['journal_id']}): {e}"
                )
                import traceback
                traceback.print_exc()
                resultados.append({
                    'journal_id': journal_info['journal_id'],
                    'journal_code': journal_info['code'],
                    'company': journal_info['company'],
                    'erro_fatal': str(e),
                })

        # Resumo final
        tempo_total = round(time.time() - t0_global, 1)

        logger.info("")
        logger.info("=" * 60)
        logger.info("RESUMO FINAL")
        logger.info("=" * 60)

        total_odoo = 0
        total_local = 0
        total_faltantes = 0
        total_importados = 0
        total_conciliados = 0
        total_enriquecidos = 0
        total_erros = 0

        for r in resultados:
            if 'erro_fatal' in r:
                logger.error(
                    f"  {r['journal_code']} (id={r['journal_id']}): "
                    f"ERRO FATAL — {r['erro_fatal']}"
                )
                continue

            total_odoo += r['odoo_total']
            total_local += r['local_total']
            total_faltantes += r['faltantes']
            total_importados += r['importados']
            total_conciliados += r['ja_conciliados']
            enriq = r.get('enriquecidos_pagar', 0) + r.get('enriquecidos_receber', 0)
            total_enriquecidos += enriq
            total_erros += r['erros']

            batches_info = f"{r['batches_ok']}/{r['batches_ok']+r['batches_falha']}"
            logger.info(
                f"  {r['journal_code']:6s} (id={r['journal_id']:5d}) [{r['company']:20s}]: "
                f"Falt={r['faltantes']:6d}  Imp={r['importados']:6d}  "
                f"Conc={r['ja_conciliados']:6d}  Enriq={enriq:4d}  "
                f"Batches={batches_info}  Erros={r['erros']}  {r['tempo_s']}s"
            )

        logger.info("")
        logger.info(
            f"  TOTAIS: Odoo={total_odoo}  Local(antes)={total_local}  "
            f"Faltantes={total_faltantes}  Importados={total_importados}"
        )
        logger.info(
            f"  Conciliados={total_conciliados}  "
            f"Com título={total_enriquecidos}  Erros={total_erros}"
        )
        logger.info(f"  Tempo total: {tempo_total}s")

        if not args.dry_run and total_importados > 0:
            cobertura_antes = round(total_local / total_odoo * 100, 1) if total_odoo else 0
            cobertura_depois = round(
                (total_local + total_importados) / total_odoo * 100, 1
            ) if total_odoo else 0
            logger.info(f"  Cobertura: {cobertura_antes}% → {cobertura_depois}%")

        logger.info("=" * 60)


if __name__ == '__main__':
    main()
