"""Correcao de dados: fecha o vinculo de CTes Complementares importados DEPOIS
da fatura que ja os referencia por um item (cte_complementar_id NULL).

Cenario (A1 Bug #2): a fatura SSW entra por PDF e cria o item com `cte_numero`,
mas o documento `CarviaCteComplementar` so e registrado quando o XML do CTe e
importado. Ate 2026-06-22 o auto-vinculo ficava sob a flag
`CARVIA_FEATURE_AUTO_VINCULAR_CTE_COMP` (default OFF), entao CTes importados
antes da flag ON ficaram com `fatura_cliente_id` NULL mesmo havendo a fatura.

Reusa `LinkingService.fechar_vinculo_cte_comp_fatura` (amarra o item existente,
sem duplicar; em fatura paga/conferida so prossegue se o valor_total nao muda).
Idempotente: CTe ja vinculado retorna SKIP.

Uso:
    # Varre TODOS os CTes Comp pendentes (RASCUNHO/EMITIDO, sem fatura):
    python scripts/migrations/2026_06_22_vincular_cte_comp_fatura_pre_existente.py

    # Ou processa apenas ids especificos (ex.: COMP-027 = id 28):
    python scripts/migrations/2026_06_22_vincular_cte_comp_fatura_pre_existente.py 28
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def main(argv):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        from app.carvia.models import CarviaCteComplementar
        from app.carvia.services.documentos.linking_service import LinkingService

        ids = [int(a) for a in argv if a.isdigit()]
        if ids:
            alvos = (
                CarviaCteComplementar.query
                .filter(CarviaCteComplementar.id.in_(ids))
                .all()
            )
        else:
            alvos = (
                CarviaCteComplementar.query
                .filter(
                    CarviaCteComplementar.fatura_cliente_id.is_(None),
                    CarviaCteComplementar.status.in_(['RASCUNHO', 'EMITIDO']),
                )
                .order_by(CarviaCteComplementar.id.asc())
                .all()
            )

        print(f'CTes Comp a avaliar: {len(alvos)}')
        linker = LinkingService()
        contagem = {}
        for cc in alvos:
            res = linker.fechar_vinculo_cte_comp_fatura(cc.id)
            status = res.get('status')
            contagem[status] = contagem.get(status, 0) + 1
            if status == 'VINCULADO':
                db.session.commit()
                print(
                    f'  [VINCULADO] {cc.numero_comp} (cte={cc.cte_numero}) '
                    f'-> fatura #{res.get("fatura_id")} '
                    f'(valor {res.get("valor_anterior"):.2f} -> '
                    f'{res.get("valor_novo"):.2f}, '
                    f'{res.get("items_atualizados")} item(ns))'
                )
            else:
                db.session.rollback()
                print(
                    f'  [{status}] {cc.numero_comp} (cte={cc.cte_numero}) '
                    f'— {res.get("motivo")}'
                )

        print('\nResumo:', ', '.join(f'{k}={v}' for k, v in sorted(contagem.items())) or '(nenhum)')


if __name__ == '__main__':
    main(sys.argv[1:])
