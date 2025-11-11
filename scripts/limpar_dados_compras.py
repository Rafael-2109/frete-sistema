"""
Script para APAGAR todos os dados das tabelas de compras
⚠️  ATENÇÃO: Este script remove TODOS os registros!
Execução local via Python
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def limpar_dados_compras():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("⚠️  LIMPEZA DE DADOS DE COMPRAS - ATENÇÃO!")
            print("=" * 80)
            print("\nEste script irá APAGAR TODOS os dados das seguintes tabelas:")
            print("  - historico_pedido_compras")
            print("  - historico_requisicao_compras")
            print("  - requisicao_compra_alocacao")
            print("  - pedido_compras")
            print("  - requisicao_compras")
            print("\n⚠️  ESTA AÇÃO É IRREVERSÍVEL!")
            print("=" * 80)

            # Solicitar confirmação
            confirmacao = input("\nDigite 'SIM' (em maiúsculas) para confirmar a exclusão: ")

            if confirmacao != 'SIM':
                print("\n❌ Operação cancelada pelo usuário.")
                return

            print("\n🚀 Iniciando limpeza de dados...")

            # ================================================
            # PASSO 1: CONTAR REGISTROS ANTES DA EXCLUSÃO
            # ================================================
            print("\n[PASSO 1] Contando registros antes da exclusão...")

            contagens = {}
            tabelas = [
                'historico_pedido_compras',
                'historico_requisicao_compras',
                'requisicao_compra_alocacao',
                'pedido_compras',
                'requisicao_compras'
            ]

            for tabela in tabelas:
                resultado = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
                count = resultado.scalar()
                contagens[tabela] = count
                print(f"   {tabela}: {count:,} registros")

            total_antes = sum(contagens.values())
            print(f"\n   TOTAL: {total_antes:,} registros")

            # ================================================
            # PASSO 2: DELETAR DADOS (ORDEM CORRETA - CASCADE)
            # ================================================
            print("\n[PASSO 2] Deletando dados (respeitando FKs)...")

            # Ordem: Primeiro históricos e alocações, depois principais

            # 1. Histórico de Pedidos (não tem FK)
            print("\n   Deletando historico_pedido_compras...")
            db.session.execute(text("DELETE FROM historico_pedido_compras"))
            print("   ✅ Deletado")

            # 2. Histórico de Requisições (não tem FK)
            print("\n   Deletando historico_requisicao_compras...")
            db.session.execute(text("DELETE FROM historico_requisicao_compras"))
            print("   ✅ Deletado")

            # 3. Alocações (FK para requisição e pedido)
            print("\n   Deletando requisicao_compra_alocacao...")
            db.session.execute(text("DELETE FROM requisicao_compra_alocacao"))
            print("   ✅ Deletado")

            # 4. Pedidos de Compras (pode ter FK em alocação - já deletada)
            print("\n   Deletando pedido_compras...")
            db.session.execute(text("DELETE FROM pedido_compras"))
            print("   ✅ Deletado")

            # 5. Requisições de Compras (pode ter FK em alocação - já deletada)
            print("\n   Deletando requisicao_compras...")
            db.session.execute(text("DELETE FROM requisicao_compras"))
            print("   ✅ Deletado")

            # Commit
            db.session.commit()

            # ================================================
            # PASSO 3: VERIFICAR EXCLUSÃO
            # ================================================
            print("\n[PASSO 3] Verificando exclusão...")

            for tabela in tabelas:
                resultado = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
                count = resultado.scalar()
                if count == 0:
                    print(f"   ✅ {tabela}: 0 registros (OK)")
                else:
                    print(f"   ❌ {tabela}: {count} registros (ERRO - ainda há dados)")

            # ================================================
            # PASSO 4: RESETAR SEQUENCES (OPCIONAL)
            # ================================================
            print("\n[PASSO 4] Resetando sequences (IDs voltam para 1)...")

            sequences = [
                ('historico_pedido_compras', 'historico_pedido_compras_id_seq'),
                ('historico_requisicao_compras', 'historico_requisicao_compras_id_seq'),
                ('requisicao_compra_alocacao', 'requisicao_compra_alocacao_id_seq'),
                ('pedido_compras', 'pedido_compras_id_seq'),
                ('requisicao_compras', 'requisicao_compras_id_seq')
            ]

            for tabela, sequence in sequences:
                try:
                    db.session.execute(text(f"ALTER SEQUENCE {sequence} RESTART WITH 1"))
                    print(f"   ✅ {sequence} resetada")
                except Exception as e:
                    print(f"   ⚠️  {sequence}: {e}")

            db.session.commit()

            print("\n" + "=" * 80)
            print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print(f"\n📊 RESUMO:")
            print(f"   Registros deletados: {total_antes:,}")
            print(f"   Tabelas limpas: {len(tabelas)}")
            print(f"   Sequences resetadas: {len(sequences)}")
            print("\n🔄 Próximo passo:")
            print("   1. Execute a migração para adicionar company_id")
            print("   2. Execute a sincronização manual das requisições")
            print("   3. Execute a sincronização manual dos pedidos")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    limpar_dados_compras()
