"""
Backfill: Numeracao sequencial para CTe CarVia e CTe Subcontrato
================================================================

Data fix (sem DDL) — preenche cte_numero onde NULL:
- carvia_operacoes: CTe-001, CTe-002, ...
- carvia_subcontratos: Sub-001, Sub-002, ...

Idempotente: so atualiza registros com cte_numero IS NULL.
Ordena por id para manter sequencia cronologica.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.carvia.models import CarviaOperacao, CarviaSubcontrato


def backfill_numeracao():
    """Preenche cte_numero em operacoes e subcontratos sem numero."""

    # --- CTe CarVia (CarviaOperacao) ---
    # Descobrir o maior numero existente
    max_cte = db.session.query(CarviaOperacao.cte_numero).filter(
        CarviaOperacao.cte_numero.ilike('CTe-%'),
    ).order_by(CarviaOperacao.cte_numero.desc()).first()

    next_cte_num = 1
    if max_cte and max_cte[0]:
        try:
            next_cte_num = int(max_cte[0].replace('CTe-', '')) + 1
        except (ValueError, TypeError):
            pass

    # Buscar operacoes sem numero
    operacoes_sem = db.session.query(CarviaOperacao).filter(
        CarviaOperacao.cte_numero.is_(None),
    ).order_by(CarviaOperacao.id).all()

    print(f"Operacoes sem cte_numero: {len(operacoes_sem)}")
    for op in operacoes_sem:
        op.cte_numero = f'CTe-{next_cte_num:03d}'
        print(f"  Operacao #{op.id} -> {op.cte_numero}")
        next_cte_num += 1

    # --- CTe Subcontrato (CarviaSubcontrato) ---
    max_sub = db.session.query(CarviaSubcontrato.cte_numero).filter(
        CarviaSubcontrato.cte_numero.ilike('Sub-%'),
    ).order_by(CarviaSubcontrato.cte_numero.desc()).first()

    next_sub_num = 1
    if max_sub and max_sub[0]:
        try:
            next_sub_num = int(max_sub[0].replace('Sub-', '')) + 1
        except (ValueError, TypeError):
            pass

    # Buscar subcontratos sem numero
    subs_sem = db.session.query(CarviaSubcontrato).filter(
        CarviaSubcontrato.cte_numero.is_(None),
    ).order_by(CarviaSubcontrato.id).all()

    print(f"Subcontratos sem cte_numero: {len(subs_sem)}")
    for sub in subs_sem:
        sub.cte_numero = f'Sub-{next_sub_num:03d}'
        print(f"  Subcontrato #{sub.id} -> {sub.cte_numero}")
        next_sub_num += 1

    db.session.commit()
    print(f"\nBackfill concluido: {len(operacoes_sem)} operacoes + {len(subs_sem)} subcontratos atualizados.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # BEFORE
        total_op_sem = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.cte_numero.is_(None),
        ).count()
        total_sub_sem = db.session.query(CarviaSubcontrato).filter(
            CarviaSubcontrato.cte_numero.is_(None),
        ).count()
        print(f"BEFORE: {total_op_sem} operacoes + {total_sub_sem} subcontratos sem cte_numero")

        backfill_numeracao()

        # AFTER
        total_op_sem = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.cte_numero.is_(None),
        ).count()
        total_sub_sem = db.session.query(CarviaSubcontrato).filter(
            CarviaSubcontrato.cte_numero.is_(None),
        ).count()
        print(f"AFTER: {total_op_sem} operacoes + {total_sub_sem} subcontratos sem cte_numero")
