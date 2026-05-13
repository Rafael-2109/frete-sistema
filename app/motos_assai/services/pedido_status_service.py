"""Service: recalcular_status_pedido.

Spec: §14
Plano: Task 17

Calcula automaticamente status do pedido baseado em qtd_faturada vs qtd_pedida:
- qtd_faturada == 0          -> ABERTO
- 0 < qtd_faturada < pedida  -> PARCIALMENTE_FATURADO
- qtd_faturada == pedida     -> FATURADO
- Manual                     -> CANCELADO (nao recalcula)

S10: chamar de TODOS callsites que afetam qtd_faturada.
A13: chamar defensivamente em finalizar_carregamento (nao muda nada por si, mas defensivo).
A14: nao re-calcula em pedido CANCELADO (estado terminal manual).
"""
import logging

from sqlalchemy import func
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiSeparacao, AssaiSeparacaoItem,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_FATURADA,
)


logger = logging.getLogger(__name__)


def recalcular_status_pedido(pedido_id):
    """Recalcula pedido.status baseado em chassis FATURADA vs qtd pedida.

    NAO commita — caller decide.

    Args:
        pedido_id: ID do AssaiPedidoVenda

    Returns:
        novo_status: str (status calculado, mesmo se nao mudou)
    """
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')

    if pedido.status == PEDIDO_STATUS_CANCELADO:
        # A13/A14: status manual terminal, nao recalcula
        return pedido.status

    qtd_pedida = (
        db.session.query(func.coalesce(func.sum(AssaiPedidoVendaItem.qtd_pedida), 0))
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .scalar() or 0
    )

    qtd_faturada = (
        db.session.query(func.count(AssaiSeparacaoItem.id))
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status == SEPARACAO_STATUS_FATURADA,
        )
        .scalar() or 0
    )

    if qtd_faturada == 0:
        novo_status = PEDIDO_STATUS_ABERTO
    elif qtd_faturada < qtd_pedida:
        novo_status = PEDIDO_STATUS_PARCIALMENTE_FATURADO
    elif qtd_faturada == qtd_pedida:
        novo_status = PEDIDO_STATUS_FATURADO
    else:
        # Code review fix H4 (2026-05-13): overdelivery (qtd_faturada > qtd_pedida).
        # Spec §2.2 define `qtd_faturada == qtd_pedida -> FATURADO` (igualdade
        # estrita). Acima disso e anomalia que merece visibilidade — operador
        # precisa investigar. Status FATURADO mas log warning para alerta.
        # P2 fix 11 (2026-05-13): logger no topo do modulo (era inline).
        logger.warning(
            'recalcular_status_pedido: OVERDELIVERY detectado pedido=%s '
            'qtd_faturada=%s > qtd_pedida=%s. Status definido como FATURADO '
            'mas excesso indica bug (verifique seps FATURADA do pedido).',
            pedido_id, qtd_faturada, qtd_pedida,
        )
        novo_status = PEDIDO_STATUS_FATURADO

    if pedido.status != novo_status:
        pedido.status = novo_status

    return novo_status
