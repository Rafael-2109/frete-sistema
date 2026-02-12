# -*- coding: utf-8 -*-
"""
Backfill: Capturar partial_reconcile_id de itens já conciliados
================================================================

~1,815 itens de ENTRADA marcados como CONCILIADO que têm o extrato
reconciliado no Odoo (via write_date, backfill, revalidação) mas não
capturaram o partial_reconcile_id/full_reconcile_id localmente.

O script:
1. Busca itens CONCILIADO sem partial/full_reconcile_id
   (EXCLUINDO Strategy 3 fallback — tratados por outro script)
2. Busca credit_line_id no Odoo em batches
3. Se reconciliado, sincroniza os IDs localmente

Puramente cosmético — não altera nada no Odoo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_partial_reconcile_id_extrato.py --dry-run
    python scripts/migrations/backfill_partial_reconcile_id_extrato.py
    python scripts/migrations/backfill_partial_reconcile_id_extrato.py --tipo entrada
    python scripts/migrations/backfill_partial_reconcile_id_extrato.py --tipo saida

Ref: Investigação de 2026-02-11 (~1,815 itens cosmetic)
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Batch size para queries no Odoo
BATCH_SIZE = 50


def buscar_itens_sem_reconcile_id(tipo_transacao=None):
    """
    Busca itens CONCILIADO sem partial_reconcile_id e sem full_reconcile_id.

    Exclui itens Strategy 3 fallback (tratados pelo script de remediação).
    """
    from app.financeiro.models import ExtratoItem, ExtratoLote
    from sqlalchemy import or_

    query = ExtratoItem.query.filter(
        ExtratoItem.status == 'CONCILIADO',
        ExtratoItem.partial_reconcile_id.is_(None),
        ExtratoItem.full_reconcile_id.is_(None),
        ExtratoItem.credit_line_id.isnot(None),
        # Excluir Strategy 3 (tratado por remediar_strategy3_extrato_solto.py)
        or_(
            ExtratoItem.mensagem.is_(None),
            ~ExtratoItem.mensagem.like(
                'Título já quitado no Odoo - extrato não reconciliado%'
            )
        )
    )

    if tipo_transacao:
        query = query.join(ExtratoLote).filter(
            ExtratoLote.tipo_transacao == tipo_transacao
        )

    return query.order_by(ExtratoItem.id).all()


def sincronizar_batch(itens_batch, conn, dry_run=False):
    """
    Sincroniza partial/full_reconcile_id para um batch de itens.

    Busca os credit_line_ids no Odoo em uma única query e
    atualiza os itens localmente.

    Returns:
        Dict com contadores: sincronizados, nao_reconciliados, erros
    """
    from app import db

    stats = {'sincronizados': 0, 'nao_reconciliados': 0, 'erros': 0}

    credit_line_ids = [item.credit_line_id for item in itens_batch]

    try:
        linhas = conn.search_read(
            'account.move.line',
            [['id', 'in', credit_line_ids]],
            fields=[
                'id', 'reconciled',
                'matched_debit_ids', 'matched_credit_ids',
                'full_reconcile_id'
            ]
        )
    except Exception as e:
        logger.error(f"  Erro ao buscar linhas no Odoo: {e}")
        stats['erros'] = len(itens_batch)
        return stats

    linhas_por_id = {l['id']: l for l in linhas}

    for item in itens_batch:
        linha = linhas_por_id.get(item.credit_line_id)

        if not linha:
            stats['erros'] += 1
            continue

        if not linha.get('reconciled'):
            stats['nao_reconciliados'] += 1
            continue

        # Extrair IDs de reconciliação
        matched = (
            linha.get('matched_debit_ids', [])
            or linha.get('matched_credit_ids', [])
        )
        full_rec = linha.get('full_reconcile_id')

        if not dry_run:
            if matched:
                item.partial_reconcile_id = matched[-1]
            if full_rec:
                item.full_reconcile_id = (
                    full_rec[0]
                    if isinstance(full_rec, (list, tuple))
                    else full_rec
                )

        stats['sincronizados'] += 1

    if not dry_run:
        db.session.flush()

    return stats


def executar():
    parser = argparse.ArgumentParser(
        description=(
            'Backfill: capturar partial_reconcile_id de itens '
            'já conciliados (cosmético)'
        )
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Simular sem alterar o banco local'
    )
    parser.add_argument(
        '--tipo', choices=['entrada', 'saida'], default=None,
        help='Filtrar por tipo de transação'
    )
    args = parser.parse_args()

    from app import create_app
    from app.odoo.utils.connection import get_odoo_connection

    app = create_app()
    with app.app_context():
        from app import db

        print("=" * 70)
        print("BACKFILL: partial_reconcile_id de itens conciliados")
        print(f"Modo: {'DRY-RUN' if args.dry_run else 'EXECUCAO REAL'}")
        if args.tipo:
            print(f"Tipo: {args.tipo}")
        print("=" * 70)

        # Autenticar no Odoo
        conn = get_odoo_connection()
        if not conn.authenticate():
            print("ERRO: Falha na autenticacao com Odoo")
            sys.exit(1)

        # Buscar itens
        itens = buscar_itens_sem_reconcile_id(tipo_transacao=args.tipo)

        print(f"\nItens encontrados: {len(itens)}")

        if not itens:
            print("Nenhum item para sincronizar.")
            return

        # Mostrar resumo
        valor_total = sum(abs(i.valor or 0) for i in itens)
        print(f"Valor total: R$ {valor_total:,.2f}")

        lotes = set(i.lote_id for i in itens)
        print(f"Lotes afetados: {len(lotes)}")
        print()

        # Processar em batches
        total_stats = {
            'sincronizados': 0,
            'nao_reconciliados': 0,
            'erros': 0
        }

        for i in range(0, len(itens), BATCH_SIZE):
            batch = itens[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(itens) + BATCH_SIZE - 1) // BATCH_SIZE

            print(
                f"Batch {batch_num}/{total_batches} "
                f"(itens {i + 1}-{min(i + BATCH_SIZE, len(itens))})"
            )

            stats = sincronizar_batch(batch, conn, dry_run=args.dry_run)

            for k, v in stats.items():
                total_stats[k] += v

            print(
                f"  sync={stats['sincronizados']}, "
                f"nao_rec={stats['nao_reconciliados']}, "
                f"erros={stats['erros']}"
            )

        if not args.dry_run:
            db.session.commit()

        # Resumo final
        print()
        print("=" * 70)
        print("RESUMO")
        print("=" * 70)
        print(f"  Sincronizados: {total_stats['sincronizados']}")
        print(f"  Nao reconciliados no Odoo: {total_stats['nao_reconciliados']}")
        print(f"  Erros: {total_stats['erros']}")

        if args.dry_run:
            print(
                f"\nDRY-RUN: {total_stats['sincronizados']} itens seriam "
                f"atualizados. Para executar: remova --dry-run"
            )


if __name__ == '__main__':
    executar()
