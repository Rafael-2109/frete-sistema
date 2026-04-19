#!/usr/bin/env python3
"""A0.6 - Snapshot de valor_total por fatura (comparacao pos A1/A2).

Grava snapshot atual de fatura.valor_total em JSON. Apos execucao do Sprint A
(A1 retrolink CTe Comp + A2 expansao NFs), rodar novamente e comparar.

Mudancas esperadas:
  - Faturas que ganharam CTe Comp tardio: valor_total aumentou em sum(cte_comp.cte_valor)
  - Faturas que ganharam items suplementares de NF (A2): valor_total NAO muda (valor_mercadoria=None)

Uso:
  source .venv/bin/activate
  python scripts/carvia/baseline_pre_sprint_a/baseline_valores_fatura.py > baseline_antes.json
  # apos Sprint A
  python scripts/carvia/baseline_pre_sprint_a/baseline_valores_fatura.py > baseline_depois.json
  diff baseline_antes.json baseline_depois.json
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from datetime import datetime  # noqa: E402


def snapshot_valores_fatura():
    from app.carvia.models import CarviaFaturaCliente

    faturas = CarviaFaturaCliente.query.order_by(CarviaFaturaCliente.id).all()
    snapshot = []

    for f in faturas:
        snapshot.append({
            'id': f.id,
            'numero_fatura': f.numero_fatura,
            'cnpj_cliente': f.cnpj_cliente,
            'status': f.status,
            'status_conferencia': getattr(f, 'status_conferencia', None),
            'valor_total': float(f.valor_total) if f.valor_total else 0.0,
        })

    return {
        'total_faturas': len(snapshot),
        'snapshot_timestamp': datetime.now().isoformat(),
        'faturas': snapshot,
    }


def main():
    app = create_app()
    with app.app_context():
        data = snapshot_valores_fatura()

    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
