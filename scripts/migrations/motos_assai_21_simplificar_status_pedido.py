"""Migration 21: backfill status pedido — chama recalcular_status_pedido para cada pedido.

Spec: §2.2, §14.3
Plano: Task 18

Substitui os 6 status legados (ABERTO/EM_PRODUCAO/SEPARANDO/FATURADO_PARCIAL/FATURADO/CANCELADO)
pelos 4 novos (ABERTO/PARCIALMENTE_FATURADO/FATURADO/CANCELADO).

Pedidos com status CANCELADO nao sao tocados (status manual terminal).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.motos_assai.models import AssaiPedidoVenda  # noqa: E402
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        # Verificar quantos pedidos com status legado
        total = AssaiPedidoVenda.query.count()
        print(f'[start] {total} pedidos no banco')

        pedidos = AssaiPedidoVenda.query.all()
        contadores = {'mudou': 0, 'manteve': 0, 'cancelado_skip': 0}

        for pedido in pedidos:
            status_antes = pedido.status
            if pedido.status == 'CANCELADO':
                contadores['cancelado_skip'] += 1
                continue

            novo_status = recalcular_status_pedido(pedido.id)
            if novo_status != status_antes:
                contadores['mudou'] += 1
                print(f'  pedido #{pedido.id}: {status_antes} -> {novo_status}')
            else:
                contadores['manteve'] += 1

        db.session.commit()

        print(f'[done] mudou: {contadores["mudou"]}, manteve: {contadores["manteve"]}, '
              f'cancelado_skip: {contadores["cancelado_skip"]}')

        # Validacao final: nao deve haver status legado
        legados = AssaiPedidoVenda.query.filter(
            AssaiPedidoVenda.status.in_(['EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL'])
        ).count()

        if legados > 0:
            print(f'[ERROR] {legados} pedidos AINDA com status legado apos backfill')
            sys.exit(1)
        print('[ok] Migration 21 aplicada — nenhum status legado restante')


if __name__ == '__main__':
    main()
