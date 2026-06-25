"""Corrige `valor_cotado` de fretes CarVia DIRETA com peso 0 que receberam o
frete do CAMINHAO inteiro (bug `_calcular_custo_rateio` else=1.0, fix 2026-06-24).

CONTEXTO: a condicao antiga `if peso_embarque_real > 0 and peso_grupo` caia no
`else: proporcao = 1.0` quando `peso_grupo == 0` (NF sem motos reconhecidas /
cubado 0), atribuindo o frete do caminhao inteiro a 1 item de peso zero
(ex.: E-VIBE NF 2044 embarque 6008 -> R$ 12.000). O codigo ja foi corrigido;
este script recalcula os fretes JA GRAVADOS pela MESMA logica corrigida.

Para peso 0 o rateio usa FALLBACK de 1 kg (fatia minima positiva, decisao Rafael
2026-06-25): nem 0 nem o frete inteiro. ATENCAO: frete com NF de valor relevante
+ peso 0 = motos NAO reconhecidas (cubado 0). Aqui ele vira a fatia minima de
1 kg, mas o valor REAL depende de reconhecer os modelos da NF (cubagem) —
investigar recognition separadamente nesses casos (marcados com ⚠).

So toca fretes NAO faturados (valor_cte IS NULL) e NAO cancelados. So sincroniza
`valor_considerado` quando ele == `valor_cotado` (nao mexe em ajuste manual).

Uso (rodar NO RENDER, apos o deploy do fix de codigo):
    python scripts/carvia/corrigir_rateio_peso_zero.py            # dry-run (default)
    python scripts/carvia/corrigir_rateio_peso_zero.py --confirm  # aplica
"""
import os
import sys

# Permite rodar como `python scripts/carvia/corrigir_rateio_peso_zero.py`
# (insere a raiz do repo no sys.path — 3 niveis acima deste arquivo).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.carvia.models import CarviaFrete
from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService
from app.embarques.models import Embarque


def main(confirm: bool) -> None:
    app = create_app()
    with app.app_context():
        fretes = (
            CarviaFrete.query.filter(
                CarviaFrete.peso_total == 0,
                CarviaFrete.valor_cotado > 0,
                CarviaFrete.valor_cte.is_(None),
                ~CarviaFrete.status.in_(['CANCELADO']),
            )
            .order_by(CarviaFrete.valor_cotado.desc())
            .all()
        )

        print(f"Candidatos (peso 0, valor_cotado>0, nao faturado): {len(fretes)}\n")
        alterados = 0
        for f in fretes:
            emb = db.session.get(Embarque, f.embarque_id)
            if not emb or emb.tipo_carga != 'DIRETA':
                continue
            novo = CarviaFreteService._calcular_custo_rateio(
                emb, float(f.peso_total or 0), float(f.valor_total_nfs or 0)
            ) or 0.0
            antigo = float(f.valor_cotado or 0)
            if abs(novo - antigo) < 0.01:
                continue

            flag = ''
            if float(f.valor_total_nfs or 0) > 500:
                flag = '  ⚠ NF relevante + peso 0 (motos nao reconhecidas? checar cubagem)'
            print(
                f"frete {f.id} | emb {f.embarque_id} | {f.nome_destino} | "
                f"NF {f.numeros_nfs} | NF R$ {float(f.valor_total_nfs or 0):.2f} | "
                f"valor_cotado {antigo:.2f} -> {novo:.2f}{flag}"
            )

            if confirm:
                considerado = f.valor_considerado
                if considerado is None or abs(float(considerado) - antigo) < 0.01:
                    f.valor_considerado = novo
                f.valor_cotado = novo
                alterados += 1

        if confirm:
            db.session.commit()
            print(f"\n✅ {alterados} fretes corrigidos e commitados.")
        else:
            print("\n(dry-run) Nada gravado. Rode com --confirm para aplicar.")


if __name__ == '__main__':
    main('--confirm' in sys.argv)
