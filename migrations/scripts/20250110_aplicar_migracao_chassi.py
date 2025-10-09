#!/usr/bin/env python3
"""
Script para aplicar migração do campo numero_chassi
Aumenta de VARCHAR(17) para VARCHAR(30)
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def aplicar_migracao():
    """Aplica a migração do campo numero_chassi"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("MIGRAÇÃO: Aumentar campo numero_chassi de VARCHAR(17) para VARCHAR(30)")
        print("=" * 80)

        try:
            # 1. Verificar estado atual
            print("\n1. Verificando estado atual do banco...")
            result = db.session.execute(text("""
                SELECT
                    COUNT(*) as total_motos,
                    MAX(LENGTH(numero_chassi)) as maior_chassi_atual
                FROM moto
            """))
            row = result.fetchone()
            print(f"   ✓ Total de motos cadastradas: {row.total_motos}")
            print(f"   ✓ Maior chassi atual: {row.maior_chassi_atual} caracteres")

            # 2. Verificar se há chassis com mais de 17 caracteres
            result = db.session.execute(text("""
                SELECT numero_chassi, LENGTH(numero_chassi) as tamanho
                FROM moto
                WHERE LENGTH(numero_chassi) > 17
                LIMIT 5
            """))
            chassis_grandes = result.fetchall()

            if chassis_grandes:
                print(f"\n   ⚠️  ATENÇÃO: Encontrados {len(chassis_grandes)} chassis com mais de 17 caracteres!")
                print("   Exemplos:")
                for chassi, tamanho in chassis_grandes:
                    print(f"      - {chassi} ({tamanho} caracteres)")
            else:
                print("   ✓ Nenhum chassi com mais de 17 caracteres encontrado")

            # 3. Aplicar migração
            print("\n2. Aplicando migração...")
            db.session.execute(text("""
                ALTER TABLE moto
                ALTER COLUMN numero_chassi TYPE VARCHAR(30)
            """))
            db.session.commit()
            print("   ✓ Campo numero_chassi alterado para VARCHAR(30)")

            # 4. Confirmar alteração
            print("\n3. Verificando alteração...")
            result = db.session.execute(text("""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'moto'
                AND column_name = 'numero_chassi'
            """))
            col_info = result.fetchone()
            print(f"   ✓ Campo: {col_info.column_name}")
            print(f"   ✓ Tipo: {col_info.data_type}({col_info.character_maximum_length})")

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERRO ao aplicar migração: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    aplicar_migracao()
