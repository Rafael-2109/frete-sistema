"""Migration: torna CarviaCustoEntrega xerox de DespesaExtra (Nacom).

Alteracoes:
1. ALTER COLUMN operacao_id DROP NOT NULL — permite criar CE sem operacao
   de venda (fluxo de compra espelho DespesaExtra)
2. ADD COLUMN transportadora_id INTEGER NULL + FK transportadoras(id)
   — override opcional de transportadora do pagamento (xerox
   DespesaExtra.transportadora_id)
3. ADD COLUMN tipo_documento VARCHAR(20) NULL (sentinel 'PENDENTE_DOCUMENTO')
4. ADD COLUMN numero_documento VARCHAR(50) NULL (sentinel 'PENDENTE_FATURA')
5. CREATE INDEX ix_carvia_custos_entrega_transportadora_id
6. BACKFILL: registros existentes recebem tipo_documento='CTE' e
   numero_documento=numero_custo para preservar semantica do fluxo venda.

Preserva fluxo VENDA (SSW 222 / CTe Complementar) — operacao_id continua
validado na camada de service, nao no modelo.

Idempotente: verifica information_schema antes de cada alteracao.
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
            # ---------- 1. ALTER operacao_id DROP NOT NULL ----------
            is_nullable = conn.execute(text("""
                SELECT is_nullable FROM information_schema.columns
                WHERE table_name = 'carvia_custos_entrega'
                  AND column_name = 'operacao_id'
            """)).scalar()

            if is_nullable == 'YES':
                print("[skip] operacao_id ja e nullable")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ALTER COLUMN operacao_id DROP NOT NULL"
                ))
                conn.commit()
                print("[ok] operacao_id agora e nullable")

            # ---------- 2. ADD COLUMN transportadora_id ----------
            col_exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_custos_entrega'
                  AND column_name = 'transportadora_id'
            """)).fetchone()

            if col_exists:
                print("[skip] Coluna transportadora_id ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ADD COLUMN transportadora_id INTEGER NULL"
                ))
                conn.commit()
                print("[ok] Coluna transportadora_id adicionada")

            # ---------- 2b. FK transportadora_id ----------
            fk_exists = conn.execute(text("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'carvia_custos_entrega'
                  AND constraint_name = 'fk_ce_transportadora'
            """)).fetchone()

            if fk_exists:
                print("[skip] FK fk_ce_transportadora ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ADD CONSTRAINT fk_ce_transportadora "
                    "FOREIGN KEY (transportadora_id) "
                    "REFERENCES transportadoras(id)"
                ))
                conn.commit()
                print("[ok] FK fk_ce_transportadora criada")

            # ---------- 2c. Index transportadora_id ----------
            idx_transp = conn.execute(text("""
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'carvia_custos_entrega'
                  AND indexname = 'ix_carvia_custos_entrega_transportadora_id'
            """)).fetchone()

            if idx_transp:
                print("[skip] Indice transportadora_id ja existe")
            else:
                conn.execute(text(
                    "CREATE INDEX ix_carvia_custos_entrega_transportadora_id "
                    "ON carvia_custos_entrega(transportadora_id)"
                ))
                conn.commit()
                print("[ok] Indice transportadora_id criado")

            # ---------- 3. ADD COLUMN tipo_documento ----------
            col_tipo_doc = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_custos_entrega'
                  AND column_name = 'tipo_documento'
            """)).fetchone()

            if col_tipo_doc:
                print("[skip] Coluna tipo_documento ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ADD COLUMN tipo_documento VARCHAR(20) NULL"
                ))
                conn.commit()
                print("[ok] Coluna tipo_documento adicionada")

            # ---------- 4. ADD COLUMN numero_documento ----------
            col_num_doc = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carvia_custos_entrega'
                  AND column_name = 'numero_documento'
            """)).fetchone()

            if col_num_doc:
                print("[skip] Coluna numero_documento ja existe")
            else:
                conn.execute(text(
                    "ALTER TABLE carvia_custos_entrega "
                    "ADD COLUMN numero_documento VARCHAR(50) NULL"
                ))
                conn.commit()
                print("[ok] Coluna numero_documento adicionada")

            # ---------- 5. BACKFILL tipo_documento/numero_documento ----------
            # Registros existentes assumem 'CTE' + numero_custo para preservar
            # semantica do fluxo venda (SSW 222 / CTe Complementar).
            before_backfill = conn.execute(text("""
                SELECT COUNT(*) FROM carvia_custos_entrega
                WHERE tipo_documento IS NULL
            """)).scalar()
            print(f"[info] CEs sem tipo_documento ANTES do backfill: {before_backfill}")

            result = conn.execute(text("""
                UPDATE carvia_custos_entrega
                   SET tipo_documento = 'CTE',
                       numero_documento = COALESCE(numero_custo, 'PENDENTE_FATURA')
                 WHERE tipo_documento IS NULL
            """))
            conn.commit()
            print(f"[ok] Backfill: {result.rowcount} CEs preenchidos com tipo_documento='CTE'")

            after_backfill = conn.execute(text("""
                SELECT COUNT(*) FROM carvia_custos_entrega
                WHERE tipo_documento IS NULL
            """)).scalar()
            print(f"[info] CEs sem tipo_documento DEPOIS do backfill: {after_backfill}")

            # ---------- 6. Resumo final ----------
            print("\n[resumo]")
            total_ces = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_custos_entrega"
            )).scalar()
            sem_operacao = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_custos_entrega WHERE operacao_id IS NULL"
            )).scalar()
            com_transportadora = conn.execute(text(
                "SELECT COUNT(*) FROM carvia_custos_entrega WHERE transportadora_id IS NOT NULL"
            )).scalar()
            print(f"  Total CEs: {total_ces}")
            print(f"  Sem operacao (fluxo compra): {sem_operacao}")
            print(f"  Com transportadora alternativa: {com_transportadora}")
            print("\nMigration concluida. Regenerar schema JSON:")
            print("  .claude/skills/consultando-sql/schemas/tables/carvia_custos_entrega.json")


if __name__ == '__main__':
    main()
