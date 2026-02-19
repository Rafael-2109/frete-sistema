"""
Migration: Reset transfer_status stale para recebimento_lf
============================================================

Contexto:
    RecebimentoLf ID 13 (DFe=37884) ficou travado com transfer_status='processando'
    apos o worker RQ ser morto por deploy durante a fase de transferencia FB->CD.
    O job nunca executou o except handler, entao transfer_status nunca foi atualizado
    para 'erro'.

    Este script detecta e reseta TODOS os recebimentos com transfer_status stale
    (processando ha mais de 30min), nao apenas o ID 13.

Acao:
    UPDATE recebimento_lf
    SET transfer_status = 'erro',
        transfer_erro_mensagem = 'Reset automatico: transfer_status stale (processando >30min)'
    WHERE transfer_status = 'processando'
      AND atualizado_em < NOW() - INTERVAL '30 minutes'

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_transfer_status_stale.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def main():
    app = create_app()
    with app.app_context():
        # BEFORE: verificar estado atual
        print("=" * 60)
        print("BEFORE: Recebimentos com transfer_status='processando'")
        print("=" * 60)

        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT id, numero_nf, transfer_status, atualizado_em,
                       EXTRACT(EPOCH FROM (NOW() - atualizado_em)) / 60 AS minutos_stale
                FROM recebimento_lf
                WHERE transfer_status = 'processando'
                ORDER BY atualizado_em ASC
            """))
            rows = result.fetchall()

            if not rows:
                print("  Nenhum recebimento com transfer_status='processando'.")
                print("  Nada a fazer.")
                return

            stale_ids = []
            for row in rows:
                minutos = round(row.minutos_stale, 1) if row.minutos_stale else 0
                is_stale = minutos > 30
                stale_marker = " [STALE >30min]" if is_stale else ""
                print(
                    f"  ID={row.id} NF={row.numero_nf} "
                    f"atualizado_em={row.atualizado_em} "
                    f"({minutos}min atras){stale_marker}"
                )
                if is_stale:
                    stale_ids.append(row.id)

            if not stale_ids:
                print("\n  Nenhum registro stale (>30min). Nada a fazer.")
                return

            print(f"\n  {len(stale_ids)} registro(s) stale para resetar: {stale_ids}")

        # EXECUTE: resetar stale
        print("\n" + "=" * 60)
        print("EXECUTE: Resetando transfer_status stale...")
        print("=" * 60)

        with db.engine.begin() as conn:
            result = conn.execute(db.text("""
                UPDATE recebimento_lf
                SET transfer_status = 'erro',
                    transfer_erro_mensagem = 'Reset automatico: transfer_status stale (processando >30min, job morto por deploy)'
                WHERE transfer_status = 'processando'
                  AND atualizado_em < NOW() - INTERVAL '30 minutes'
            """))
            print(f"  {result.rowcount} registro(s) atualizado(s).")

        # AFTER: verificar resultado
        print("\n" + "=" * 60)
        print("AFTER: Verificando resultado")
        print("=" * 60)

        with db.engine.connect() as conn:
            result = conn.execute(db.text("""
                SELECT id, numero_nf, transfer_status, transfer_erro_mensagem, atualizado_em
                FROM recebimento_lf
                WHERE id = ANY(:ids)
            """), {'ids': stale_ids})

            for row in result.fetchall():
                print(
                    f"  ID={row.id} NF={row.numero_nf} "
                    f"transfer_status={row.transfer_status} "
                    f"msg={row.transfer_erro_mensagem[:60] if row.transfer_erro_mensagem else '-'}"
                )

        print("\nDone! Recebimentos resetados podem ser retentados via UI.")


if __name__ == '__main__':
    main()
