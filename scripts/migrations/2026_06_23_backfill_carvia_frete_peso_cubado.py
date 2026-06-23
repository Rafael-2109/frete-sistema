"""Backfill: corrige CarviaFrete.peso_total subestimado (gravou bruto, nao cubado).

Causa (IMP-2026-06-22-004, fix 2026-06-23): ate o fix, o frete gravava o peso
BRUTO quando a cotacao nao cobria o modelo da moto (Ramo 1 de
_peso_cubado_resolvido resolvia o cubado via CarviaCotacaoMoto da cotacao -> 0
-> max(bruto, 0) = bruto). A tela/export ja usavam o cubado canonico (via
CarviaNfItem.modelo_moto_id) — divergencia.

Em producao (2026-06-23): 71 fretes PENDENTE com peso_total < cubado canonico
(deficit ~21.172 kg). Este backfill recalcula peso_total = sum(max(bruto,
cubado canonico)) por NF — a MESMA formula do codigo corrigido
(MotoRecognitionService.calcular_peso_cubado_batch + max), porem em BATCH GLOBAL
(3 queries no total, em vez de N+1) para rodar rapido contra o banco remoto.

OPCAO (a), decisao Rafael 2026-06-23: corrige SOMENTE o peso_total. NAO
recalcula valor_cotado/custo (valor contratado; todos os fretes afetados estao
PENDENTE — nada conciliado a desfazer).

DRY-RUN por padrao (nao grava). Use --confirmar para efetivar.
  python scripts/migrations/2026_06_23_backfill_carvia_frete_peso_cubado.py [--confirmar]
Para apontar a producao localmente:
  DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/...py [--confirmar]
"""
import argparse
import logging
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.carvia.models import CarviaFrete, CarviaNf  # noqa: E402
from app.carvia.services.pricing.moto_recognition_service import (  # noqa: E402
    MotoRecognitionService,
)

logger = logging.getLogger(__name__)

TOLERANCIA_KG = 0.5


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        '--confirmar', action='store_true',
        help='Efetiva a gravacao (default = dry-run, nada gravado).',
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING)
    app = create_app()
    with app.app_context():
        # 1 query: fretes nao-cancelados com NFs
        fretes = CarviaFrete.query.filter(
            CarviaFrete.status != 'CANCELADO',
            CarviaFrete.numeros_nfs.isnot(None),
            CarviaFrete.numeros_nfs != '',
        ).order_by(CarviaFrete.id).all()

        fretes_nums = {}
        todos_nums = set()
        for f in fretes:
            nums = [n.strip() for n in (f.numeros_nfs or '').split(',') if n.strip()]
            fretes_nums[f.id] = nums
            todos_nums.update(nums)

        # 1 query: todas as NFs ATIVAS referenciadas (numero -> [nfs])
        nfs_por_num = defaultdict(list)
        nf_ids = []
        if todos_nums:
            for nf in CarviaNf.query.filter(
                CarviaNf.numero_nf.in_(todos_nums),
                CarviaNf.status == 'ATIVA',
            ).all():
                nfs_por_num[nf.numero_nf].append(nf)
                nf_ids.append(nf.id)

        # 1 batch: cubado canonico de todas as NFs de uma vez (mesma fonte do fix)
        cubado_por_nf = MotoRecognitionService().calcular_peso_cubado_batch(nf_ids) if nf_ids else {}

        candidatos = []  # (frete, gravado, correto)
        for f in fretes:
            nfs_do_frete = [nf for n in fretes_nums[f.id] for nf in nfs_por_num.get(n, [])]
            if not nfs_do_frete:
                continue
            correto = sum(
                max(float(nf.peso_bruto or 0), float(cubado_por_nf.get(nf.id, 0) or 0))
                for nf in nfs_do_frete
            )
            gravado = float(f.peso_total or 0)
            if correto > gravado + TOLERANCIA_KG:
                candidatos.append((f, gravado, correto))

        print('\n' + '=' * 74)
        print(f'Fretes com peso_total subestimado: {len(candidatos)}')
        if candidatos:
            difs = [c - g for _, g, c in candidatos]
            print(f'Deficit total: {sum(difs):.1f} kg | maior: {max(difs):.1f} kg')
            print('-' * 74)
            print(f'{"frete":>6} {"status":>10} {"embarque":>9} '
                  f'{"gravado":>10} {"correto":>10} {"diff_kg":>9}')
            for f, g, c in sorted(candidatos, key=lambda x: x[2] - x[1], reverse=True):
                print(f'{f.id:>6} {f.status:>10} {str(f.embarque_id or "-"):>9} '
                      f'{g:>10.1f} {c:>10.1f} {c - g:>+9.1f}')

        if not args.confirmar:
            print('\n[DRY-RUN] Nada gravado. Use --confirmar para efetivar '
                  '(corrige SOMENTE peso_total; valor_cotado/custo intactos).')
            return

        for f, _, c in candidatos:
            f.peso_total = round(c, 2)
        db.session.commit()
        print(f'\n[CONFIRMADO] peso_total corrigido em {len(candidatos)} fretes '
              f'(valor_cotado NAO alterado).')


if __name__ == '__main__':
    main()
