# -*- coding: utf-8 -*-
"""
Script de Backfill: Sincronizacao Cruzada Comprovantes <-> Extrato <-> Odoo
============================================================================

O servico bidirecional ConciliacaoSyncService foi criado em 2026-02-08.
Antes dessa data, reconciliacoes no Extrato e nos Comprovantes aconteciam
independentemente. Este backfill sincroniza ambos os lados e preenche dados
faltantes do Odoo.

Cenarios cobertos:
  A) Comprovante LANCADO -> ExtratoItem nao CONCILIADO
  B) ExtratoItem CONCILIADO -> Comprovante nao reconciliado
  C) Odoo reconciliado -> ExtratoItem local nao reflete
  D) Odoo reconciliado -> Comprovante local nao reflete
  E) Registros CONCILIADOS/reconciliados sem reconcile IDs

Uso:
    # Dry-run (apenas mostra o que faria, sem alterar nada)
    python scripts/backfill_sincronizacao_extrato_comprovantes.py --dry-run

    # Execucao real
    python scripts/backfill_sincronizacao_extrato_comprovantes.py

Autor: Sistema de Fretes
Data: 2026-02-09
"""

import sys
import os
import time

# Adiciona o diretorio raiz ao path para importar modulos do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.financeiro.models import ExtratoItem
from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.financeiro.services.conciliacao_sync_service import ConciliacaoSyncService
from app.utils.timezone import agora_utc_naive

ODOO_CHUNK_SIZE = 200   # IDs por query ao Odoo (evita timeout XML-RPC)
COMMIT_BATCH_SIZE = 50  # Commit ao DB local a cada N registros


