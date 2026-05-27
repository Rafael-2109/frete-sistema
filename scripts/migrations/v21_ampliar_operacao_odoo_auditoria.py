"""Migration v21+ G-AUDIT-2 (2026-05-27) — ampliar VARCHAR de operacao_odoo_auditoria.

Aplica ALTER COLUMN TYPE em 3 colunas que causaram crash StringDataRightTruncation
no pipeline real v21+ ETAPA B/F5a:
  - acao: VARCHAR(20) -> VARCHAR(60)
  - status: VARCHAR(20) -> VARCHAR(30) (profilático)
  - pipeline_etapa: VARCHAR(20) -> VARCHAR(40) (profilático)

Incidente raiz:
  Skill 5 v15a usa nomes longos para auditoria:
  - 'criar_picking_inter_company'           (27 chars) — crashou
  - 'validar_picking_inter_company'         (28 chars)
  - 'criar_picking_entrada_destino_manual'  (37 chars)

Verificação BEFORE+AFTER incluida. Usar:
  python scripts/migrations/v21_ampliar_operacao_odoo_auditoria.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _print_columns(conn):
    rows = conn.execute(text("""
        SELECT column_name, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'operacao_odoo_auditoria'
          AND column_name IN ('acao', 'status', 'pipeline_etapa')
        ORDER BY column_name
    """)).fetchall()
    for r in rows:
        print(f"  {r.column_name}: VARCHAR({r.character_maximum_length})")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=== ANTES ===")
            _print_columns(conn)

            print("\n=== APLICANDO MIGRATION v21+ G-AUDIT-2 ===")
            conn.execute(text(
                "ALTER TABLE operacao_odoo_auditoria ALTER COLUMN acao TYPE VARCHAR(60)"
            ))
            print("  acao VARCHAR(20) -> VARCHAR(60) OK")
            conn.execute(text(
                "ALTER TABLE operacao_odoo_auditoria ALTER COLUMN status TYPE VARCHAR(30)"
            ))
            print("  status VARCHAR(20) -> VARCHAR(30) OK")
            conn.execute(text(
                "ALTER TABLE operacao_odoo_auditoria ALTER COLUMN pipeline_etapa TYPE VARCHAR(40)"
            ))
            print("  pipeline_etapa VARCHAR(20) -> VARCHAR(40) OK")

            print("\n=== DEPOIS ===")
            _print_columns(conn)
            print("\nMIGRATION APLICADA COM SUCESSO")


if __name__ == '__main__':
    main()
