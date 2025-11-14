"""
Script para adicionar campo tomador_e_empresa na tabela conhecimentos_transporte
e preencher valores existentes

Execução: python3 migrations/add_tomador_e_empresa_field.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.fretes.models import ConhecimentoTransporte
from sqlalchemy import text

def adicionar_campo_tomador_e_empresa():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("ADICIONANDO CAMPO tomador_e_empresa")
            print("=" * 80)

            # 1. Verificar se a coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'tomador_e_empresa';
            """))

            if resultado.fetchone():
                print("⚠️  Coluna 'tomador_e_empresa' já existe!")
                print("Pulando para atualização de valores...")
            else:
                print("📝 Criando coluna 'tomador_e_empresa'...")

                # Adicionar coluna
                db.session.execute(text("""
                    ALTER TABLE conhecimento_transporte
                    ADD COLUMN tomador_e_empresa BOOLEAN NOT NULL DEFAULT FALSE;
                """))

                # Criar índice
                db.session.execute(text("""
                    CREATE INDEX idx_cte_tomador_empresa
                    ON conhecimento_transporte(tomador_e_empresa);
                """))

                db.session.commit()
                print("✅ Coluna criada com sucesso!")

            # 2. Atualizar valores existentes
            print("\n📊 Buscando CTes para atualizar...")
            ctes = ConhecimentoTransporte.query.all()
            print(f"   Total de CTes encontrados: {len(ctes)}")

            contador_atualizados = 0
            contador_empresa = 0

            for cte in ctes:
                # Calcular se tomador é a empresa
                tomador_e_empresa = cte.calcular_tomador_e_empresa()

                if cte.tomador_e_empresa != tomador_e_empresa:
                    cte.tomador_e_empresa = tomador_e_empresa
                    contador_atualizados += 1

                    if tomador_e_empresa:
                        contador_empresa += 1

                # Commit em batch (a cada 100 registros)
                if contador_atualizados % 100 == 0:
                    db.session.commit()
                    print(f"   Processados: {contador_atualizados}")

            # Commit final
            db.session.commit()

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"   CTes atualizados: {contador_atualizados}")
            print(f"   CTes com tomador=empresa: {contador_empresa}")
            print(f"   CTes com tomador≠empresa: {len(ctes) - contador_empresa}")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    adicionar_campo_tomador_e_empresa()
