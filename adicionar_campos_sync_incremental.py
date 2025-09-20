#!/usr/bin/env python3
"""
Script para adicionar campos de sincronização incremental diretamente no banco
"""

from app import create_app, db
from sqlalchemy import text
import sys

def adicionar_campos_sync_incremental():
    """
    Adiciona campos odoo_write_date e ultima_sync na tabela carteira_principal
    """

    print("="*60)
    print("ADICIONANDO CAMPOS DE SINCRONIZAÇÃO INCREMENTAL")
    print("="*60)

    try:
        # Criar aplicação Flask
        app = create_app()

        with app.app_context():
            print("\n📊 Verificando estrutura atual da tabela...")

            # Verificar se os campos já existem
            check_sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'carteira_principal'
            AND column_name IN ('odoo_write_date', 'ultima_sync')
            """

            result = db.session.execute(text(check_sql))
            existing_columns = [row[0] for row in result]

            if 'odoo_write_date' in existing_columns and 'ultima_sync' in existing_columns:
                print("✅ Os campos já existem na tabela!")
                return True

            print("\n🔧 Adicionando novos campos...")

            # Adicionar campo odoo_write_date se não existir
            if 'odoo_write_date' not in existing_columns:
                try:
                    alter_sql_1 = """
                    ALTER TABLE carteira_principal
                    ADD COLUMN odoo_write_date TIMESTAMP NULL
                    """
                    db.session.execute(text(alter_sql_1))
                    print("   ✅ Campo 'odoo_write_date' adicionado")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print("   ℹ️ Campo 'odoo_write_date' já existe")
                    else:
                        raise

            # Adicionar campo ultima_sync se não existir
            if 'ultima_sync' not in existing_columns:
                try:
                    alter_sql_2 = """
                    ALTER TABLE carteira_principal
                    ADD COLUMN ultima_sync TIMESTAMP NULL
                    """
                    db.session.execute(text(alter_sql_2))
                    print("   ✅ Campo 'ultima_sync' adicionado")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print("   ℹ️ Campo 'ultima_sync' já existe")
                    else:
                        raise

            print("\n🔍 Criando índice para melhor performance...")

            # Criar índice para odoo_write_date
            try:
                index_sql = """
                CREATE INDEX idx_carteira_odoo_write_date
                ON carteira_principal(odoo_write_date)
                """
                db.session.execute(text(index_sql))
                print("   ✅ Índice 'idx_carteira_odoo_write_date' criado")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("   ℹ️ Índice já existe")
                else:
                    # Tentar criar com IF NOT EXISTS (PostgreSQL)
                    try:
                        index_sql_pg = """
                        CREATE INDEX IF NOT EXISTS idx_carteira_odoo_write_date
                        ON carteira_principal(odoo_write_date)
                        """
                        db.session.execute(text(index_sql_pg))
                        print("   ✅ Índice criado com IF NOT EXISTS")
                    except:
                        print("   ⚠️ Não foi possível criar o índice (pode já existir)")

            # Commit das alterações
            db.session.commit()
            print("\n💾 Alterações salvas no banco de dados")

            # Verificar resultado final
            print("\n📋 Verificando estrutura final...")

            verify_sql = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'carteira_principal'
            AND column_name IN ('odoo_write_date', 'ultima_sync')
            ORDER BY column_name
            """

            result = db.session.execute(text(verify_sql))

            print("\nCampos adicionados:")
            for row in result:
                print(f"   - {row[0]}: {row[1]} (nullable: {row[2]})")

            # Verificar índices
            index_check_sql = """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'carteira_principal'
            AND indexname = 'idx_carteira_odoo_write_date'
            """

            try:
                result = db.session.execute(text(index_check_sql))
                indices = [row[0] for row in result]
                if indices:
                    print(f"\nÍndices criados: {', '.join(indices)}")
            except:
                # Pode não ser PostgreSQL
                pass

            print("\n" + "="*60)
            print("✅ CAMPOS ADICIONADOS COM SUCESSO!")
            print("="*60)

            print("\n🎯 Próximos passos:")
            print("1. Teste a sincronização incremental com:")
            print("   from app.odoo.services.carteira_service import CarteiraService")
            print("   service = CarteiraService()")
            print("   resultado = service.sincronizar_incremental()")
            print("\n2. Configure o job para rodar a cada 30 minutos")
            print("\n3. Na primeira execução, use:")
            print("   resultado = service.sincronizar_incremental(primeira_execucao=True)")

            return True

    except Exception as e:
        print(f"\n❌ Erro ao adicionar campos: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = adicionar_campos_sync_incremental()
    sys.exit(0 if success else 1)