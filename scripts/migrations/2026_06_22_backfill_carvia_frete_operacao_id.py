"""Backfill: preenche CarviaFrete.operacao_id NULL via junction (reconciliacao).

Causa (auditoria 2026-06-22): a importacao do CTe CarVia cria a CarviaOperacao +
a junction carvia_operacao_nfs, mas NUNCA atualiza carvia_fretes.operacao_id.
Em producao, 110 de 114 fretes "sem operacao" ja tinham o CTe (FATURADO). Como a
UI le "tem CTe" so pela FK direta (frete.operacao_id), eles aparecem como "Sem
operacao" indevidamente.

Este backfill casa numeros_nfs -> carvia_nfs (ATIVA) -> carvia_operacao_nfs ->
CarviaOperacao (nao-cancelada) e grava operacao_id SO quando ha UMA candidata
(regra Rafael 2026-06-22: ambiguo -> PULA e lista para revisao manual, nao
adivinha). Reusa CarviaFreteService.revincular_frete_estrito (mesma logica do
hook do import) — fonte unica.

DRY-RUN por padrao (nao grava). Use --confirmar para efetivar.
  python scripts/migrations/2026_06_22_backfill_carvia_frete_operacao_id.py [--confirmar]
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.carvia.models import CarviaFrete  # noqa: E402
from app.carvia.services.documentos.carvia_frete_service import (  # noqa: E402
    CarviaFreteService,
)

logger = logging.getLogger(__name__)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        '--confirmar', action='store_true',
        help='Efetiva a gravacao (default = dry-run, nada gravado).',
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING)  # silencia o INFO de cada vinculo
    app = create_app()
    with app.app_context():
        fretes = CarviaFrete.query.filter(
            CarviaFrete.status != 'CANCELADO',
            CarviaFrete.operacao_id.is_(None),
        ).order_by(CarviaFrete.id).all()

        vinculados, ambiguos, residuais = [], [], []
        for f in fretes:
            res = CarviaFreteService.revincular_frete_estrito(f)
            if res['status'] == 'UNICA':
                op = res['operacao']
                vinculados.append((f.id, op.id, op.cte_numero, op.ctrc_numero))
            elif res['status'] == 'AMBIGUA':
                ambiguos.append((f.id, f.numeros_nfs, res['candidatas']))
            else:  # NENHUMA
                residuais.append((f.id, f.numeros_nfs))

        print(f"\n=== Backfill CarviaFrete.operacao_id ({'CONFIRMAR' if args.confirmar else 'DRY-RUN'}) ===")
        print(f"Fretes ativos com operacao_id NULL analisados: {len(fretes)}")
        print(f"  Vinculaveis (operacao UNICA):     {len(vinculados)}")
        print(f"  Ambiguos (PULADOS — revisar):     {len(ambiguos)}")
        print(f"  Residuais (sem CTe importado):    {len(residuais)}")

        if vinculados:
            print("\n-- Vinculados --")
            for fid, opid, cte, ctrc in vinculados:
                print(f"  frete {fid} -> operacao {opid} (cte={cte} ctrc={ctrc})")
        if ambiguos:
            print("\n-- AMBIGUOS (nao vinculados — revisar manualmente) --")
            for fid, nfs, cands in ambiguos:
                print(f"  frete {fid} nfs='{nfs}' -> operacoes candidatas {cands}")
        if residuais:
            print("\n-- Residuais (NF inexistente/cancelada ou CTe ainda nao importado) --")
            for fid, nfs in residuais:
                print(f"  frete {fid} nfs='{nfs}'")

        if args.confirmar:
            db.session.commit()
            print(f"\nOK — COMMIT. {len(vinculados)} fretes vinculados a operacao.")
        else:
            db.session.rollback()
            print("\nDRY-RUN — nada gravado. Rode com --confirmar para efetivar.")


if __name__ == '__main__':
    main()
