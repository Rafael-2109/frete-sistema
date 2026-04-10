"""
Migration: Expandir precisão de quantidade_convertida para 4 casas decimais.

Motivo: divisões como 1/6 = 0.1667 precisam de 4 casas para manter integridade
        no roundtrip (0.167 * 6 = 1.002, mas 0.1667 * 6 = 1.0002).

Tabela: nf_devolucao_linha
Coluna: quantidade_convertida NUMERIC(15,3) → NUMERIC(15,4)

Uso:
    python scripts/migrations/expand_quantidade_convertida_precision.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.extensions import db


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(db.text("""
        SELECT numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_name = 'nf_devolucao_linha'
          AND column_name = 'quantidade_convertida'
    """)).fetchone()

    if not result:
        print("[ERRO] Coluna quantidade_convertida não encontrada em nf_devolucao_linha")
        return False

    precision, scale = result
    print(f"[ANTES] quantidade_convertida: NUMERIC({precision},{scale})")

    if scale >= 4:
        print("[INFO] Coluna já possui precisão >= 4. Nada a fazer.")
        return False

    return True


def executar_migration():
    """Executa o ALTER COLUMN."""
    db.session.execute(db.text("""
        ALTER TABLE nf_devolucao_linha
        ALTER COLUMN quantidade_convertida TYPE NUMERIC(15, 4)
    """))
    db.session.commit()
    print("[OK] ALTER COLUMN executado com sucesso.")


def verificar_depois():
    """Verifica estado após a migration."""
    result = db.session.execute(db.text("""
        SELECT numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_name = 'nf_devolucao_linha'
          AND column_name = 'quantidade_convertida'
    """)).fetchone()

    precision, scale = result
    print(f"[DEPOIS] quantidade_convertida: NUMERIC({precision},{scale})")

    if scale == 4:
        print("[SUCESSO] Migration concluída.")
    else:
        print(f"[ERRO] Escala esperada: 4, encontrada: {scale}")


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Migration: expand_quantidade_convertida_precision")
        print("=" * 60)

        if not verificar_antes():
            return

        executar_migration()
        verificar_depois()


if __name__ == '__main__':
    main()
