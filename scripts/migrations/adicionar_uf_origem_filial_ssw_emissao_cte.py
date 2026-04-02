#!/usr/bin/env python3
"""Migration: Adicionar uf_origem e filial_ssw a carvia_emissao_cte.

Motivo: Emissao de CTe precisa usar filial SSW conforme UF de origem.
        SP -> CAR, RJ -> GIG.

Data: 2026-04-02
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_coluna_existe(coluna):
    """Verifica se coluna ja existe na tabela."""
    result = db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'carvia_emissao_cte' AND column_name = :col
    """), {'col': coluna})
    return result.scalar() is not None


def migrar():
    app = create_app()
    with app.app_context():
        colunas = {
            'uf_origem': "ALTER TABLE carvia_emissao_cte ADD COLUMN uf_origem VARCHAR(2)",
            'filial_ssw': "ALTER TABLE carvia_emissao_cte ADD COLUMN filial_ssw VARCHAR(10)",
        }

        for col, ddl in colunas.items():
            if verificar_coluna_existe(col):
                print(f"  [OK] Coluna '{col}' ja existe — pulando")
            else:
                db.session.execute(db.text(ddl))
                print(f"  [+] Coluna '{col}' adicionada")

        # Backfill: preencher registros existentes com filial='CAR' (padrao historico)
        result = db.session.execute(db.text("""
            UPDATE carvia_emissao_cte
            SET filial_ssw = 'CAR', uf_origem = 'SP'
            WHERE filial_ssw IS NULL
        """))
        if result.rowcount > 0:
            print(f"  [~] Backfill: {result.rowcount} registros atualizados com CAR/SP")

        db.session.commit()
        print("Migration concluida com sucesso.")


if __name__ == '__main__':
    migrar()
