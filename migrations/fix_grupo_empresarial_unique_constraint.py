"""
Script para corrigir constraint UNIQUE indevido em grupo_empresarial.nome_grupo

PROBLEMA:
- nome_grupo está com UNIQUE mas deveria permitir duplicatas
- Um grupo pode ter vários prefixos CNPJ (1 linha por prefixo)
- Exemplo: "Atacadao" com 3 prefixos = 3 linhas com mesmo nome_grupo

SOLUÇÃO:
- Remove UNIQUE de nome_grupo
- Mantém UNIQUE em prefixo_cnpj
- Cria índice normal em nome_grupo para performance

USO:
    python migrations/fix_grupo_empresarial_unique_constraint.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def fix_grupo_empresarial_constraint():
    """Remove constraint UNIQUE de nome_grupo"""

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("FIX: Grupo Empresarial - Remover UNIQUE de nome_grupo")
        print("=" * 60)

        try:
            # 1. Verificar constraints existentes
            print("\n1. Verificando constraints existentes...")
            result = db.session.execute(text("""
                SELECT conname, contype, pg_get_constraintdef(oid) as definicao
                FROM pg_constraint
                WHERE conrelid = 'grupo_empresarial'::regclass
            """))

            constraints = result.fetchall()
            print(f"   Encontrados {len(constraints)} constraints:")
            for c in constraints:
                print(f"   - {c[0]} ({c[1]}): {c[2]}")

            # 2. Verificar índices existentes
            print("\n2. Verificando índices existentes...")
            result = db.session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'grupo_empresarial'
            """))

            indexes = result.fetchall()
            print(f"   Encontrados {len(indexes)} índices:")
            for idx in indexes:
                print(f"   - {idx[0]}")
                print(f"     {idx[1]}")

            # 3. Remover constraint UNIQUE de nome_grupo
            print("\n3. Removendo UNIQUE de nome_grupo...")

            # Tentar vários nomes possíveis de constraint
            constraint_names = [
                'ix_grupo_empresarial_nome_grupo',
                'grupo_empresarial_nome_grupo_key',
                'uq_grupo_empresarial_nome_grupo'
            ]

            removed = False
            for constraint_name in constraint_names:
                try:
                    db.session.execute(text(f"""
                        ALTER TABLE grupo_empresarial
                        DROP CONSTRAINT IF EXISTS {constraint_name}
                    """))
                    print(f"   ✓ Tentou remover constraint: {constraint_name}")
                    removed = True
                except Exception as e:
                    print(f"   - {constraint_name} não existe ou erro: {str(e)[:50]}")

            # Tentar dropar índice UNIQUE
            try:
                db.session.execute(text("""
                    DROP INDEX IF EXISTS ix_grupo_empresarial_nome_grupo
                """))
                print(f"   ✓ Removido índice: ix_grupo_empresarial_nome_grupo")
                removed = True
            except Exception as e:
                print(f"   - Índice não existe: {str(e)[:50]}")

            # 4. Recriar índice NORMAL (sem UNIQUE)
            print("\n4. Criando índice NORMAL em nome_grupo...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_grupo_empresarial_nome
                ON grupo_empresarial(nome_grupo)
            """))
            print("   ✓ Índice idx_grupo_empresarial_nome criado")

            # 5. Garantir UNIQUE em prefixo_cnpj
            print("\n5. Garantindo UNIQUE em prefixo_cnpj...")
            db.session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uk_prefixo_cnpj'
                        AND conrelid = 'grupo_empresarial'::regclass
                    ) THEN
                        ALTER TABLE grupo_empresarial
                        ADD CONSTRAINT uk_prefixo_cnpj UNIQUE (prefixo_cnpj);
                    END IF;
                END$$;
            """))
            print("   ✓ Constraint uk_prefixo_cnpj garantida")

            # Commit
            db.session.commit()

            # 6. Verificar resultado final
            print("\n6. Verificando resultado final...")
            result = db.session.execute(text("""
                SELECT conname, pg_get_constraintdef(oid) as definicao
                FROM pg_constraint
                WHERE conrelid = 'grupo_empresarial'::regclass
                ORDER BY conname
            """))

            print("\n   CONSTRAINTS ATUAIS:")
            for c in result.fetchall():
                print(f"   - {c[0]}: {c[1]}")

            result = db.session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'grupo_empresarial'
                ORDER BY indexname
            """))

            print("\n   ÍNDICES ATUAIS:")
            for idx in result.fetchall():
                print(f"   - {idx[0]}")

            print("\n" + "=" * 60)
            print("✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            print("\nAgora você pode cadastrar grupos com mesmo nome e prefixos diferentes.")
            print("Exemplo: 'Atacadao' com prefixos 93209765, 73315333, 00063960")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    return True

if __name__ == '__main__':
    print("\nEste script vai corrigir o problema de UNIQUE em nome_grupo.")
    print("Tem certeza que deseja continuar? (s/n): ", end='')

    resposta = input().lower()
    if resposta == 's':
        fix_grupo_empresarial_constraint()
    else:
        print("Operação cancelada.")
