"""Migration HORA 11: reconcilia status dos pedidos HORA apos bug VARCHAR(20).

Motivo: antes da migration hora_10, tentativas de gravar
'PARCIALMENTE_FATURADO' (22 char) em hora_pedido.status VARCHAR(20)
quebravam com StringDataRightTruncation e abortavam o flush. Resultado:
pedidos que deveriam estar em PARCIALMENTE_FATURADO (ou FATURADO) ficaram
com status anterior (normalmente ABERTO).

Esta migration recalcula o status de todos os pedidos que tem pelo menos
uma NF vinculada, comparando com o estado real do faturamento.

Data fix puro (sem DDL) — apenas Python, sem artefato .sql.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def _calcular_status(pedido) -> str:
    """Replica a logica de pedido_service.atualizar_status_pedido_por_faturamento
    SEM fazer commit (para poder comparar com estado atual antes de persistir).
    """
    from app.hora.models import HoraNfEntrada, HoraNfEntradaItem

    chassis_pedido = {i.numero_chassi for i in pedido.itens if i.numero_chassi}
    if not chassis_pedido:
        # Pedido sem chassis preenchidos — preserva status atual (nao temos como avaliar).
        return pedido.status

    chassis_faturados = {
        row.numero_chassi
        for row in (
            db.session.query(HoraNfEntradaItem.numero_chassi)
            .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
            .filter(HoraNfEntrada.pedido_id == pedido.id)
            .all()
        )
        if row.numero_chassi
    }

    faturados_no_pedido = chassis_pedido & chassis_faturados
    if not faturados_no_pedido:
        return 'ABERTO'
    if faturados_no_pedido == chassis_pedido:
        return 'FATURADO'
    return 'PARCIALMENTE_FATURADO'


def reconciliar(dry_run: bool = False):
    from app.hora.models import HoraPedido, HoraNfEntrada

    pedidos_com_nf_ids = {
        row[0]
        for row in (
            db.session.query(HoraNfEntrada.pedido_id)
            .filter(HoraNfEntrada.pedido_id.isnot(None))
            .distinct()
            .all()
        )
    }

    print(f"[INFO] {len(pedidos_com_nf_ids)} pedido(s) com NF vinculada para avaliar")

    divergentes = []
    for pid in pedidos_com_nf_ids:
        pedido = HoraPedido.query.get(pid)
        if not pedido:
            continue
        status_calc = _calcular_status(pedido)
        if status_calc != pedido.status:
            divergentes.append((pedido, status_calc))

    if not divergentes:
        print("[OK] Nenhum pedido com status divergente. Nada a reconciliar.")
        return 0

    print(f"[DIVERGENCIA] {len(divergentes)} pedido(s) com status incorreto:")
    for pedido, novo in divergentes:
        print(f"   - pedido_id={pedido.id} numero={pedido.numero_pedido} "
              f"atual='{pedido.status}' → novo='{novo}'")

    if dry_run:
        print("[DRY-RUN] Nada foi persistido.")
        return len(divergentes)

    from app.utils.timezone import agora_utc_naive
    for pedido, novo in divergentes:
        pedido.status = novo
        pedido.atualizado_em = agora_utc_naive()
    db.session.commit()
    print(f"[OK] {len(divergentes)} pedido(s) reconciliado(s).")
    return len(divergentes)


if __name__ == '__main__':
    app = create_app()
    dry_run = '--dry-run' in sys.argv
    with app.app_context():
        n = reconciliar(dry_run=dry_run)
        print(f"[DONE] Migration HORA 11 concluida ({n} alterado(s))")
