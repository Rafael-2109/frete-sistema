"""
Script para corrigir constraints em requisicao_compras
Para ambiente de DESENVOLVIMENTO local

Correção:
- Remove UNIQUE de num_requisicao
- Adiciona UNIQUE em odoo_id
- Adiciona UNIQUE composto em (num_requisicao + cod_produto)

Uso:
    python scripts/corrigir_constraint_requisicao_compras.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def mostrar_constraints_atuais():
    """Mostra constraints UNIQUE atuais"""
    try:
        resultado = db.session.execute(text("""
            SELECT
                conname as constraint_name,
                contype as constraint_type,
                pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'requisicao_compras'::regclass
            AND contype = 'u'
            ORDER BY conname;
        """))

        constraints = resultado.fetchall()

        if constraints:
            print("\n📋 Constraints UNIQUE atuais:")
            for con in constraints:
                print(f"   - {con[0]}: {con[2]}")
            return True
        else:
            print("\n⚠️  Nenhuma constraint UNIQUE encontrada")
            return False
    except Exception as e:
        print(f"\n❌ Erro ao verificar constraints: {e}")
        return False


def corrigir_constraints():
    """Corrige as constraints da tabela requisicao_compras"""
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("🔧 CORRIGINDO CONSTRAINTS - requisicao_compras")
            print("=" * 80)

            # Mostrar constraints atuais
            print("\n🔍 ESTADO ATUAL:")
            mostrar_constraints_atuais()

            print("\n⚠️  IMPORTANTE: Esta operação vai alterar as constraints da tabela!")
            print("   - Remove UNIQUE de num_requisicao")
            print("   - Adiciona UNIQUE em odoo_id")
            print("   - Adiciona UNIQUE em (num_requisicao + cod_produto)")

            resposta = input("\n   Confirma? (s/N): ").strip().lower()

            if resposta != 's':
                print("❌ Operação cancelada")
                return

            # =====================================================
            # PASSO 1: Remover índice UNIQUE de num_requisicao
            # =====================================================
            print("\n📝 PASSO 1: Removendo índice UNIQUE de num_requisicao...")

            try:
                db.session.execute(text("""
                    DROP INDEX IF EXISTS ix_requisicao_compras_num_requisicao;
                """))
                db.session.commit()
                print("   ✅ Índice UNIQUE removido de num_requisicao")
            except Exception as e:
                print(f"   ⚠️  Aviso ao remover índice: {e}")
                db.session.rollback()

            # =====================================================
            # PASSO 2: Recriar índice SEM unique (apenas index)
            # =====================================================
            print("\n📝 PASSO 2: Recriando índice simples em num_requisicao...")

            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_requisicao_num
                ON requisicao_compras(num_requisicao);
            """))
            db.session.commit()
            print("   ✅ Índice simples criado em num_requisicao")

            # =====================================================
            # PASSO 3: Adicionar UNIQUE em odoo_id (ID da linha)
            # =====================================================
            print("\n📝 PASSO 3: Adicionando UNIQUE em odoo_id...")

            # Remover constraint se existir
            try:
                db.session.execute(text("""
                    ALTER TABLE requisicao_compras
                    DROP CONSTRAINT IF EXISTS requisicao_compras_odoo_id_key;
                """))
                db.session.commit()
            except Exception as e:
                print(f"   ⚠️  Aviso: {e}")
                db.session.rollback()

            # Adicionar UNIQUE em odoo_id
            db.session.execute(text("""
                ALTER TABLE requisicao_compras
                ADD CONSTRAINT uq_requisicao_odoo_id UNIQUE (odoo_id);
            """))
            db.session.commit()
            print("   ✅ UNIQUE adicionado em odoo_id")

            # =====================================================
            # PASSO 4: Adicionar UNIQUE em (num_requisicao + cod_produto)
            # =====================================================
            print("\n📝 PASSO 4: Adicionando UNIQUE composto (num_requisicao + cod_produto)...")

            # Remover se existir
            try:
                db.session.execute(text("""
                    ALTER TABLE requisicao_compras
                    DROP CONSTRAINT IF EXISTS uq_requisicao_produto;
                """))
                db.session.commit()
            except Exception as e:
                print(f"   ⚠️  Aviso: {e}")
                db.session.rollback()

            # Adicionar constraint composta
            db.session.execute(text("""
                ALTER TABLE requisicao_compras
                ADD CONSTRAINT uq_requisicao_produto
                UNIQUE (num_requisicao, cod_produto);
            """))
            db.session.commit()
            print("   ✅ UNIQUE composto adicionado (num_requisicao + cod_produto)")

            # =====================================================
            # Verificar constraints finais
            # =====================================================
            print("\n📊 ESTADO FINAL:")
            mostrar_constraints_atuais()

            # Verificar índices
            print("\n📊 Índices criados:")
            resultado = db.session.execute(text("""
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = 'requisicao_compras'
                AND indexname LIKE '%requisicao%'
                ORDER BY indexname;
            """))

            indices = resultado.fetchall()
            for idx in indices:
                print(f"   - {idx[0]}")

            print("\n" + "=" * 80)
            print("✅ CONSTRAINTS CORRIGIDAS COM SUCESSO!")
            print("=" * 80)
            print("\n💡 Mudanças aplicadas:")
            print("   1. ✅ num_requisicao: UNIQUE removido (agora apenas INDEX)")
            print("   2. ✅ odoo_id: UNIQUE adicionado")
            print("   3. ✅ (num_requisicao + cod_produto): UNIQUE composto adicionado")
            print("\n📝 Agora uma requisição pode ter MÚLTIPLAS LINHAS de produtos!")
            print("   Exemplo:")
            print("   - REQ/FB/06611 + Produto A ✅")
            print("   - REQ/FB/06611 + Produto B ✅")
            print("   - REQ/FB/06611 + Produto C ✅")
            print()

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao corrigir constraints: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    corrigir_constraints()
