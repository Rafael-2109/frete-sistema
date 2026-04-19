#!/usr/bin/env python3
"""A0.2 - NFs em junction CarviaOperacaoNf sem item na fatura (estima A2).

Detecta o padrao do Bug #1: CTe com N NFs, fatura tem apenas M < N items
com nf_id setado. Resultado esperado: (N - M) items suplementares precisariam
ser criados retroativamente.

Agrupa por:
  - Total de faturas afetadas
  - Total de items suplementares que A2 criaria
  - Por fatura: quantos items faltam

READ-ONLY.

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/count_nfs_sem_item_fatura.py
  python scripts/carvia/baseline_pre_sprint_a/count_nfs_sem_item_fatura.py --json
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402


def contar_nfs_faltantes_em_faturas():
    """Para cada fatura ativa, comparar junctions de NF vs items com nf_id."""
    from app.carvia.models import (
        CarviaFaturaCliente,
        CarviaFaturaClienteItem,
        CarviaOperacao,
        CarviaOperacaoNf,
    )

    # Faturas ativas (nao canceladas)
    faturas_ativas = CarviaFaturaCliente.query.filter(
        CarviaFaturaCliente.status != 'CANCELADA'
    ).all()

    total_faturas_ativas = len(faturas_ativas)
    faturas_afetadas = []
    total_items_suplementares_faltando = 0

    for fatura in faturas_ativas:
        # Buscar operacoes desta fatura
        operacao_ids = db.session.query(CarviaOperacao.id).filter(
            CarviaOperacao.fatura_cliente_id == fatura.id
        ).all()
        operacao_ids = [o[0] for o in operacao_ids]

        if not operacao_ids:
            continue

        # Para cada operacao, comparar junction vs items
        items_faltando_por_op = 0
        ops_com_gap = 0

        for op_id in operacao_ids:
            # NFs na junction
            junction_nf_ids = set(
                r[0] for r in db.session.query(
                    CarviaOperacaoNf.nf_id
                ).filter(CarviaOperacaoNf.operacao_id == op_id).all()
            )

            # NFs nos items da fatura para esta op
            items_nf_ids = set(
                r[0] for r in db.session.query(
                    CarviaFaturaClienteItem.nf_id
                ).filter(
                    CarviaFaturaClienteItem.fatura_cliente_id == fatura.id,
                    CarviaFaturaClienteItem.operacao_id == op_id,
                    CarviaFaturaClienteItem.nf_id.isnot(None),
                ).all()
            )

            diff = junction_nf_ids - items_nf_ids
            if diff:
                items_faltando_por_op += len(diff)
                ops_com_gap += 1

        if items_faltando_por_op > 0:
            faturas_afetadas.append({
                'fatura_id': fatura.id,
                'numero_fatura': fatura.numero_fatura,
                'status': fatura.status,
                'status_conferencia': getattr(fatura, 'status_conferencia', None),
                'operacoes_com_gap': ops_com_gap,
                'items_suplementares_faltando': items_faltando_por_op,
            })
            total_items_suplementares_faltando += items_faltando_por_op

    return {
        'total_faturas_ativas_analisadas': total_faturas_ativas,
        'faturas_afetadas': len(faturas_afetadas),
        'total_items_suplementares_faltando': total_items_suplementares_faltando,
        'amostra_faturas_afetadas': faturas_afetadas[:15],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        stats = contar_nfs_faltantes_em_faturas()

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
        return

    print('=' * 70)
    print('A0.2 - NFs sem item em faturas (estima esforco item A2 - Bug #1)')
    print('=' * 70)
    print(f"Faturas ativas analisadas:            {stats['total_faturas_ativas_analisadas']:>6}")
    print(f"Faturas afetadas (>=1 NF faltando):   {stats['faturas_afetadas']:>6}")
    print(f"Items suplementares a criar (total):  {stats['total_items_suplementares_faltando']:>6}")
    print()

    if stats['amostra_faturas_afetadas']:
        print('Amostra faturas afetadas (primeiras 15):')
        for f in stats['amostra_faturas_afetadas']:
            print(f"  fatura_id={f['fatura_id']:>5} num={f['numero_fatura']:<20} "
                  f"status={f['status']:<10} ops_gap={f['operacoes_com_gap']} "
                  f"items_faltando={f['items_suplementares_faltando']}")


if __name__ == '__main__':
    main()
