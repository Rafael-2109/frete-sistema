"""Migration: CarviaSubcontrato.operacao_id nullable.

Permite criar CarviaSubcontrato independente de CarviaOperacao.
CarviaFrete e o eixo central; operacao e subcontrato sao filhos independentes.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db

def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(db.text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos' AND column_name = 'operacao_id'
    """)).scalar()
    print(f"[BEFORE] carvia_subcontratos.operacao_id is_nullable = {result}")
    return result


def executar_migration():
    """Executa a migration."""
    db.session.execute(db.text("""
        ALTER TABLE carvia_subcontratos ALTER COLUMN operacao_id DROP NOT NULL
    """))
    db.session.commit()
    print("[OK] operacao_id alterado para nullable")


def verificar_depois():
    """Verifica estado apos a migration."""
    result = db.session.execute(db.text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos' AND column_name = 'operacao_id'
    """)).scalar()
    print(f"[AFTER] carvia_subcontratos.operacao_id is_nullable = {result}")

    # Verificar dados existentes (nenhum deve ter sido afetado)
    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_subcontratos"
    )).scalar()
    com_op = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_subcontratos WHERE operacao_id IS NOT NULL"
    )).scalar()
    print(f"[DATA] {com_op}/{total} subcontratos com operacao_id preenchido")

    assert result == 'YES', f"Esperado 'YES', obtido '{result}'"


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        antes = verificar_antes()
        if antes == 'YES':
            print("[SKIP] Ja e nullable — nada a fazer")
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
