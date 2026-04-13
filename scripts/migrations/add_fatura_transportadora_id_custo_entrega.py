"""Migration: adiciona fatura_transportadora_id em carvia_custos_entrega.

Replica o padrao DespesaExtra.fatura_frete_id do modulo Nacom no CarVia.
Permite vincular CarviaCustoEntrega diretamente a CarviaFaturaTransportadora,
sem precisar intermediar por CarviaSubcontrato.

Operacoes:
1. ADD COLUMN fatura_transportadora_id INTEGER NULL
2. ADD FOREIGN KEY ON DELETE SET NULL
3. CREATE INDEX
4. BACKFILL: propaga sub.fatura_transportadora_id para CEs atualmente vinculados via subcontrato_id
5. BACKFILL de status: PENDENTE -> VINCULADO_FT para CEs que acabaram de receber FK
6. Reporta CEs orfaos (com subcontrato_id mas sem fatura_transportadora_id)

Idempotente: verifica information_schema antes de cada alteracao estrutural.
NAO remove subcontrato_id — isso sera feito em migration destructive separada.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # ---------- 1. ADD COLUMN ----------
            col_exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_custos_entrega'
                  AND column_name = 'fatura_transportadora_id'
            """)).fetchone()

            if col_exists:
                print("[skip] Coluna fatura_transportadora_id ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ADD COLUMN fatura_transportadora_id INTEGER NULL"
                ))
                conn.commit()
                print("[ok] Coluna fatura_transportadora_id adicionada")

            # ---------- 2. ADD FOREIGN KEY ----------
            fk_exists = conn.execute(text("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'carvia_custos_entrega'
                  AND constraint_name = 'fk_ce_fatura_transportadora'
            """)).fetchone()

            if fk_exists:
                print("[skip] FK fk_ce_fatura_transportadora ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ADD CONSTRAINT fk_ce_fatura_transportadora "
                    "FOREIGN KEY (fatura_transportadora_id) "
                    "REFERENCES carvia_faturas_transportadora(id) "
                    "ON DELETE SET NULL"
                ))
                conn.commit()
                print("[ok] FK fk_ce_fatura_transportadora criada")

            # ---------- 3. CREATE INDEX ----------
            idx_exists = conn.execute(text("""
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'carvia_custos_entrega'
                  AND indexname = 'ix_carvia_custos_entrega_fatura_transportadora_id'
            """)).fetchone()

            if idx_exists:
                print("[skip] Indice fatura_transportadora_id ja existe")
            else:
                conn.execute(text(
                    "CREATE INDEX ix_carvia_custos_entrega_fatura_transportadora_id "
                    "ON carvia_custos_entrega(fatura_transportadora_id)"
                ))
                conn.commit()
                print("[ok] Indice fatura_transportadora_id criado")

            # ---------- 4. BACKFILL fatura_transportadora_id via subcontrato_id ----------
            before_count = conn.execute(text("""
                SELECT COUNT(*) FROM carvia_custos_entrega
                WHERE fatura_transportadora_id IS NOT NULL
            """)).scalar()
            print(f"[info] CEs com fatura_transportadora_id ANTES do backfill: {before_count}")

            result = conn.execute(text("""
                UPDATE carvia_custos_entrega ce
                SET fatura_transportadora_id = sub.fatura_transportadora_id
                FROM carvia_subcontratos sub
                WHERE ce.subcontrato_id = sub.id
                  AND sub.fatura_transportadora_id IS NOT NULL
                  AND ce.fatura_transportadora_id IS NULL
            """))
            conn.commit()
            backfill_count = result.rowcount
            print(f"[ok] Backfill: {backfill_count} CEs receberam fatura_transportadora_id via subcontrato_id")

            after_count = conn.execute(text("""
                SELECT COUNT(*) FROM carvia_custos_entrega
                WHERE fatura_transportadora_id IS NOT NULL
            """)).scalar()
            print(f"[info] CEs com fatura_transportadora_id DEPOIS do backfill: {after_count}")

            # ---------- 5. BACKFILL status PENDENTE -> VINCULADO_FT ----------
            result_status = conn.execute(text("""
                UPDATE carvia_custos_entrega
                SET status = 'VINCULADO_FT'
                WHERE fatura_transportadora_id IS NOT NULL
                  AND status = 'PENDENTE'
            """))
            conn.commit()
            status_count = result_status.rowcount
            print(f"[ok] Backfill status: {status_count} CEs migrados de PENDENTE para VINCULADO_FT")

            # ---------- 6. Relatorio de orfaos ----------
            orfaos = conn.execute(text("""
                SELECT ce.id, ce.numero_custo, ce.subcontrato_id
                FROM carvia_custos_entrega ce
                LEFT JOIN carvia_subcontratos sub ON sub.id = ce.subcontrato_id
                WHERE ce.subcontrato_id IS NOT NULL
                  AND ce.fatura_transportadora_id IS NULL
                ORDER BY ce.id
            """)).fetchall()

            print(f"\n[relatorio] CEs com subcontrato_id mas sem fatura_transportadora_id: {len(orfaos)}")
            if orfaos:
                print("  (estes CEs tem sub sem FT vinculada — revisar manualmente)")
                for row in orfaos[:20]:
                    print(f"  - CE #{row.id} ({row.numero_custo}) -> sub #{row.subcontrato_id}")
                if len(orfaos) > 20:
                    print(f"  ... e mais {len(orfaos) - 20}")

            # ---------- 6b. Relatorio de CEs PAGO com FT nova sem pago_por='auto:' ----------
            # Estes sao CEs pagos manualmente ANTES da migracao que agora receberam
            # fatura_transportadora_id via backfill. Como pago_por nao comeca com 'auto:',
            # a propagacao _propagar_status_ces_cobertos NAO reverte esses CEs ao
            # desconciliar a FT. Estado permanente a revisar — provavelmente OK,
            # mas o usuario precisa saber.
            inconsistentes = conn.execute(text("""
                SELECT ce.id, ce.numero_custo, ce.fatura_transportadora_id, ce.pago_por
                FROM carvia_custos_entrega ce
                WHERE ce.status = 'PAGO'
                  AND ce.fatura_transportadora_id IS NOT NULL
                  AND (ce.pago_por IS NULL OR ce.pago_por NOT LIKE 'auto:%')
                ORDER BY ce.id
            """)).fetchall()

            print(f"\n[relatorio] CEs PAGO com FT vinculada (pre-migration, pagamento manual): {len(inconsistentes)}")
            if inconsistentes:
                print("  (pago_por nao comeca com 'auto:' — desconciliacao da FT NAO revertera estes CEs)")
                print("  (comportamento intencional — pagamento manual preservado)")
                for row in inconsistentes[:20]:
                    pago_por = row.pago_por or '(null)'
                    print(f"  - CE #{row.id} ({row.numero_custo}) -> FT #{row.fatura_transportadora_id} pago_por='{pago_por}'")
                if len(inconsistentes) > 20:
                    print(f"  ... e mais {len(inconsistentes) - 20}")

            # ---------- 7. Resumo final ----------
            print("\n[resumo]")
            total_ces = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_custos_entrega"
            )).scalar()
            total_com_ft = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_custos_entrega WHERE fatura_transportadora_id IS NOT NULL"
            )).scalar()
            total_vinculado_ft = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_custos_entrega WHERE status = 'VINCULADO_FT'"
            )).scalar()
            print(f"  Total CEs: {total_ces}")
            print(f"  Com fatura_transportadora_id: {total_com_ft}")
            print(f"  Status VINCULADO_FT: {total_vinculado_ft}")


if __name__ == '__main__':
    main()
