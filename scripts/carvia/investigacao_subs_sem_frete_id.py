#!/usr/bin/env python3
"""C1 (2026-04-19): investigacao read-only — subs sem frete_id.

Problema do plano: `CarviaSubcontrato.status=CONFERIDO` depende de
`CarviaFrete` associado via `frete_id`. Subs sem `frete_id` podem
nunca atingir CONFERIDO no lifecycle.

Este script:
  1. Conta subs sem frete_id por status, criado_em, fatura_transportadora_id
  2. Identifica se sao legado pre-Phase C ou drift operacional
  3. Gera relatorio textual com recomendacao

READ-ONLY. Uso local:
    source .venv/bin/activate
    python scripts/carvia/investigacao_subs_sem_frete_id.py
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        from app.carvia.models import CarviaSubcontrato

        total = CarviaSubcontrato.query.count()
        sem_frete_id = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.frete_id.is_(None)
        ).count()

        print('=' * 60)
        print('C1 — Subs sem frete_id (investigacao)')
        print('=' * 60)
        print(f'Total CarviaSubcontrato: {total}')
        pct = (sem_frete_id / total * 100) if total > 0 else 0.0
        print(f'Sem frete_id:            {sem_frete_id} ({pct:.1f}%)')
        print()

        print('Por status:')
        rows = (
            db.session.query(
                CarviaSubcontrato.status,
                func.count(CarviaSubcontrato.id),
            )
            .filter(CarviaSubcontrato.frete_id.is_(None))
            .group_by(CarviaSubcontrato.status)
            .all()
        )
        for status, qtd in rows:
            print(f'  {status:15s}: {qtd}')
        print()

        conferidos_sem_frete = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.frete_id.is_(None),
            CarviaSubcontrato.status == 'CONFERIDO',
        ).count()
        if conferidos_sem_frete > 0:
            print(f'⚠ ANOMALIA: {conferidos_sem_frete} subs CONFERIDO sem frete_id')
        else:
            print('✓ Nenhum sub CONFERIDO sem frete_id (ok)')

        faturados_sem_frete = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.frete_id.is_(None),
            CarviaSubcontrato.status == 'FATURADO',
        ).count()
        print(f'FATURADO sem frete_id: {faturados_sem_frete}')

        com_ft = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.frete_id.is_(None),
            CarviaSubcontrato.fatura_transportadora_id.isnot(None),
        ).count()
        print(f'Sem frete_id mas com fatura_transportadora_id: {com_ft}')
        print()

        print('=' * 60)
        print('RECOMENDACAO')
        print('=' * 60)
        if conferidos_sem_frete > 0:
            print('⛔ CRITICO: subs CONFERIDO sem frete_id exigem backfill.')
        elif sem_frete_id == 0:
            print('✓ Nenhum sub sem frete_id — dados consistentes.')
        elif faturados_sem_frete > 0 and conferidos_sem_frete == 0:
            print('✓ Subs sem frete_id sao legado pre-Phase C.')
            print('  Acao: aceitar como historico imutavel.')
        else:
            print('⚠ Investigar caso a caso.')

        print()
        print('Gerado em:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


if __name__ == '__main__':
    main()
