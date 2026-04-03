"""
Backfill: Marcar faturas cliente como PAGA quando conciliacao ja e 100%
=======================================================================

A regra R11 (conciliacao quita titulo) foi implementada no service, mas
faturas conciliadas ANTES da implementacao ficaram com status != PAGA.

Data fix (sem DDL) — atualiza status + pago_em + pago_por + conciliado.
Idempotente: so atualiza faturas com total_conciliado >= valor_total - 0.01
que NAO estejam PAGA ou CANCELADA.

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_faturas_pagas_conciliacao.py [--dry-run]
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def contar_estado():
    """Retorna contadores do estado atual."""
    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_faturas_cliente"
    )).scalar()

    pagas = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_faturas_cliente WHERE status = 'PAGA'"
    )).scalar()

    canceladas = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_faturas_cliente WHERE status = 'CANCELADA'"
    )).scalar()

    pendentes_com_conciliacao_total = db.session.execute(db.text("""
        SELECT COUNT(*) FROM carvia_faturas_cliente
        WHERE status NOT IN ('PAGA', 'CANCELADA')
          AND total_conciliado >= valor_total - 0.01
          AND valor_total > 0
    """)).scalar()

    return {
        'total': total,
        'pagas': pagas,
        'canceladas': canceladas,
        'pendentes_com_conciliacao_total': pendentes_com_conciliacao_total,
    }


def listar_afetadas():
    """Lista faturas que serao atualizadas."""
    rows = db.session.execute(db.text("""
        SELECT id, numero_fatura, status, valor_total, total_conciliado, cnpj_cliente
        FROM carvia_faturas_cliente
        WHERE status NOT IN ('PAGA', 'CANCELADA')
          AND total_conciliado >= valor_total - 0.01
          AND valor_total > 0
        ORDER BY id
    """)).fetchall()
    return rows


def executar_backfill(dry_run=False):
    """Atualiza faturas com conciliacao total para PAGA."""
    afetadas = listar_afetadas()

    if not afetadas:
        print("[OK] Nenhuma fatura para atualizar.")
        return 0

    print(f"\nFaturas a atualizar: {len(afetadas)}")
    for row in afetadas:
        print(f"  #{row.id} {row.numero_fatura} | status={row.status} | "
              f"valor={row.valor_total} | conciliado={row.total_conciliado} | "
              f"cnpj={row.cnpj_cliente}")

    if dry_run:
        print("\n[DRY-RUN] Nenhuma alteracao feita.")
        return len(afetadas)

    resultado = db.session.execute(db.text("""
        UPDATE carvia_faturas_cliente
        SET status = 'PAGA',
            pago_em = NOW(),
            pago_por = 'BACKFILL_CONCILIACAO',
            conciliado = true
        WHERE status NOT IN ('PAGA', 'CANCELADA')
          AND total_conciliado >= valor_total - 0.01
          AND valor_total > 0
    """))

    db.session.commit()
    print(f"\n[OK] {resultado.rowcount} faturas atualizadas para PAGA.")
    return resultado.rowcount


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Backfill: Faturas Cliente — Conciliacao Total → PAGA")
        print("=" * 60)

        if dry_run:
            print("[MODO] Dry-run (nenhuma alteracao sera feita)\n")

        print("=== Estado ANTES ===")
        estado_antes = contar_estado()
        for k, v in estado_antes.items():
            print(f"  {k}: {v}")

        print("\n=== Executando ===")
        atualizadas = executar_backfill(dry_run=dry_run)

        print("\n=== Estado DEPOIS ===")
        estado_depois = contar_estado()
        for k, v in estado_depois.items():
            print(f"  {k}: {v}")

        print(f"\n[DONE] Backfill concluido. {atualizadas} faturas afetadas.")
