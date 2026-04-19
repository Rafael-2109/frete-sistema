#!/usr/bin/env python3
"""A0.3 - CTe Comp sem CTRNC (estima esforco item A3 - Bug #3).

Conta CarviaCteComplementar onde ctrc_numero IS NULL mas cte_numero IS NOT NULL
(candidatos a preenchimento via SSW 101).

Divide por:
  - Criados < 30 dias (urgente — SSW ainda tem o CTRNC indexado)
  - Criados 30-90 dias (intermediario)
  - Criados > 90 dias (pode ter sido expurgado no SSW)

READ-ONLY.

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/count_cte_comp_sem_ctrc.py
  python scripts/carvia/baseline_pre_sprint_a/count_cte_comp_sem_ctrc.py --json
"""

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def contar_cte_comp_sem_ctrc():
    from app.carvia.models import CarviaCteComplementar
    from app.utils.timezone import agora_utc_naive

    agora = agora_utc_naive()
    dt_30 = agora - timedelta(days=30)
    dt_90 = agora - timedelta(days=90)

    base = CarviaCteComplementar.query.filter(
        CarviaCteComplementar.ctrc_numero.is_(None),
        CarviaCteComplementar.cte_numero.isnot(None),
    )

    total = base.count()

    q_buckets = db.session.query(
        func.count(CarviaCteComplementar.id).filter(
            CarviaCteComplementar.criado_em >= dt_30,
        ).label('ate_30d'),
        func.count(CarviaCteComplementar.id).filter(
            CarviaCteComplementar.criado_em < dt_30,
            CarviaCteComplementar.criado_em >= dt_90,
        ).label('de_30_a_90d'),
        func.count(CarviaCteComplementar.id).filter(
            CarviaCteComplementar.criado_em < dt_90,
        ).label('mais_90d'),
    ).filter(
        CarviaCteComplementar.ctrc_numero.is_(None),
        CarviaCteComplementar.cte_numero.isnot(None),
    ).first()

    amostra = base.order_by(CarviaCteComplementar.criado_em.desc()).limit(10).all()

    return {
        'total_cte_comp_sem_ctrc': total,
        'ate_30_dias': q_buckets.ate_30d or 0,
        'de_30_a_90_dias': q_buckets.de_30_a_90d or 0,
        'mais_de_90_dias': q_buckets.mais_90d or 0,
        'amostra': [
            {
                'id': c.id,
                'numero_comp': c.numero_comp,
                'cte_numero': c.cte_numero,
                'status': c.status,
                'criado_em': c.criado_em.isoformat() if c.criado_em else None,
            }
            for c in amostra
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        stats = contar_cte_comp_sem_ctrc()

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
        return

    print('=' * 70)
    print('A0.3 - CTe Comp sem CTRNC (estima esforco A3 - Bug #3)')
    print('=' * 70)
    print(f"Total CTe Comp sem ctrc_numero:       {stats['total_cte_comp_sem_ctrc']:>6}")
    print(f"  <= 30 dias (urgente):               {stats['ate_30_dias']:>6}")
    print(f"  30-90 dias (intermediario):         {stats['de_30_a_90_dias']:>6}")
    print(f"  > 90 dias (pode estar expurgado):   {stats['mais_de_90_dias']:>6}")
    print()
    print(f"Estimativa backfill: {stats['total_cte_comp_sem_ctrc']} jobs SSW 101")
    print(f"  Tempo estimado (~90s/job): {stats['total_cte_comp_sem_ctrc'] * 90 // 60} min")


if __name__ == '__main__':
    main()
