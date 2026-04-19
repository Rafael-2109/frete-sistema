#!/usr/bin/env python3
"""A0.4 - Operacoes sem XML do CTe (bloqueio parcial A4 backfill).

Conta CarviaOperacao onde cte_xml_path IS NULL. Essas operacoes nao podem
ter enderecos textuais preenchidos via re-parse em A4.3, porque nao ha XML
para baixar do S3.

Quebra por tipo_entrada:
  - IMPORTADO: tem XML (esperado)
  - MANUAL_FRETEIRO: sem XML (esperado — freteiro emite papel)
  - MANUAL_SEM_CTE: sem XML (esperado)
  - Outros: investigar

READ-ONLY.

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/count_operacoes_sem_xml.py
  python scripts/carvia/baseline_pre_sprint_a/count_operacoes_sem_xml.py --json
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def contar_operacoes_sem_xml():
    from app.carvia.models import CarviaOperacao

    total = CarviaOperacao.query.count()

    por_tipo = db.session.query(
        CarviaOperacao.tipo_entrada,
        func.count(CarviaOperacao.id).label('total'),
        func.count(CarviaOperacao.cte_xml_path).label('com_xml'),
    ).group_by(CarviaOperacao.tipo_entrada).all()

    breakdown = []
    for tipo, tot, com_xml in por_tipo:
        breakdown.append({
            'tipo_entrada': tipo or '(null)',
            'total': tot,
            'com_xml': com_xml,
            'sem_xml': tot - com_xml,
        })

    importado_sem_xml = db.session.query(CarviaOperacao).filter(
        CarviaOperacao.tipo_entrada == 'IMPORTADO',
        CarviaOperacao.cte_xml_path.is_(None),
    ).all()

    return {
        'total_operacoes': total,
        'breakdown_por_tipo_entrada': breakdown,
        'importado_sem_xml_count': len(importado_sem_xml),
        'amostra_importado_sem_xml': [
            {
                'id': op.id,
                'cte_numero': op.cte_numero,
                'status': op.status,
                'criado_em': op.criado_em.isoformat() if op.criado_em else None,
            }
            for op in importado_sem_xml[:10]
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        stats = contar_operacoes_sem_xml()

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False, default=str))
        return

    print('=' * 70)
    print('A0.4 - Operacoes sem XML (bloqueio parcial A4.3 backfill)')
    print('=' * 70)
    print(f"Total CarviaOperacao:                 {stats['total_operacoes']:>6}")
    print()
    print(f"{'tipo_entrada':<20} {'total':>8} {'com_xml':>8} {'sem_xml':>8}")
    for b in stats['breakdown_por_tipo_entrada']:
        print(f"  {b['tipo_entrada']:<18} {b['total']:>8} {b['com_xml']:>8} {b['sem_xml']:>8}")
    print()
    print(f"IMPORTADO sem XML (ANOMALIA):         {stats['importado_sem_xml_count']:>6}")
    if stats['importado_sem_xml_count'] > 0:
        print('  ⚠ IMPORTADO deveria ter XML — investigar causa raiz')


if __name__ == '__main__':
    main()
