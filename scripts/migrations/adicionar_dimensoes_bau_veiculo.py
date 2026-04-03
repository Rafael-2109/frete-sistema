"""
Migration: Adicionar campos de dimensao do bau ao modelo Veiculo.

Campos: comprimento_bau, largura_bau, altura_bau (Float, nullable).
Usados pelo simulador 3D de carga de motos para calcular
quantas motos cabem em cada tipo de veiculo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/adicionar_dimensoes_bau_veiculo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


def verificar_coluna_existe(coluna):
    """Verifica se coluna existe na tabela veiculos."""
    result = db.session.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'veiculos' AND column_name = :col
    """), {'col': coluna})
    return result.fetchone() is not None


def main():
    app = create_app()
    with app.app_context():
        colunas = [
            ('comprimento_bau', 'FLOAT'),
            ('largura_bau', 'FLOAT'),
            ('altura_bau', 'FLOAT'),
        ]

        # Before: verificar estado atual
        print("=== BEFORE ===")
        for col, _ in colunas:
            existe = verificar_coluna_existe(col)
            print(f"  {col}: {'JA EXISTE' if existe else 'NAO EXISTE'}")

        # Aplicar migration
        print("\n=== APLICANDO MIGRATION ===")
        for col, tipo in colunas:
            if not verificar_coluna_existe(col):
                db.session.execute(text(
                    f"ALTER TABLE veiculos ADD COLUMN {col} {tipo}"
                ))
                print(f"  + Coluna '{col}' adicionada")
            else:
                print(f"  = Coluna '{col}' ja existe, pulando")

        # Adicionar comentarios
        db.session.execute(text(
            "COMMENT ON COLUMN veiculos.comprimento_bau IS "
            "'Comprimento interno do bau em centimetros'"
        ))
        db.session.execute(text(
            "COMMENT ON COLUMN veiculos.largura_bau IS "
            "'Largura interna do bau em centimetros'"
        ))
        db.session.execute(text(
            "COMMENT ON COLUMN veiculos.altura_bau IS "
            "'Altura interna do bau em centimetros'"
        ))

        db.session.commit()

        # After: verificar resultado
        print("\n=== AFTER ===")
        for col, _ in colunas:
            existe = verificar_coluna_existe(col)
            print(f"  {col}: {'OK' if existe else 'FALHA!'}")

        # Mostrar contagem de veiculos
        result = db.session.execute(text("SELECT COUNT(*) FROM veiculos"))
        total = result.scalar()
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM veiculos "
            "WHERE comprimento_bau IS NOT NULL "
            "AND largura_bau IS NOT NULL "
            "AND altura_bau IS NOT NULL"
        ))
        com_dims = result.scalar()
        print(f"\n  Veiculos totais: {total}")
        print(f"  Com dimensoes do bau: {com_dims}")
        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    main()
