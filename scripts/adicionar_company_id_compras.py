"""
Script para adicionar campo company_id nas tabelas de compras
Execução local via Python
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_company_id():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("ADICIONANDO CAMPO company_id NAS TABELAS DE COMPRAS")
            print("=" * 80)

            # ================================================
            # PASSO 1: VERIFICAR SE COLUNAS JÁ EXISTEM
            # ================================================
            print("\n[PASSO 1] Verificando se colunas já existem...")

            tabelas = [
                'requisicao_compras',
                'pedido_compras',
                'requisicao_compra_alocacao',
                'historico_requisicao_compras',
                'historico_pedido_compras'
            ]

            colunas_existentes = {}

            for tabela in tabelas:
                resultado = db.session.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{tabela}' AND column_name = 'company_id'
                """))
                existe = resultado.fetchone() is not None
                colunas_existentes[tabela] = existe

                if existe:
                    print(f"   ✅ {tabela}: company_id JÁ EXISTE")
                else:
                    print(f"   ❌ {tabela}: company_id NÃO EXISTE")

            # ================================================
            # PASSO 2: ADICIONAR COLUNAS company_id
            # ================================================
            print("\n[PASSO 2] Adicionando colunas company_id...")

            for tabela in tabelas:
                if not colunas_existentes[tabela]:
                    print(f"   Adicionando company_id em {tabela}...")
                    db.session.execute(text(f"""
                        ALTER TABLE {tabela}
                        ADD COLUMN company_id VARCHAR(100)
                    """))
                    print(f"   ✅ Coluna adicionada em {tabela}")
                else:
                    print(f"   ⚠️  Coluna já existe em {tabela} - PULANDO")

            db.session.commit()

            # ================================================
            # PASSO 3: CRIAR ÍNDICES
            # ================================================
            print("\n[PASSO 3] Criando índices para company_id...")

            indices = [
                ('requisicao_compras', 'idx_requisicao_empresa', 'company_id, num_requisicao'),
                ('pedido_compras', 'idx_pedido_empresa', 'company_id, num_pedido'),
                ('requisicao_compra_alocacao', 'idx_alocacao_empresa', 'company_id'),
            ]

            for tabela, nome_indice, campos in indices:
                try:
                    print(f"   Criando índice {nome_indice}...")
                    db.session.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS {nome_indice}
                        ON {tabela} ({campos})
                    """))
                    print(f"   ✅ Índice {nome_indice} criado")
                except Exception as e:
                    print(f"   ⚠️  Erro ao criar índice {nome_indice}: {e}")

            db.session.commit()

            # ================================================
            # PASSO 4: REMOVER CONSTRAINT ANTIGA E CRIAR NOVA
            # ================================================
            print("\n[PASSO 4] Atualizando constraints...")

            # Requisição de Compras
            print("   Atualizando constraint em requisicao_compras...")
            try:
                # Remover constraint antiga
                db.session.execute(text("""
                    ALTER TABLE requisicao_compras
                    DROP CONSTRAINT IF EXISTS uq_requisicao_produto
                """))
                print("   ✅ Constraint antiga removida")

                # Criar nova constraint
                db.session.execute(text("""
                    ALTER TABLE requisicao_compras
                    ADD CONSTRAINT uq_requisicao_produto_empresa
                    UNIQUE (num_requisicao, cod_produto, company_id)
                """))
                print("   ✅ Nova constraint criada: uq_requisicao_produto_empresa")
            except Exception as e:
                print(f"   ⚠️  Erro: {e}")

            # Pedido de Compras
            print("\n   Atualizando constraint em pedido_compras...")
            try:
                # Remover constraint antiga
                db.session.execute(text("""
                    ALTER TABLE pedido_compras
                    DROP CONSTRAINT IF EXISTS uq_pedido_compras_num_cod_produto
                """))
                print("   ✅ Constraint antiga removida")

                # Criar nova constraint
                db.session.execute(text("""
                    ALTER TABLE pedido_compras
                    ADD CONSTRAINT uq_pedido_compras_num_cod_produto_empresa
                    UNIQUE (num_pedido, cod_produto, company_id)
                """))
                print("   ✅ Nova constraint criada: uq_pedido_compras_num_cod_produto_empresa")
            except Exception as e:
                print(f"   ⚠️  Erro: {e}")

            db.session.commit()

            # ================================================
            # PASSO 5: VERIFICAR RESULTADO
            # ================================================
            print("\n[PASSO 5] Verificando resultado...")

            for tabela in tabelas:
                resultado = db.session.execute(text(f"""
                    SELECT
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{tabela}' AND column_name = 'company_id'
                """))

                coluna = resultado.fetchone()
                if coluna:
                    print(f"   ✅ {tabela}.company_id:")
                    print(f"      Tipo: {coluna[1]}")
                    print(f"      Tamanho: {coluna[2]}")
                    print(f"      Nullable: {coluna[3]}")
                else:
                    print(f"   ❌ {tabela}.company_id NÃO ENCONTRADO!")

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n⚠️  PRÓXIMOS PASSOS:")
            print("1. Reimportar dados do Odoo com os serviços atualizados")
            print("2. Verificar se company_id está sendo preenchido corretamente")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    adicionar_company_id()
