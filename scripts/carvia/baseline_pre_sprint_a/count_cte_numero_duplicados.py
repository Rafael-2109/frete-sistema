#!/usr/bin/env python3
"""A0.5 - Duplicados em numeros sequenciais (bloqueia UniqueConstraint B2).

Checa se ha duplicatas em:
  - CarviaOperacao.cte_numero (formato 'CTe-###')
  - CarviaSubcontrato.cte_numero (formato 'Sub-###')
  - CarviaCteComplementar.numero_comp (formato 'COMP-###')

Se houver duplicatas, B2 (UniqueConstraint) precisa de script de remediacao
antes da migration.

READ-ONLY.

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/count_cte_numero_duplicados.py
  python scripts/carvia/baseline_pre_sprint_a/count_cte_numero_duplicados.py --json
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def contar_duplicados():
    from app.carvia.models import (
        CarviaOperacao,
        CarviaSubcontrato,
        CarviaCteComplementar,
    )

    dupes = {
        'carvia_operacao.cte_numero': [],
        'carvia_subcontrato.cte_numero': [],
        'carvia_cte_complementar.numero_comp': [],
    }

    # CarviaOperacao
    q_op = db.session.query(
        CarviaOperacao.cte_numero,
        func.count(CarviaOperacao.id).label('qtd'),
    ).filter(
        CarviaOperacao.cte_numero.isnot(None),
    ).group_by(CarviaOperacao.cte_numero).having(
        func.count(CarviaOperacao.id) > 1,
    ).all()

    for cte, qtd in q_op:
        dupes['carvia_operacao.cte_numero'].append({'valor': cte, 'qtd': qtd})

    # CarviaSubcontrato
    q_sub = db.session.query(
        CarviaSubcontrato.cte_numero,
        func.count(CarviaSubcontrato.id).label('qtd'),
    ).filter(
        CarviaSubcontrato.cte_numero.isnot(None),
    ).group_by(CarviaSubcontrato.cte_numero).having(
        func.count(CarviaSubcontrato.id) > 1,
    ).all()

    for cte, qtd in q_sub:
        dupes['carvia_subcontrato.cte_numero'].append({'valor': cte, 'qtd': qtd})

    # CarviaCteComplementar
    q_comp = db.session.query(
        CarviaCteComplementar.numero_comp,
        func.count(CarviaCteComplementar.id).label('qtd'),
    ).filter(
        CarviaCteComplementar.numero_comp.isnot(None),
    ).group_by(CarviaCteComplementar.numero_comp).having(
        func.count(CarviaCteComplementar.id) > 1,
    ).all()

    for num, qtd in q_comp:
        dupes['carvia_cte_complementar.numero_comp'].append({'valor': num, 'qtd': qtd})

    return dupes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        dupes = contar_duplicados()

    if args.json:
        print(json.dumps(dupes, indent=2, ensure_ascii=False, default=str))
        return

    print('=' * 70)
    print('A0.5 - Numeros sequenciais duplicados (bloqueia B2 UniqueConstraint)')
    print('=' * 70)
    for tabela_coluna, lista in dupes.items():
        print(f"{tabela_coluna}: {len(lista)} valor(es) duplicado(s)")
        for d in lista[:5]:
            print(f"  valor={d['valor']} ocorre {d['qtd']}x")
        if len(lista) > 5:
            print(f"  ... e mais {len(lista) - 5}")
    print()

    total_dupes = sum(len(v) for v in dupes.values())
    if total_dupes == 0:
        print('OK: B2 UniqueConstraint pode ser aplicada diretamente')
    else:
        print(f'ATENCAO: {total_dupes} grupos de duplicatas detectados.')
        print('  B2 exige script de remediacao ANTES da migration.')


if __name__ == '__main__':
    main()
