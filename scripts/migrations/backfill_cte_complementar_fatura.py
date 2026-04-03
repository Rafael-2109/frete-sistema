"""
Backfill: vincular CTe complementares orfaos a fatura da operacao pai.

Cenario: CTe complementar criado APOS a fatura da operacao pai ja existir.
O CTe comp tem operacao_id mas fatura_cliente_id IS NULL, enquanto a operacao
ja esta faturada (fatura_cliente_id IS NOT NULL).

Este script:
1. Encontra CTe comps orfaos (fatura_cliente_id IS NULL) cuja operacao ja esta faturada
2. Vincula o CTe comp a mesma fatura
3. Atualiza status para FATURADO (se RASCUNHO ou EMITIDO)
4. Vincula frete_id se CarviaFrete existir para a operacao
5. Recalcula valor_total de cada fatura afetada

Idempotente: roda multiplas vezes sem efeito colateral.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run():
    from app import create_app, db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        # 1. Diagnostico BEFORE
        print("=" * 60)
        print("BEFORE — CTe Complementares orfaos")
        print("=" * 60)
        orfaos = db.session.execute(text("""
            SELECT cc.id, cc.numero_comp, cc.cte_valor, cc.status,
                   cc.operacao_id, cc.fatura_cliente_id, cc.frete_id,
                   o.fatura_cliente_id AS op_fatura_id,
                   o.status AS op_status
            FROM carvia_cte_complementares cc
            JOIN carvia_operacoes o ON o.id = cc.operacao_id
            WHERE cc.fatura_cliente_id IS NULL
              AND o.fatura_cliente_id IS NOT NULL
        """)).fetchall()

        if not orfaos:
            print("Nenhum CTe complementar orfao encontrado. Nada a fazer.")
            return

        for row in orfaos:
            print(
                f"  COMP id={row.id} ({row.numero_comp}) "
                f"valor={row.cte_valor} status={row.status} "
                f"op={row.operacao_id} op_fatura={row.op_fatura_id}"
            )

        print(f"\nTotal: {len(orfaos)} CTe(s) complementar(es) a vincular.\n")

        # 2. Vincular
        faturas_afetadas = set()
        for row in orfaos:
            fatura_id = row.op_fatura_id
            faturas_afetadas.add(fatura_id)

            # Vincular fatura_cliente_id
            db.session.execute(text("""
                UPDATE carvia_cte_complementares
                SET fatura_cliente_id = :fatura_id,
                    status = CASE
                        WHEN status IN ('RASCUNHO', 'EMITIDO') THEN 'FATURADO'
                        ELSE status
                    END
                WHERE id = :comp_id
                  AND fatura_cliente_id IS NULL
            """), {'fatura_id': fatura_id, 'comp_id': row.id})

            print(f"  Vinculado: COMP {row.id} ({row.numero_comp}) -> fatura {fatura_id}")

            # Vincular frete_id se existir
            if row.frete_id is None:
                frete = db.session.execute(text("""
                    SELECT id FROM carvia_fretes
                    WHERE operacao_id = :op_id
                    LIMIT 1
                """), {'op_id': row.operacao_id}).fetchone()

                if frete:
                    db.session.execute(text("""
                        UPDATE carvia_cte_complementares
                        SET frete_id = :frete_id
                        WHERE id = :comp_id
                    """), {'frete_id': frete.id, 'comp_id': row.id})
                    print(f"  Frete vinculado: COMP {row.id} -> frete {frete.id}")

        # 3. Recalcular valor_total de cada fatura afetada
        print(f"\nRecalculando {len(faturas_afetadas)} fatura(s)...")
        for fatura_id in faturas_afetadas:
            result = db.session.execute(text("""
                SELECT
                    fc.valor_total AS valor_antes,
                    COALESCE(
                        (SELECT SUM(cte_valor) FROM carvia_operacoes WHERE fatura_cliente_id = :fid),
                        0
                    ) AS soma_ops,
                    COALESCE(
                        (SELECT SUM(cte_valor) FROM carvia_cte_complementares WHERE fatura_cliente_id = :fid),
                        0
                    ) AS soma_comp
                FROM carvia_faturas_cliente fc
                WHERE fc.id = :fid
            """), {'fid': fatura_id}).fetchone()

            novo_total = float(result.soma_ops) + float(result.soma_comp)
            db.session.execute(text("""
                UPDATE carvia_faturas_cliente
                SET valor_total = :novo_total
                WHERE id = :fid
            """), {'novo_total': novo_total, 'fid': fatura_id})

            print(
                f"  Fatura {fatura_id}: "
                f"R$ {float(result.valor_antes):.2f} -> R$ {novo_total:.2f} "
                f"(ops={float(result.soma_ops):.2f} + comp={float(result.soma_comp):.2f})"
            )

        db.session.commit()

        # 4. Diagnostico AFTER
        print("\n" + "=" * 60)
        print("AFTER — Verificacao")
        print("=" * 60)
        verificacao = db.session.execute(text("""
            SELECT cc.id, cc.numero_comp, cc.cte_valor, cc.status,
                   cc.fatura_cliente_id, cc.frete_id,
                   fc.numero_fatura, fc.valor_total AS fatura_valor
            FROM carvia_cte_complementares cc
            LEFT JOIN carvia_faturas_cliente fc ON fc.id = cc.fatura_cliente_id
            ORDER BY cc.id
        """)).fetchall()

        for row in verificacao:
            print(
                f"  COMP {row.id} ({row.numero_comp}) "
                f"valor={row.cte_valor} status={row.status} "
                f"fatura={row.fatura_cliente_id} ({row.numero_fatura or 'N/A'}) "
                f"fatura_valor={row.fatura_valor} frete={row.frete_id}"
            )

        print("\nBackfill concluido com sucesso!")


if __name__ == '__main__':
    run()
