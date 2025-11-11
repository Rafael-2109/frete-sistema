"""
Script para verificar se company_id está sendo preenchido nas tabelas de compras
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def verificar_company_id():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("VERIFICANDO CAMPO company_id NAS TABELAS DE COMPRAS")
            print("=" * 80)

            # ================================================
            # PASSO 1: VERIFICAR SE COLUNA EXISTE
            # ================================================
            print("\n[PASSO 1] Verificando se coluna company_id existe...")

            tabelas = [
                'requisicao_compras',
                'pedido_compras',
                'requisicao_compra_alocacao',
                'historico_requisicao_compras',
                'historico_pedido_compras'
            ]

            for tabela in tabelas:
                resultado = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{tabela}' AND column_name = 'company_id'
                """))
                coluna = resultado.fetchone()

                if coluna:
                    print(f"   ✅ {tabela}: company_id EXISTS ({coluna[1]}, nullable={coluna[2]})")
                else:
                    print(f"   ❌ {tabela}: company_id NÃO EXISTE!")

            # ================================================
            # PASSO 2: CONTAR REGISTROS COM E SEM company_id
            # ================================================
            print("\n[PASSO 2] Contando registros com/sem company_id...")

            # Requisições
            print("\n   📋 REQUISIÇÕES DE COMPRAS:")
            resultado = db.session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as com_company,
                    COUNT(*) FILTER (WHERE company_id IS NULL) as sem_company,
                    COUNT(*) as total
                FROM requisicao_compras
            """))
            row = resultado.fetchone()
            print(f"      Total: {row[2]:,}")
            print(f"      Com company_id: {row[0]:,} ({row[0]*100//row[2] if row[2] > 0 else 0}%)")
            print(f"      Sem company_id (NULL): {row[1]:,} ({row[1]*100//row[2] if row[2] > 0 else 0}%)")

            # Pedidos
            print("\n   📦 PEDIDOS DE COMPRAS:")
            resultado = db.session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as com_company,
                    COUNT(*) FILTER (WHERE company_id IS NULL) as sem_company,
                    COUNT(*) as total
                FROM pedido_compras
            """))
            row = resultado.fetchone()
            print(f"      Total: {row[2]:,}")
            print(f"      Com company_id: {row[0]:,} ({row[0]*100//row[2] if row[2] > 0 else 0}%)")
            print(f"      Sem company_id (NULL): {row[1]:,} ({row[1]*100//row[2] if row[2] > 0 else 0}%)")

            # Alocações
            print("\n   🔗 ALOCAÇÕES:")
            resultado = db.session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as com_company,
                    COUNT(*) FILTER (WHERE company_id IS NULL) as sem_company,
                    COUNT(*) as total
                FROM requisicao_compra_alocacao
            """))
            row = resultado.fetchone()
            print(f"      Total: {row[2]:,}")
            print(f"      Com company_id: {row[0]:,} ({row[0]*100//row[2] if row[2] > 0 else 0}%)")
            print(f"      Sem company_id (NULL): {row[1]:,} ({row[1]*100//row[2] if row[2] > 0 else 0}%)")

            # ================================================
            # PASSO 3: MOSTRAR EXEMPLOS DE REGISTROS
            # ================================================
            print("\n[PASSO 3] Mostrando exemplos de registros...")

            # Requisições - primeiros 5 registros
            print("\n   📋 EXEMPLOS DE REQUISIÇÕES (primeiros 5):")
            resultado = db.session.execute(text("""
                SELECT
                    id,
                    num_requisicao,
                    company_id,
                    cod_produto,
                    data_requisicao_criacao
                FROM requisicao_compras
                ORDER BY id DESC
                LIMIT 5
            """))

            print("      ID | Requisição | Company ID | Produto | Data Criação")
            print("      " + "-" * 70)
            for row in resultado:
                company_display = row[2] if row[2] else "NULL"
                data_display = row[4].strftime('%d/%m/%Y') if row[4] else "NULL"
                print(f"      {row[0]:<4} | {row[1]:<15} | {company_display:<20} | {row[3]:<10} | {data_display}")

            # Pedidos - primeiros 5 registros
            print("\n   📦 EXEMPLOS DE PEDIDOS (primeiros 5):")
            resultado = db.session.execute(text("""
                SELECT
                    id,
                    num_pedido,
                    company_id,
                    cod_produto,
                    raz_social
                FROM pedido_compras
                ORDER BY id DESC
                LIMIT 5
            """))

            print("      ID | Pedido | Company ID | Produto | Fornecedor")
            print("      " + "-" * 70)
            for row in resultado:
                company_display = row[2] if row[2] else "NULL"
                fornecedor_display = (row[4][:20] + "...") if row[4] and len(row[4]) > 20 else (row[4] or "NULL")
                print(f"      {row[0]:<4} | {row[1]:<15} | {company_display:<20} | {row[3]:<10} | {fornecedor_display}")

            # ================================================
            # PASSO 4: LISTAR VALORES ÚNICOS DE company_id
            # ================================================
            print("\n[PASSO 4] Valores únicos de company_id...")

            print("\n   📋 Em REQUISIÇÕES:")
            resultado = db.session.execute(text("""
                SELECT
                    company_id,
                    COUNT(*) as total
                FROM requisicao_compras
                WHERE company_id IS NOT NULL
                GROUP BY company_id
                ORDER BY total DESC
            """))

            empresas = resultado.fetchall()
            if empresas:
                for row in empresas:
                    print(f"      - {row[0]}: {row[1]:,} requisições")
            else:
                print("      ⚠️  Nenhuma empresa encontrada (todos NULL)")

            print("\n   📦 Em PEDIDOS:")
            resultado = db.session.execute(text("""
                SELECT
                    company_id,
                    COUNT(*) as total
                FROM pedido_compras
                WHERE company_id IS NOT NULL
                GROUP BY company_id
                ORDER BY total DESC
            """))

            empresas = resultado.fetchall()
            if empresas:
                for row in empresas:
                    print(f"      - {row[0]}: {row[1]:,} pedidos")
            else:
                print("      ⚠️  Nenhuma empresa encontrada (todos NULL)")

            # ================================================
            # DIAGNÓSTICO
            # ================================================
            print("\n" + "=" * 80)
            print("📊 DIAGNÓSTICO")
            print("=" * 80)

            # Verificar se há dados
            resultado = db.session.execute(text("SELECT COUNT(*) FROM requisicao_compras"))
            total_req = resultado.scalar()

            resultado = db.session.execute(text("SELECT COUNT(*) FROM pedido_compras"))
            total_ped = resultado.scalar()

            if total_req == 0 and total_ped == 0:
                print("\n⚠️  PROBLEMA IDENTIFICADO:")
                print("   - Não há dados nas tabelas de compras")
                print("\n💡 SOLUÇÃO:")
                print("   1. Execute a sincronização manual de requisições")
                print("   2. Execute a sincronização manual de pedidos")
                print("   3. Execute este script novamente para verificar")
            else:
                resultado = db.session.execute(text("""
                    SELECT COUNT(*) FROM requisicao_compras WHERE company_id IS NULL
                """))
                req_null = resultado.scalar()

                resultado = db.session.execute(text("""
                    SELECT COUNT(*) FROM pedido_compras WHERE company_id IS NULL
                """))
                ped_null = resultado.scalar()

                if req_null > 0 or ped_null > 0:
                    print("\n⚠️  PROBLEMA IDENTIFICADO:")
                    print(f"   - {req_null:,} requisições com company_id NULL")
                    print(f"   - {ped_null:,} pedidos com company_id NULL")
                    print("\n💡 POSSÍVEIS CAUSAS:")
                    print("   1. Dados importados ANTES da atualização do serviço")
                    print("   2. Odoo não retorna company_id para alguns registros")
                    print("   3. Erro na extração do company_id do Odoo")
                    print("\n💡 SOLUÇÃO:")
                    print("   1. Limpe os dados: python3 scripts/limpar_dados_compras.py")
                    print("   2. Reimporte: Sincronização manual com janela de 90 dias")
                else:
                    print("\n✅ TUDO OK!")
                    print("   - Todos os registros possuem company_id preenchido")

            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    verificar_company_id()
