"""
Script Retroativo: Preencher metodo_baixa em titulos existentes.

Ordem de prioridade (mais especifico primeiro):
1. CNAB → contas_a_receber (via cnab_retorno_item)
2. EXCEL → contas_a_receber (via baixa_titulo_item)
3. COMPROVANTE → contas_a_pagar (via lancamento_comprovante)
4. EXTRATO → contas_a_receber (via extrato_item FK ou extrato_item_titulo M:N)
5. EXTRATO → contas_a_pagar (via extrato_item FK ou extrato_item_titulo M:N)
6. ODOO_DIRETO → catch-all para parcela_paga=True sem metodo_baixa

IMPORTANTE: Executar APOS a migration adicionar_metodo_baixa.py
Executar: source .venv/bin/activate && python scripts/migrations/preencher_metodo_baixa_retroativo.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db


def contar_estado(conn, label):
    """Mostra distribuicao atual de metodo_baixa."""
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print(f"{'=' * 60}")

    for tabela in ['contas_a_receber', 'contas_a_pagar']:
        result = conn.execute(db.text(f"""
            SELECT
                metodo_baixa,
                COUNT(*) as qtd
            FROM {tabela}
            WHERE parcela_paga = TRUE
            GROUP BY metodo_baixa
            ORDER BY metodo_baixa NULLS FIRST
        """))
        rows = result.fetchall()
        total = sum(r[1] for r in rows)
        print(f"\n  {tabela} (total pagos: {total}):")
        for row in rows:
            metodo = row[0] or '(NULL)'
            print(f"    {metodo}: {row[1]}")


def main():
    app = create_app()

    with app.app_context():
        # ── BEFORE ──
        with db.engine.connect() as conn:
            contar_estado(conn, "BEFORE: Estado antes do preenchimento")

        # ── EXECUTE ──
        print(f"\n{'=' * 60}")
        print("EXECUTE: Preenchendo metodo_baixa retroativo")
        print(f"{'=' * 60}")

        with db.engine.begin() as conn:
            # ── 1. CNAB → contas_a_receber ──
            result = conn.execute(db.text("""
                UPDATE contas_a_receber
                SET metodo_baixa = 'CNAB'
                WHERE parcela_paga = TRUE
                  AND metodo_baixa IS NULL
                  AND id IN (
                      SELECT conta_a_receber_id
                      FROM cnab_retorno_item
                      WHERE conta_a_receber_id IS NOT NULL
                        AND codigo_ocorrencia IN ('06', '10', '17')
                  )
            """))
            print(f"  1. CNAB → contas_a_receber: {result.rowcount} registros")

            # ── 2. EXCEL → contas_a_receber ──
            result = conn.execute(db.text("""
                UPDATE contas_a_receber cr
                SET metodo_baixa = 'EXCEL'
                WHERE cr.parcela_paga = TRUE
                  AND cr.metodo_baixa IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM baixa_titulo_item bti
                      WHERE bti.nf_excel = cr.titulo_nf
                        AND bti.status = 'SUCESSO'
                        AND CAST(bti.parcela_excel AS TEXT) = NULLIF(regexp_replace(cr.parcela, '[^0-9]', '', 'g'), '')
                  )
            """))
            print(f"  2. EXCEL → contas_a_receber: {result.rowcount} registros")

            # ── 3. COMPROVANTE → contas_a_pagar ──
            # Via odoo_move_line_id (mais confiavel)
            result = conn.execute(db.text("""
                UPDATE contas_a_pagar cp
                SET metodo_baixa = 'COMPROVANTE'
                WHERE cp.parcela_paga = TRUE
                  AND cp.metodo_baixa IS NULL
                  AND cp.odoo_line_id IS NOT NULL
                  AND EXISTS (
                      SELECT 1
                      FROM lancamento_comprovante lc
                      WHERE lc.odoo_move_line_id = cp.odoo_line_id
                        AND lc.status = 'LANCADO'
                  )
            """))
            print(f"  3. COMPROVANTE → contas_a_pagar (via odoo_line_id): {result.rowcount} registros")

            # Fallback: via NF+parcela
            result = conn.execute(db.text("""
                UPDATE contas_a_pagar cp
                SET metodo_baixa = 'COMPROVANTE'
                WHERE cp.parcela_paga = TRUE
                  AND cp.metodo_baixa IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM lancamento_comprovante lc
                      WHERE lc.nf_numero = cp.titulo_nf
                        AND CAST(lc.parcela AS TEXT) = NULLIF(regexp_replace(cp.parcela, '[^0-9]', '', 'g'), '')
                        AND lc.status = 'LANCADO'
                  )
            """))
            print(f"  3b. COMPROVANTE → contas_a_pagar (via NF+parcela): {result.rowcount} registros")

            # ── 4. EXTRATO → contas_a_receber ──
            # Via FK legacy
            result = conn.execute(db.text("""
                UPDATE contas_a_receber cr
                SET metodo_baixa = 'EXTRATO'
                WHERE cr.parcela_paga = TRUE
                  AND cr.metodo_baixa IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM extrato_item ei
                      WHERE ei.titulo_receber_id = cr.id
                        AND ei.status = 'CONCILIADO'
                  )
            """))
            print(f"  4a. EXTRATO → contas_a_receber (via FK legacy): {result.rowcount} registros")

            # Via M:N
            result = conn.execute(db.text("""
                UPDATE contas_a_receber cr
                SET metodo_baixa = 'EXTRATO'
                WHERE cr.parcela_paga = TRUE
                  AND cr.metodo_baixa IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM extrato_item_titulo eit
                      JOIN extrato_item ei ON ei.id = eit.extrato_item_id
                      WHERE eit.titulo_receber_id = cr.id
                        AND eit.status = 'CONCILIADO'
                  )
            """))
            print(f"  4b. EXTRATO → contas_a_receber (via M:N): {result.rowcount} registros")

            # ── 5. EXTRATO → contas_a_pagar ──
            # Via FK legacy
            result = conn.execute(db.text("""
                UPDATE contas_a_pagar cp
                SET metodo_baixa = 'EXTRATO'
                WHERE cp.parcela_paga = TRUE
                  AND cp.metodo_baixa IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM extrato_item ei
                      WHERE ei.titulo_pagar_id = cp.id
                        AND ei.status = 'CONCILIADO'
                  )
            """))
            print(f"  5a. EXTRATO → contas_a_pagar (via FK legacy): {result.rowcount} registros")

            # Via M:N
            result = conn.execute(db.text("""
                UPDATE contas_a_pagar cp
                SET metodo_baixa = 'EXTRATO'
                WHERE cp.parcela_paga = TRUE
                  AND cp.metodo_baixa IS NULL
                  AND EXISTS (
                      SELECT 1
                      FROM extrato_item_titulo eit
                      JOIN extrato_item ei ON ei.id = eit.extrato_item_id
                      WHERE eit.titulo_pagar_id = cp.id
                        AND eit.status = 'CONCILIADO'
                  )
            """))
            print(f"  5b. EXTRATO → contas_a_pagar (via M:N): {result.rowcount} registros")

            # ── 6. ODOO_DIRETO (catch-all) ──
            result = conn.execute(db.text("""
                UPDATE contas_a_receber
                SET metodo_baixa = 'ODOO_DIRETO'
                WHERE parcela_paga = TRUE
                  AND metodo_baixa IS NULL
            """))
            print(f"  6a. ODOO_DIRETO → contas_a_receber (catch-all): {result.rowcount} registros")

            result = conn.execute(db.text("""
                UPDATE contas_a_pagar
                SET metodo_baixa = 'ODOO_DIRETO'
                WHERE parcela_paga = TRUE
                  AND metodo_baixa IS NULL
            """))
            print(f"  6b. ODOO_DIRETO → contas_a_pagar (catch-all): {result.rowcount} registros")

        # ── AFTER ──
        with db.engine.connect() as conn:
            contar_estado(conn, "AFTER: Estado apos preenchimento")

            # Verificar se ainda existem NULLs em pagos
            for tabela in ['contas_a_receber', 'contas_a_pagar']:
                result = conn.execute(db.text(f"""
                    SELECT COUNT(*)
                    FROM {tabela}
                    WHERE parcela_paga = TRUE AND metodo_baixa IS NULL
                """))
                nulls = result.scalar() or 0
                if nulls > 0:
                    print(f"\n  AVISO: {tabela} ainda tem {nulls} pagos sem metodo_baixa!")
                else:
                    print(f"\n  OK: {tabela} — todos os pagos tem metodo_baixa preenchido")

        print(f"\n{'=' * 60}")
        print("Script retroativo concluido com SUCESSO!")
        print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
