"""
Evolucao: Regras de Comissao - Hierarquia de Especificidade

Mudancas:
1. Adiciona campo 'vendedor' standalone
2. Adiciona novos tipos: CLIENTE_PRODUTO, GRUPO_PRODUTO, VENDEDOR_PRODUTO, VENDEDOR
3. Adiciona parametro COMISSAO_PADRAO (3%)

Executar: python scripts/migrations/evolucao_regra_comissao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_evolucao():
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("EVOLUCAO: Regras de Comissao - Hierarquia")
        print("=" * 60)

        try:
            # 1. Adicionar campo vendedor
            print("\n1. Verificando campo 'vendedor'...")
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'regra_comissao' AND column_name = 'vendedor'
            """))
            if result.fetchone():
                print("   Campo 'vendedor' ja existe")
            else:
                db.session.execute(text("""
                    ALTER TABLE regra_comissao
                    ADD COLUMN vendedor VARCHAR(100)
                """))
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_regra_comissao_vendedor
                    ON regra_comissao(vendedor)
                """))
                print("   Campo 'vendedor' criado com sucesso")

            # 2. Atualizar constraint de tipo_regra
            print("\n2. Atualizando constraint tipo_regra...")
            try:
                db.session.execute(text("""
                    ALTER TABLE regra_comissao DROP CONSTRAINT IF EXISTS chk_tipo_regra
                """))
            except:
                pass

            db.session.execute(text("""
                ALTER TABLE regra_comissao ADD CONSTRAINT chk_tipo_regra
                CHECK (tipo_regra IN (
                    'CLIENTE_PRODUTO',
                    'GRUPO_PRODUTO',
                    'VENDEDOR_PRODUTO',
                    'CLIENTE',
                    'GRUPO',
                    'VENDEDOR',
                    'PRODUTO'
                ))
            """))
            print("   Constraint atualizada com novos tipos")

            # 3. Adicionar parametro COMISSAO_PADRAO
            print("\n3. Verificando parametro COMISSAO_PADRAO...")
            result = db.session.execute(text("""
                SELECT valor FROM parametro_custeio WHERE chave = 'COMISSAO_PADRAO'
            """))
            if result.fetchone():
                print("   Parametro COMISSAO_PADRAO ja existe")
            else:
                db.session.execute(text("""
                    INSERT INTO parametro_custeio (chave, valor, descricao, atualizado_em, atualizado_por)
                    VALUES (
                        'COMISSAO_PADRAO',
                        3.00,
                        'Comissao padrao (%) quando nenhuma regra especifica se aplica',
                        NOW(),
                        'migracao'
                    )
                """))
                print("   Parametro COMISSAO_PADRAO criado (3%)")

            db.session.commit()

            # 4. Verificacao final
            print("\n" + "=" * 60)
            print("VERIFICACAO FINAL")
            print("=" * 60)

            # Verificar campo vendedor
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'regra_comissao' AND column_name = 'vendedor'
            """))
            print(f"Campo vendedor: {'OK' if result.fetchone() else 'ERRO'}")

            # Verificar parametro
            result = db.session.execute(text("""
                SELECT valor FROM parametro_custeio WHERE chave = 'COMISSAO_PADRAO'
            """))
            row = result.fetchone()
            print(f"COMISSAO_PADRAO: {row[0] if row else 'ERRO'}%")

            # Listar tipos validos
            print("\nTipos de regra (ordem de especificidade):")
            print("  1. CLIENTE_PRODUTO   (cliente + produto)")
            print("  2. GRUPO_PRODUTO     (grupo + produto)")
            print("  3. VENDEDOR_PRODUTO  (vendedor + produto)")
            print("  4. CLIENTE           (apenas cliente)")
            print("  5. GRUPO             (apenas grupo)")
            print("  6. VENDEDOR          (apenas vendedor)")
            print("  7. PRODUTO           (apenas produto)")
            print("  8. (padrao)          3%")

            print("\n" + "=" * 60)
            print("EVOLUCAO CONCLUIDA COM SUCESSO!")
            print("=" * 60 + "\n")

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO: {e}")
            raise


if __name__ == '__main__':
    executar_evolucao()
