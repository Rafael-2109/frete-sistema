#!/usr/bin/env python3
"""A0.1 - Contar CTe Comp orfaos (estima esforco do item A1 do plano).

Categorias:
  - CTE_COMP_SEM_FATURA_COM_OP_FATURADA: fatura_cliente_id IS NULL
    e operacao_pai.fatura_cliente_id IS NOT NULL (candidato a retrolink)
  - CTE_COMP_SEM_FATURA_SEM_OP_FATURADA: fatura_cliente_id IS NULL
    e operacao_pai.fatura_cliente_id IS NULL (aguarda fatura chegar)
  - CTE_COMP_VINCULADO: fatura_cliente_id IS NOT NULL (OK)

READ-ONLY. Nao modifica dados.

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/count_cte_comp_orfaos.py
  python scripts/carvia/baseline_pre_sprint_a/count_cte_comp_orfaos.py --json
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def contar_cte_comp_orfaos():
    """Retorna stats de CTe Comps vs fatura vinculada via operacao pai."""
    from app.carvia.models import CarviaCteComplementar, CarviaOperacao

    q_total = db.session.query(func.count(CarviaCteComplementar.id)).scalar()

    # Join com operacao pai para decidir categoria
    q_base = db.session.query(
        CarviaCteComplementar.id,
        CarviaCteComplementar.numero_comp,
        CarviaCteComplementar.cte_numero,
        CarviaCteComplementar.status,
        CarviaCteComplementar.fatura_cliente_id,
        CarviaCteComplementar.operacao_id,
        CarviaOperacao.fatura_cliente_id.label('op_fatura_id'),
        CarviaOperacao.cte_numero.label('op_cte_numero'),
    ).join(
        CarviaOperacao,
        CarviaOperacao.id == CarviaCteComplementar.operacao_id,
    )

    vinculados = 0
    candidatos_retrolink = []
    aguardando_fatura = []

    for row in q_base.all():
        if row.fatura_cliente_id is not None:
            vinculados += 1
        elif row.op_fatura_id is not None:
            candidatos_retrolink.append({
                'id': row.id,
                'numero_comp': row.numero_comp,
                'cte_numero': row.cte_numero,
                'status': row.status,
                'operacao_id': row.operacao_id,
                'op_fatura_id': row.op_fatura_id,
                'op_cte_numero': row.op_cte_numero,
            })
        else:
            aguardando_fatura.append({
                'id': row.id,
                'numero_comp': row.numero_comp,
                'status': row.status,
            })

    return {
        'total_cte_complementares': q_total,
        'vinculados_a_fatura': vinculados,
        'candidatos_retrolink_a1': len(candidatos_retrolink),
        'aguardando_fatura_chegar': len(aguardando_fatura),
        'amostra_candidatos_retrolink': candidatos_retrolink[:10],
        'amostra_aguardando_fatura': aguardando_fatura[:10],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        stats = contar_cte_comp_orfaos()

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
        return

    print('=' * 70)
    print('A0.1 - CTe Comp orfaos (estima esforco item A1)')
    print('=' * 70)
    print(f"Total CTe Complementares:             {stats['total_cte_complementares']:>6}")
    print(f"  Vinculados a fatura (OK):           {stats['vinculados_a_fatura']:>6}")
    print(f"  Candidatos a retrolink (A1):        {stats['candidatos_retrolink_a1']:>6}")
    print(f"  Aguardando fatura chegar:           {stats['aguardando_fatura_chegar']:>6}")
    print()

    if stats['amostra_candidatos_retrolink']:
        print('Amostra candidatos retrolink (primeiros 10):')
        for c in stats['amostra_candidatos_retrolink']:
            print(f"  id={c['id']} COMP={c['numero_comp']} status={c['status']} "
                  f"op_id={c['operacao_id']} op_fatura={c['op_fatura_id']}")


if __name__ == '__main__':
    main()
