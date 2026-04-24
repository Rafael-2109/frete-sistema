"""Migration: Remover 'EMBARCADO' do status de carvia_pedidos (P12, 2026-04-24).

EMBARCADO virou BADGE VISUAL ortogonal ao ciclo fiscal (via property
`Pedido.badge_embarcado` derivada de `data_embarque` + `ControlePortaria.hora_saida`).

Pipeline:
    1. UPDATE carvia_pedidos SET status='FATURADO' WHERE status='EMBARCADO'
       (no fluxo CarVia, EMBARCADO implica NF ativa — saida da portaria so
       dispara apos NF anexada)
    2. DROP + ADD CHECK constraint sem 'EMBARCADO'

Idempotente: pode rodar multiplas vezes. Pedidos ja FATURADO nao sao tocados.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    count_embarcado = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_pedidos WHERE status = 'EMBARCADO'"
    )).scalar()
    constraint_def = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_carvia_pedido_status'
    """)).scalar()
    print(f"[BEFORE] carvia_pedidos com status='EMBARCADO': {count_embarcado}")
    print(f"[BEFORE] constraint = {constraint_def}")
    return count_embarcado, constraint_def


def executar_migration():
    # 1. Migrar dados (EMBARCADO -> FATURADO)
    result = db.session.execute(db.text(
        "UPDATE carvia_pedidos SET status='FATURADO' "
        "WHERE status='EMBARCADO'"
    ))
    affected = result.rowcount if result.rowcount is not None else 0
    db.session.commit()
    print(f"[STEP 1] {affected} pedido(s) EMBARCADO -> FATURADO")

    # 2. DROP + ADD constraint (commit intermediario e necessario)
    db.session.execute(db.text(
        "ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status"
    ))
    db.session.commit()
    db.session.execute(db.text(
        "ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status "
        "CHECK (status IN ('ABERTO','COTADO','FATURADO','CANCELADO'))"
    ))
    db.session.commit()
    print("[STEP 2] CHECK constraint atualizado")


def verificar_depois():
    count_embarcado = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_pedidos WHERE status = 'EMBARCADO'"
    )).scalar()
    constraint_def = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_carvia_pedido_status'
    """)).scalar()
    print(f"[AFTER]  carvia_pedidos com status='EMBARCADO': {count_embarcado}")
    print(f"[AFTER]  constraint = {constraint_def}")


def main():
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("MIGRATION P12: Remover EMBARCADO de carvia_pedidos.status")
        print("=" * 70)
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("=" * 70)


if __name__ == '__main__':
    main()
