"""Backfill: reverte CarviaFretes ORFAOS FATURADO (FATURADO sem fatura).

CONTEXTO (causa-raiz embarque 6075): excluir/desanexar a FaturaTransportadora
soltava apenas a FK `fatura_transportadora_id` do CarviaFrete, deixando-o
status=FATURADO + valor_cte preenchido + fatura_transportadora_id=NULL. Como o
Lancamento Freteiros filtra `valor_cte IS NULL`, o frete ficava INVISIVEL (preso)
— nao reaparecia para refaturamento. O codigo das rotas ja foi corrigido
(`reverter_frete_ao_desfazer_fatura`); este script repara os fretes JA gravados
nesse estado, reusando o MESMO helper (freteiro -> PENDENTE limpa valor_cte;
demais -> CONFERIDO).

Idempotente: so toca fretes status='FATURADO' AND fatura_transportadora_id IS NULL.
Rodar de novo apos a 1a aplicacao nao acha mais nada.

Uso (rodar NO RENDER, apos o deploy do fix de codigo):
    python scripts/carvia/corrigir_fretes_orfaos_faturado.py --embarque 6075           # dry-run (default)
    python scripts/carvia/corrigir_fretes_orfaos_faturado.py --embarque 6075 --confirmar
    python scripts/carvia/corrigir_fretes_orfaos_faturado.py                           # TODOS os orfaos (dry-run)
"""
import argparse
import os
import sys

# Permite rodar como `python scripts/carvia/corrigir_fretes_orfaos_faturado.py`
# (insere a raiz do repo no sys.path — 3 niveis acima deste arquivo).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.carvia.models import CarviaFrete
from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService


def main(confirmar: bool, embarque_id: int | None) -> None:
    app = create_app()
    with app.app_context():
        q = CarviaFrete.query.filter(
            CarviaFrete.status == 'FATURADO',
            CarviaFrete.fatura_transportadora_id.is_(None),
        )
        if embarque_id is not None:
            q = q.filter(CarviaFrete.embarque_id == embarque_id)
        fretes = q.order_by(CarviaFrete.embarque_id, CarviaFrete.id).all()

        escopo = f"embarque {embarque_id}" if embarque_id is not None else "TODOS os embarques"
        print(f"Orfaos FATURADO (sem fatura) — {escopo}: {len(fretes)}\n")

        for f in fretes:
            transp = f.transportadora
            eh_freteiro = bool(transp and transp.freteiro)
            destino = 'PENDENTE (limpa valor_cte)' if eh_freteiro else 'CONFERIDO'
            print(
                f"frete {f.id} | emb {f.embarque_id} | "
                f"{transp.razao_social if transp else '?'} (freteiro={eh_freteiro}) | "
                f"valor_cte {f.valor_cte} status_conf {f.status_conferencia} "
                f"-> {destino}"
            )
            CarviaFreteService.reverter_frete_ao_desfazer_fatura(f)

        if confirmar:
            db.session.commit()
            print(f"\n✅ {len(fretes)} fretes revertidos e commitados.")
        else:
            db.session.rollback()
            print("\n(dry-run) Nada gravado. Rode com --confirmar para aplicar.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--embarque', type=int, default=None,
                        help='Limita a um embarque (ex.: 6075). Sem isso, todos os orfaos.')
    parser.add_argument('--confirmar', action='store_true',
                        help='Aplica (commit). Sem isso, dry-run.')
    args = parser.parse_args()
    main(args.confirmar, args.embarque)
