"""
Script para tornar numero_motor NULLABLE mantendo UNIQUE
Executar: python3 -m app.motochefe.scripts.tornar_motor_nullable
"""
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def tornar_motor_nullable():
    """Altera numero_motor para nullable=True mantendo unique=True"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar estado atual
            print("📝 Verificando estado atual da coluna numero_motor...")
            resultado = db.session.execute(text("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name='moto'
                AND column_name='numero_motor'
            """))

            atual = resultado.fetchone()
            if atual:
                print(f"   Estado atual: is_nullable = {atual[1]}")

                if atual[1] == 'YES':
                    print("✅ Coluna 'numero_motor' já é NULLABLE")
                    return
            else:
                print("❌ Coluna 'numero_motor' não encontrada!")
                return

            # Alterar para nullable
            print("📝 Alterando coluna para NULLABLE...")
            db.session.execute(text("""
                ALTER TABLE moto
                ALTER COLUMN numero_motor DROP NOT NULL
            """))

            db.session.commit()
            print("✅ Coluna 'numero_motor' agora é NULLABLE!")

            # Verificar constraint UNIQUE
            print("📝 Verificando constraint UNIQUE...")
            resultado = db.session.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name='moto'
                AND constraint_type='UNIQUE'
                AND constraint_name LIKE '%numero_motor%'
            """))

            constraint = resultado.fetchone()
            if constraint:
                print(f"✅ Constraint UNIQUE mantida: {constraint[0]}")
            else:
                print("⚠️  Nenhuma constraint UNIQUE encontrada para numero_motor")

            # Testar comportamento
            print("\n📊 COMPORTAMENTO ESPERADO:")
            print("   ✅ Múltiplos numero_motor=NULL são permitidos")
            print("   ✅ Valores únicos são permitidos (ex: 'MOT123')")
            print("   ❌ Valores duplicados são BLOQUEADOS")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao alterar coluna: {str(e)}")
            raise

if __name__ == '__main__':
    tornar_motor_nullable()
