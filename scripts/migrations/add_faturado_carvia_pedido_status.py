"""Migration: Adicionar 'FATURADO' ao CHECK constraint de carvia_pedidos.status

Contexto (2026-04-24 — P7):
    CarviaPedido nao transicionava para FATURADO, ficando preso em EMBARCADO
    mesmo quando a NF ja estava importada em CarviaNf. A VIEW `pedidos`
    Parte 2B lia `ped.status` diretamente. Paridade com Nacom (FATURADO
    via RelatorioFaturamentoImportado) exige adicionar o status valido.

Idempotente: DROP + ADD do constraint.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    result = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_carvia_pedido_status'
    """)).scalar()
    print(f"[BEFORE] ck_carvia_pedido_status = {result}")
    return 'FATURADO' in (result or '')


def executar_migration():
    # DROP + COMMIT + ADD + COMMIT: sem o commit intermediario, o ADD
    # colide com o constraint antigo ainda "reservado" na transacao.
    db.session.execute(db.text(
        "ALTER TABLE carvia_pedidos DROP CONSTRAINT IF EXISTS ck_carvia_pedido_status"
    ))
    db.session.commit()
    db.session.execute(db.text(
        "ALTER TABLE carvia_pedidos ADD CONSTRAINT ck_carvia_pedido_status "
        "CHECK (status IN ('ABERTO','COTADO','EMBARCADO','FATURADO','CANCELADO'))"
    ))
    db.session.commit()
    print("[OK] CHECK constraint atualizado")


def verificar_depois():
    result = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_carvia_pedido_status'
    """)).scalar()
    print(f"[AFTER] ck_carvia_pedido_status = {result}")
    return 'FATURADO' in (result or '')


def main():
    app = create_app()
    with app.app_context():
        if verificar_antes():
            print("[SKIP] Ja inclui FATURADO — nada a fazer.")
            return
        executar_migration()
        if verificar_depois():
            print("[SUCCESS] Migration aplicada.")
        else:
            print("[WARN] Verificar manualmente — constraint nao detectada.")


if __name__ == '__main__':
    main()