def chunked(iterable, size):
    """Divide um iteravel em chunks de tamanho fixo."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def print_amostra(registros, label_fn, total_label="registros"):
    """Imprime amostra dos primeiros 20 + ultimos 5."""
    total = len(registros)
    amostra = registros[:20]
    amostra_final = registros[-5:] if total > 25 else []

    for r in amostra:
        print(f"  {label_fn(r)}")
    if total > 25:
        print(f"  ... ({total - 25} {total_label} omitidos) ...")
        for r in amostra_final:
            print(f"  {label_fn(r)}")


# ===========================================================================
#  ETAPA 1: DIAGNOSTICO (read-only)
# ===========================================================================

def diagnostico():
    """
    Quantifica cada cenario de desync.
    Retorna dict com contagens e listas de IDs para cada cenario.
    """
    resultado = {}

    # Cenario A: Comprovante LANCADO -> ExtratoItem nao CONCILIADO
    cenario_a = db.session.query(
        ComprovantePagamentoBoleto.id,
        ComprovantePagamentoBoleto.odoo_statement_line_id,
        ExtratoItem.id.label('extrato_item_id'),
        ExtratoItem.status.label('extrato_status'),
    ).join(
        LancamentoComprovante,
        LancamentoComprovante.comprovante_id == ComprovantePagamentoBoleto.id,
    ).join(
        ExtratoItem,
        ExtratoItem.statement_line_id == ComprovantePagamentoBoleto.odoo_statement_line_id,
    ).filter(
        LancamentoComprovante.status == 'LANCADO',
        ComprovantePagamentoBoleto.odoo_statement_line_id.isnot(None),
        ExtratoItem.status != 'CONCILIADO',
    ).distinct().all()

    resultado['cenario_a'] = {
        'count': len(cenario_a),
        'comprovante_ids': [r[0] for r in cenario_a],
    }

    # Cenario B: ExtratoItem CONCILIADO -> Comprovante nao reconciliado
    cenario_b = db.session.query(
        ExtratoItem.id,
        ExtratoItem.statement_line_id,
        ComprovantePagamentoBoleto.id.label('comprovante_id'),
        ComprovantePagamentoBoleto.odoo_is_reconciled,
    ).join(
        ComprovantePagamentoBoleto,
        ComprovantePagamentoBoleto.odoo_statement_line_id == ExtratoItem.statement_line_id,
    ).filter(
        ExtratoItem.status == 'CONCILIADO',
        ExtratoItem.statement_line_id.isnot(None),
        db.or_(
            ComprovantePagamentoBoleto.odoo_is_reconciled.is_(None),
            ComprovantePagamentoBoleto.odoo_is_reconciled == False,  # noqa: E712
        ),
    ).all()

    resultado['cenario_b'] = {
        'count': len(cenario_b),
        'extrato_item_ids': [r[0] for r in cenario_b],
    }

    # Cenario C: ExtratoItem nao CONCILIADO com statement_line_id, sem comprovante
    # (precisam verificacao no Odoo)
    cenario_c = db.session.query(
        ExtratoItem.id,
        ExtratoItem.statement_line_id,
        ExtratoItem.status,
    ).filter(
        ExtratoItem.status.notin_(['CONCILIADO', 'ERRO']),
        ExtratoItem.statement_line_id.isnot(None),
        ~ExtratoItem.statement_line_id.in_(
            db.session.query(ComprovantePagamentoBoleto.odoo_statement_line_id).filter(
                ComprovantePagamentoBoleto.odoo_statement_line_id.isnot(None)
            )
        ),
    ).all()

    resultado['cenario_c'] = {
        'count': len(cenario_c),
        'extrato_item_ids': [r[0] for r in cenario_c],
        'statement_line_ids': [r[1] for r in cenario_c],
    }

    # Cenario D: Comprovante com statement_line_id, nao reconciliado, sem extrato
    cenario_d = db.session.query(
        ComprovantePagamentoBoleto.id,
        ComprovantePagamentoBoleto.odoo_statement_line_id,
    ).filter(
        ComprovantePagamentoBoleto.odoo_statement_line_id.isnot(None),
        db.or_(
            ComprovantePagamentoBoleto.odoo_is_reconciled.is_(None),
            ComprovantePagamentoBoleto.odoo_is_reconciled == False,  # noqa: E712
        ),
        ~ComprovantePagamentoBoleto.odoo_statement_line_id.in_(
            db.session.query(ExtratoItem.statement_line_id).filter(
                ExtratoItem.statement_line_id.isnot(None)
            )
        ),
    ).all()

    resultado['cenario_d'] = {
        'count': len(cenario_d),
        'comprovante_ids': [r[0] for r in cenario_d],
        'statement_line_ids': [r[1] for r in cenario_d],
    }

    # Cenario E: Registros CONCILIADOS sem reconcile IDs
    cenario_e = db.session.query(
        ExtratoItem.id,
        ExtratoItem.statement_line_id,
    ).filter(
        ExtratoItem.status == 'CONCILIADO',
        ExtratoItem.full_reconcile_id.is_(None),
        ExtratoItem.statement_line_id.isnot(None),
    ).all()

    resultado['cenario_e'] = {
        'count': len(cenario_e),
        'extrato_item_ids': [r[0] for r in cenario_e],
        'statement_line_ids': [r[1] for r in cenario_e],
    }

    return resultado


def imprimir_diagnostico(diag, titulo="DIAGNOSTICO"):
    """Imprime resultados do diagnostico de forma formatada."""
    print(f"  --- {titulo} ---")
    print(f"  [A] Comprovante LANCADO, ExtratoItem nao CONCILIADO: {diag['cenario_a']['count']}")
    print(f"  [B] ExtratoItem CONCILIADO, Comprovante nao reconciliado: {diag['cenario_b']['count']}")
    print(f"  [C] ExtratoItem nao CONCILIADO, sem comprovante (verificar Odoo): {diag['cenario_c']['count']}")
    print(f"  [D] Comprovante nao reconciliado, sem ExtratoItem (verificar Odoo): {diag['cenario_d']['count']}")
    print(f"  [E] ExtratoItem CONCILIADO sem full_reconcile_id: {diag['cenario_e']['count']}")


# ===========================================================================
#  ETAPA 2: SYNC LOCAL -> LOCAL (sem Odoo)
# ===========================================================================

def sync_local_cenario_a(comprovante_ids, dry_run=False):
    """
    Cenario A: Comprovante LANCADO -> ExtratoItem nao CONCILIADO.
    Usa ConciliacaoSyncService.sync_comprovante_para_extrato().
    """
    sync_service = ConciliacaoSyncService()
    synced = 0
    erros = 0

    for comp_id in comprovante_ids:
        if dry_run:
            comp = db.session.get(ComprovantePagamentoBoleto, comp_id)
            if comp:
                ei = ExtratoItem.query.filter_by(
                    statement_line_id=comp.odoo_statement_line_id
                ).first()
                print(
                    f"  [DRY-RUN] SINCRONIZARIA: comp_id={comp_id} "
                    f"(statement_line={comp.odoo_statement_line_id}) "
                    f"-> ExtratoItem {ei.id if ei else '?'} "
                    f"(status atual: {ei.status if ei else '?'})"
                )
            synced += 1
        else:
            try:
                resultado = sync_service.sync_comprovante_para_extrato(comp_id)
                if resultado and resultado.get('action') == 'synced':
                    synced += 1
                    print(
                        f"  Synced: comp_id={comp_id} -> "
                        f"ExtratoItem {resultado['extrato_item_id']} CONCILIADO"
                    )
                elif resultado and resultado.get('action') == 'skip':
                    synced += 1  # ja estava ok
                else:
                    synced += 1  # nada a fazer (sem match)

                if synced % COMMIT_BATCH_SIZE == 0:
                    db.session.commit()
                    print(f"  ... commit parcial ({synced}/{len(comprovante_ids)})")

            except Exception as e:
                erros += 1
                print(f"  ERRO comp_id={comp_id}: {e}")
                db.session.rollback()

    if not dry_run and synced > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"  ERRO no commit final cenario A: {e}")
            erros += synced
            synced = 0

    return synced, erros


def sync_local_cenario_b(extrato_item_ids, dry_run=False):
    """
    Cenario B: ExtratoItem CONCILIADO -> Comprovante nao reconciliado.
    Usa ConciliacaoSyncService.sync_extrato_para_comprovante().
    """
    sync_service = ConciliacaoSyncService()
    synced = 0
    erros = 0

    for ei_id in extrato_item_ids:
        if dry_run:
            ei = db.session.get(ExtratoItem, ei_id)
            if ei:
                comp = ComprovantePagamentoBoleto.query.filter_by(
                    odoo_statement_line_id=ei.statement_line_id
                ).first()
                print(
                    f"  [DRY-RUN] SINCRONIZARIA: ExtratoItem {ei_id} "
                    f"(statement_line={ei.statement_line_id}) "
                    f"-> comp_id={comp.id if comp else '?'} "
                    f"(reconciled atual: {comp.odoo_is_reconciled if comp else '?'})"
                )
            synced += 1
        else:
            try:
                resultado = sync_service.sync_extrato_para_comprovante(ei_id)
                if resultado and resultado.get('action') == 'synced':
                    synced += 1
                    print(
                        f"  Synced: ExtratoItem {ei_id} -> "
                        f"Comprovante {resultado['comprovante_id']} "
                        f"odoo_is_reconciled=True"
                    )
                else:
                    synced += 1

                if synced % COMMIT_BATCH_SIZE == 0:
                    db.session.commit()
                    print(f"  ... commit parcial ({synced}/{len(extrato_item_ids)})")

            except Exception as e:
                erros += 1
                print(f"  ERRO ExtratoItem {ei_id}: {e}")
                db.session.rollback()

    if not dry_run and synced > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"  ERRO no commit final cenario B: {e}")
            erros += synced
            synced = 0

    return synced, erros


# ===========================================================================
#  ETAPA 3: SYNC ODOO -> LOCAL (Cenarios C e D)
# ===========================================================================

def sync_odoo_para_local(diag, dry_run=False):
    """
    Cenarios C e D: Consultar Odoo para statement lines nao sincronizadas.
    Retorna contadores (synced_extrato, synced_comprovante, erros).
    """
    # Coletar TODOS os statement_line_ids que precisam verificacao no Odoo
    statement_line_ids_c = diag['cenario_c'].get('statement_line_ids', [])
    statement_line_ids_d = diag['cenario_d'].get('statement_line_ids', [])

    # Unificar IDs unicos
    todos_ids = list(set(statement_line_ids_c + statement_line_ids_d))

    if not todos_ids:
        print("  Nenhum statement_line_id para verificar no Odoo.")
        return 0, 0, 0

    # Conectar ao Odoo
    print(f"  Consultando Odoo para {len(todos_ids)} statement_line_ids...")
    try:
        from app.odoo.utils.connection import get_odoo_connection
        connection = get_odoo_connection()
        connection.authenticate()
    except Exception as e:
        print(f"  ERRO ao conectar ao Odoo: {e}")
        return 0, 0, 1

    synced_extrato = 0
    synced_comprovante = 0
    erros = 0
    total_reconciliados_odoo = 0

    # Processar em chunks
    total_chunks = (len(todos_ids) + ODOO_CHUNK_SIZE - 1) // ODOO_CHUNK_SIZE

    for idx_chunk, chunk_ids in enumerate(chunked(todos_ids, ODOO_CHUNK_SIZE), 1):
        t0 = time.time()
        try:
            linhas_odoo = connection.search_read(
                'account.bank.statement.line',
                [['id', 'in', chunk_ids]],
                fields=['id', 'is_reconciled', 'move_id'],
            )
        except Exception as e:
            erros += 1
            print(f"  ERRO chunk {idx_chunk}/{total_chunks}: {e}")
            continue

        elapsed = time.time() - t0

        # Filtrar reconciliados
        reconciliados = {
            l['id']: l for l in linhas_odoo if l.get('is_reconciled')
        }
        total_reconciliados_odoo += len(reconciliados)

        print(
            f"  Chunk {idx_chunk}/{total_chunks}: "
            f"{len(chunk_ids)} IDs -> {len(linhas_odoo)} encontrados, "
            f"{len(reconciliados)} reconciliados ({elapsed:.1f}s)"
        )

        if not reconciliados:
            continue

        # Atualizar ExtratoItems (Cenario C)
        for sl_id in reconciliados:
            # Buscar ExtratoItem com esse statement_line_id
            ei = ExtratoItem.query.filter_by(statement_line_id=sl_id).first()
            if ei and ei.status != 'CONCILIADO':
                if dry_run:
                    print(
                        f"  [DRY-RUN] ATUALIZARIA: ExtratoItem {ei.id} "
                        f"(statement_line={sl_id}) -> CONCILIADO (via Odoo)"
                    )
                else:
                    ei.status = 'CONCILIADO'
                    ei.processado_em = agora_utc_naive()
                    ei.mensagem = 'Conciliado via backfill sync Odoo'
                synced_extrato += 1

            # Buscar Comprovante com esse statement_line_id (Cenario D)
            comp = ComprovantePagamentoBoleto.query.filter_by(
                odoo_statement_line_id=sl_id
            ).first()
            if comp and not comp.odoo_is_reconciled:
                if dry_run:
                    print(
                        f"  [DRY-RUN] ATUALIZARIA: Comprovante {comp.id} "
                        f"(statement_line={sl_id}) -> odoo_is_reconciled=True (via Odoo)"
                    )
                else:
                    comp.odoo_is_reconciled = True
                synced_comprovante += 1

        # Commit parcial por chunk
        if not dry_run:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                erros += 1
                print(f"  ERRO commit chunk {idx_chunk}: {e}")

    print(
        f"  Total reconciliados no Odoo: {total_reconciliados_odoo}/{len(todos_ids)}"
    )

    return synced_extrato, synced_comprovante, erros


# ===========================================================================
#  ETAPA 4: PREENCHER RECONCILE IDs FALTANTES (Cenario E)
# ===========================================================================

def preencher_reconcile_ids(diag, dry_run=False):
    """
    Cenario E: ExtratoItems CONCILIADOS sem full_reconcile_id.
    Consulta Odoo para preencher os IDs faltantes.
    Retorna (preenchidos, erros).
    """
    statement_line_ids = diag['cenario_e'].get('statement_line_ids', [])
    extrato_item_ids = diag['cenario_e'].get('extrato_item_ids', [])

    if not statement_line_ids:
        print("  Nenhum ExtratoItem CONCILIADO com reconcile_id faltante.")
        return 0, 0

    # Conectar ao Odoo
    print(f"  Consultando Odoo para {len(statement_line_ids)} statement lines...")
    try:
        from app.odoo.utils.connection import get_odoo_connection
        connection = get_odoo_connection()
        connection.authenticate()
    except Exception as e:
        print(f"  ERRO ao conectar ao Odoo: {e}")
        return 0, 1

    # Montar mapeamento para _buscar_dados_conciliacao_preexistente
    # Precisamos do move_id de cada ExtratoItem
    ei_por_sl_id = {}
    for ei_id, sl_id in zip(extrato_item_ids, statement_line_ids):
        ei = db.session.get(ExtratoItem, ei_id)
        if ei and ei.move_id:
            ei_por_sl_id[sl_id] = {
                'extrato_item_id': ei_id,
                'move_id': ei.move_id,
            }

    if not ei_por_sl_id:
        print("  Nenhum ExtratoItem com move_id para consultar.")
        return 0, 0

    preenchidos = 0
    erros = 0

    # Buscar move_lines com full_reconcile_id em chunks
    todos_sl_ids = list(ei_por_sl_id.keys())
    total_chunks = (len(todos_sl_ids) + ODOO_CHUNK_SIZE - 1) // ODOO_CHUNK_SIZE

    for idx_chunk, chunk_ids in enumerate(chunked(todos_sl_ids, ODOO_CHUNK_SIZE), 1):
        t0 = time.time()

        # Coletar move_ids deste chunk
        chunk_move_ids = [
            ei_por_sl_id[sl_id]['move_id']
            for sl_id in chunk_ids
            if sl_id in ei_por_sl_id
        ]

        if not chunk_move_ids:
            continue

        try:
            # Buscar move_lines de debito dos moves do extrato com reconcile info
            move_lines = connection.search_read(
                'account.move.line',
                [
                    ['move_id', 'in', chunk_move_ids],
                    ['debit', '>', 0],
                ],
                fields=['id', 'move_id', 'full_reconcile_id'],
            )
        except Exception as e:
            erros += 1
            print(f"  ERRO chunk {idx_chunk}/{total_chunks}: {e}")
            continue

        elapsed = time.time() - t0

        # Mapear move_id -> full_reconcile_id
        reconcile_por_move = {}
        for ml in move_lines:
            move_id_val = ml.get('move_id')
            move_id = move_id_val[0] if isinstance(move_id_val, (list, tuple)) else move_id_val
            full_rec = ml.get('full_reconcile_id')
            full_rec_id = full_rec[0] if isinstance(full_rec, (list, tuple)) and full_rec else (
                full_rec if full_rec else None
            )
            if move_id and full_rec_id:
                reconcile_por_move[move_id] = full_rec_id

        print(
            f"  Chunk {idx_chunk}/{total_chunks}: "
            f"{len(chunk_move_ids)} move_ids -> "
            f"{len(reconcile_por_move)} com full_reconcile_id ({elapsed:.1f}s)"
        )

        # Atualizar ExtratoItems e LancamentoComprovantes
        for sl_id in chunk_ids:
            dados = ei_por_sl_id.get(sl_id)
            if not dados:
                continue

            full_rec_id = reconcile_por_move.get(dados['move_id'])
            if not full_rec_id:
                continue

            ei = db.session.get(ExtratoItem, dados['extrato_item_id'])
            if not ei:
                continue

            if dry_run:
                print(
                    f"  [DRY-RUN] PREENCHERIA: ExtratoItem {ei.id} "
                    f"full_reconcile_id={full_rec_id}"
                )
            else:
                ei.full_reconcile_id = full_rec_id

                # Tambem propagar para LancamentoComprovante se existir
                comp = ComprovantePagamentoBoleto.query.filter_by(
                    odoo_statement_line_id=sl_id
                ).first()
                if comp:
                    lanc = LancamentoComprovante.query.filter_by(
                        comprovante_id=comp.id,
                        status='LANCADO',
                    ).order_by(LancamentoComprovante.lancado_em.desc()).first()
                    if lanc and not lanc.odoo_full_reconcile_extrato_id:
                        lanc.odoo_full_reconcile_extrato_id = full_rec_id

            preenchidos += 1

        # Commit parcial por chunk
        if not dry_run:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                erros += 1
                print(f"  ERRO commit chunk {idx_chunk}: {e}")

    return preenchidos, erros


# ===========================================================================
#  MAIN
# ===========================================================================

def main():
    dry_run = '--dry-run' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 80)
        if dry_run:
            print("  BACKFILL SINCRONIZACAO EXTRATO <-> COMPROVANTES (DRY-RUN)")
        else:
            print("  BACKFILL SINCRONIZACAO EXTRATO <-> COMPROVANTES")
        print("=" * 80)
        print()

        # ─── ETAPA 1: DIAGNOSTICO ──────────────────────────────────────
        print("[Etapa 1] Diagnostico de desync...")
        t0 = time.time()
        diag_antes = diagnostico()
        elapsed = time.time() - t0
        print()
        imprimir_diagnostico(diag_antes, "ANTES")
        print(f"  (diagnostico em {elapsed:.1f}s)")
        print()

        total_desync = sum(
            diag_antes[k]['count'] for k in diag_antes
        )
        if total_desync == 0:
            print("Nenhum desync encontrado. Sistema ja esta sincronizado.")
            return

        # ─── ETAPA 2: SYNC LOCAL -> LOCAL ───────────────────────────────
        print("[Etapa 2] Sync Local -> Local (sem Odoo)...")
        print()

        # Cenario A
        ids_a = diag_antes['cenario_a']['comprovante_ids']
        if ids_a:
            print(f"  [A] Sincronizando {len(ids_a)} comprovante(s) LANCADO(s) -> ExtratoItem...")
            synced_a, erros_a = sync_local_cenario_a(ids_a, dry_run)
            print(f"  [A] Resultado: {synced_a} synced, {erros_a} erro(s)")
        else:
            synced_a, erros_a = 0, 0
            print("  [A] Nenhum registro para sincronizar.")
        print()

        # Cenario B
        ids_b = diag_antes['cenario_b']['extrato_item_ids']
        if ids_b:
            print(f"  [B] Sincronizando {len(ids_b)} ExtratoItem(ns) CONCILIADO(s) -> Comprovante...")
            synced_b, erros_b = sync_local_cenario_b(ids_b, dry_run)
            print(f"  [B] Resultado: {synced_b} synced, {erros_b} erro(s)")
        else:
            synced_b, erros_b = 0, 0
            print("  [B] Nenhum registro para sincronizar.")
        print()

        # ─── ETAPA 3: SYNC ODOO -> LOCAL ────────────────────────────────
        ids_c = diag_antes['cenario_c'].get('statement_line_ids', [])
        ids_d = diag_antes['cenario_d'].get('statement_line_ids', [])
        total_cd = len(set(ids_c + ids_d))

        if total_cd > 0:
            print(f"[Etapa 3] Sync Odoo -> Local ({total_cd} statement_line_ids)...")
            print()
            synced_ei, synced_comp, erros_cd = sync_odoo_para_local(diag_antes, dry_run)
            print(
                f"  Resultado: {synced_ei} ExtratoItems atualizados, "
                f"{synced_comp} Comprovantes atualizados, {erros_cd} erro(s)"
            )
        else:
            synced_ei, synced_comp, erros_cd = 0, 0, 0
            print("[Etapa 3] Nenhum registro para verificar no Odoo (cenarios C/D).")
        print()

        # ─── ETAPA 4: PREENCHER RECONCILE IDs ──────────────────────────
        ids_e = diag_antes['cenario_e'].get('statement_line_ids', [])
        if ids_e:
            print(f"[Etapa 4] Preenchendo reconcile IDs faltantes ({len(ids_e)} registros)...")
            print()
            preenchidos, erros_e = preencher_reconcile_ids(diag_antes, dry_run)
            print(f"  Resultado: {preenchidos} preenchidos, {erros_e} erro(s)")
        else:
            preenchidos, erros_e = 0, 0
            print("[Etapa 4] Nenhum ExtratoItem CONCILIADO com reconcile_id faltante.")
        print()

        # ─── ETAPA 5: VERIFICACAO ──────────────────────────────────────
        print("[Etapa 5] Verificacao pos-backfill...")
        if not dry_run:
            diag_depois = diagnostico()
            print()
            imprimir_diagnostico(diag_depois, "DEPOIS")
            print()

            # Comparar
            print("  COMPARACAO ANTES x DEPOIS:")
            for cenario in ['cenario_a', 'cenario_b', 'cenario_c', 'cenario_d', 'cenario_e']:
                antes = diag_antes[cenario]['count']
                depois = diag_depois[cenario]['count']
                label = cenario.upper().replace('_', ' ')
                delta = antes - depois
                sinal = f"-{delta}" if delta > 0 else f"+{abs(delta)}" if delta < 0 else "0"
                print(f"  {label}: {antes} -> {depois} ({sinal})")
        else:
            print("  (DRY-RUN: verificacao pos-backfill pulada)")
        print()

        # ─── RESUMO ─────────────────────────────────────────────────────
        total_erros = erros_a + erros_b + erros_cd + erros_e
        print("=" * 80)
        print("  RESUMO")
        print("=" * 80)
        prefixo = "[DRY-RUN] " if dry_run else ""
        print(f"  {prefixo}Cenario A (Comp LANCADO -> Extrato): {synced_a} sincronizado(s)")
        print(f"  {prefixo}Cenario B (Extrato CONCIL -> Comp):  {synced_b} sincronizado(s)")
        print(f"  {prefixo}Cenario C (Odoo -> ExtratoItem):     {synced_ei} atualizado(s)")
        print(f"  {prefixo}Cenario D (Odoo -> Comprovante):     {synced_comp} atualizado(s)")
        print(f"  {prefixo}Cenario E (Reconcile IDs):           {preenchidos} preenchido(s)")
        print(f"  Erros totais:                                  {total_erros}")
        if dry_run:
            print()
            print("  (DRY-RUN: nenhum registro foi alterado)")
        print("=" * 80)


if __name__ == '__main__':
    main()
