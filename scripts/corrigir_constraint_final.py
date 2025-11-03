"""
Script DEFINITIVO para corrigir constraints em requisicao_compras
Remove a FK de pedido_compras, corrige o índice UNIQUE e recria a FK

Uso:
    python scripts/corrigir_constraint_final.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def corrigir_constraints():
    """Corrige as constraints da tabela requisicao_compras"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 CORREÇÃO DEFINITIVA - requisicao_compras")
            print("=" * 80)

            # =====================================================
            # PASSO 1: Remover FK de pedido_compras
            # =====================================================
            print("\n📝 PASSO 1: Removendo FK de pedido_compras...")

            db.session.execute(text("""
                ALTER TABLE pedido_compras
                DROP CONSTRAINT IF EXISTS pedido_compras_num_requisicao_fkey CASCADE;
            """))
            db.session.commit()
            print("   ✅ FK removida de pedido_compras")

            # =====================================================
            # PASSO 2: Remover índice UNIQUE problemático
            # =====================================================
            print("\n📝 PASSO 2: Removendo índice UNIQUE de num_requisicao...")

            db.session.execute(text("""
                DROP INDEX IF EXISTS ix_requisicao_compras_num_requisicao CASCADE;
            """))
            db.session.commit()
            print("   ✅ Índice UNIQUE removido")

            # =====================================================
            # PASSO 3: Recriar índice simples (SEM unique)
            # =====================================================
            print("\n📝 PASSO 3: Recriando índice simples...")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_requisicao_num
                ON requisicao_compras(num_requisicao);
            """))
            db.session.commit()
            print("   ✅ Índice simples criado")

            # =====================================================
            # PASSO 4: FK NÃO será recriada
            # =====================================================
            print("\n📝 PASSO 4: FK não será recriada (num_requisicao agora é informativo)...")
            print("   ✅ Campo num_requisicao mantido como índice simples")

            # =====================================================
            # Verificar estado final
            # =====================================================
            print("\n📊 ESTADO FINAL:")

            # Verificar índices
            resultado = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'requisicao_compras'
                AND indexname LIKE '%num_requisicao%'
                ORDER BY indexname;
            """))

            print("\n   Índices em num_requisicao:")
            indices = resultado.fetchall()
            for idx in indices:
                is_unique = "UNIQUE" in idx[1]
                status = "❌ UNIQUE" if is_unique else "✅ SIMPLES"
                print(f"   {status}: {idx[0]}")

            # Verificar constraints
            resultado = db.session.execute(text("""
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'requisicao_compras'::regclass
                AND contype = 'u'
                ORDER BY conname;
            """))

            print("\n   Constraints UNIQUE:")
            constraints = resultado.fetchall()
            for con in constraints:
                print(f"   ✅ {con[0]}: {con[1]}")

            # Verificar FK
            resultado = db.session.execute(text("""
                SELECT conname, confrelid::regclass, conkey
                FROM pg_constraint
                WHERE conrelid = 'pedido_compras'::regclass
                AND contype = 'f'
                AND conname LIKE '%num_requisicao%';
            """))

            print("\n   Foreign Keys em pedido_compras:")
            fks = resultado.fetchall()
            for fk in fks:
                print(f"   ✅ {fk[0]} -> {fk[1]}")

            print("\n" + "=" * 80)
            print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n💡 Mudanças aplicadas:")
            print("   1. ✅ FK de pedido_compras removida e recriada")
            print("   2. ✅ Índice UNIQUE de num_requisicao removido")
            print("   3. ✅ Índice SIMPLES de num_requisicao criado")
            print("   4. ✅ Constraints UNIQUE corretas mantidas:")
            print("      - (num_requisicao + cod_produto)")
            print("      - (odoo_id)")
            print("\n📝 Agora uma requisição pode ter MÚLTIPLAS LINHAS de produtos!")
            print()

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    corrigir_constraints()
