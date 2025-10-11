"""
Script de migração LOCAL - Adiciona campos de impressão em PedidoVendaMoto
Campos: impresso, impresso_por, impresso_em
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campos_impressao():
    app = create_app()

    with app.app_context():
        try:
            # Verificar se campos já existem
            resultado = db.session.execute(text("""
                SELECT column_name, is_nullable, data_type
                FROM information_schema.columns
                WHERE table_name = 'pedido_venda_moto'
                AND column_name IN ('impresso', 'impresso_por', 'impresso_em')
                ORDER BY column_name;
            """))

            campos_existentes = [row[0] for row in resultado]

            print("=" * 80)
            print("VERIFICAÇÃO DE CAMPOS EXISTENTES")
            print("=" * 80)

            if campos_existentes:
                print(f"\n⚠️  Campos já existentes: {', '.join(campos_existentes)}")
                resposta = input("\nDeseja recriar os campos? (s/n): ")
                if resposta.lower() != 's':
                    print("❌ Operação cancelada")
                    return

                # Remover campos existentes
                for campo in campos_existentes:
                    print(f"\n🗑️  Removendo campo: {campo}")
                    db.session.execute(text(f"ALTER TABLE pedido_venda_moto DROP COLUMN {campo}"))

                db.session.commit()
                print("✅ Campos removidos com sucesso")
            else:
                print("\n✅ Nenhum campo existente. Prosseguindo com criação...")

            print("\n" + "=" * 80)
            print("ADICIONANDO CAMPOS DE IMPRESSÃO")
            print("=" * 80)

            # 1. Campo impresso (Boolean, default False)
            print("\n1️⃣  Adicionando campo: impresso (BOOLEAN)")
            db.session.execute(text("""
                ALTER TABLE pedido_venda_moto
                ADD COLUMN impresso BOOLEAN DEFAULT FALSE NOT NULL;
            """))
            print("   ✅ Campo 'impresso' criado com sucesso")

            # 2. Campo impresso_por (String 100)
            print("\n2️⃣  Adicionando campo: impresso_por (VARCHAR(100))")
            db.session.execute(text("""
                ALTER TABLE pedido_venda_moto
                ADD COLUMN impresso_por VARCHAR(100);
            """))
            print("   ✅ Campo 'impresso_por' criado com sucesso")

            # 3. Campo impresso_em (DateTime)
            print("\n3️⃣  Adicionando campo: impresso_em (TIMESTAMP)")
            db.session.execute(text("""
                ALTER TABLE pedido_venda_moto
                ADD COLUMN impresso_em TIMESTAMP;
            """))
            print("   ✅ Campo 'impresso_em' criado com sucesso")

            # 4. Criar índice para busca rápida
            print("\n4️⃣  Criando índice: idx_pedido_venda_impresso")
            db.session.execute(text("""
                CREATE INDEX idx_pedido_venda_impresso
                ON pedido_venda_moto(impresso);
            """))
            print("   ✅ Índice criado com sucesso")

            db.session.commit()

            print("\n" + "=" * 80)
            print("VERIFICAÇÃO FINAL")
            print("=" * 80)

            # Verificar campos criados
            resultado = db.session.execute(text("""
                SELECT column_name, is_nullable, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'pedido_venda_moto'
                AND column_name IN ('impresso', 'impresso_por', 'impresso_em')
                ORDER BY column_name;
            """))

            print("\n📋 Campos criados:")
            for row in resultado:
                print(f"   • {row[0]}: {row[2]} (Nullable: {row[1]}, Default: {row[3]})")

            # Contar registros
            count = db.session.execute(text("SELECT COUNT(*) FROM pedido_venda_moto")).scalar()
            print(f"\n📊 Total de pedidos na tabela: {count}")

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print("\n" + "=" * 80)
            print("❌ ERRO NA MIGRAÇÃO")
            print("=" * 80)
            print(f"\nDetalhes: {str(e)}")
            raise

if __name__ == '__main__':
    adicionar_campos_impressao()
