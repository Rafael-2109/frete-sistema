"""
Script para Deletar Lotes de Comissão da Importação Histórica

Problema:
- Lotes de comissão (261 registros PAI) estão aparecendo no extrato
- Valor: R$ 3.545.947,68
- MAS as comissões filhas (10.857) já existem e já foram contabilizadas
- Isso está DUPLICANDO o valor no extrato

Solução:
- Deletar os 261 lotes PAI (categoria='Lote Comissão')
- Manter as 10.857 comissões filhas (categoria='Comissão')
- Atualizar as comissões filhas para ficarem sem lote (movimentacao_origem_id = NULL)

IMPORTANTE:
- O saldo da empresa JÁ ESTÁ CORRETO (não foi afetado pelos lotes)
- Apenas o EXTRATO está mostrando valor errado

USO:
    python migrations/deletar_lotes_comissao_historico.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text
from decimal import Decimal


def main():
    app = create_app()

    with app.app_context():
        print("\n" + "=" * 120)
        print("🧹 DELETAR LOTES DE COMISSÃO DA IMPORTAÇÃO HISTÓRICA")
        print("=" * 120)

        # 1. IDENTIFICAR LOTES
        print("\n1️⃣  IDENTIFICANDO LOTES DE COMISSÃO...")
        print("=" * 120)

        lotes = db.session.execute(text("""
            SELECT
                id,
                valor,
                data_movimentacao,
                descricao
            FROM movimentacao_financeira
            WHERE categoria = 'Lote Comissão'
              AND tipo = 'PAGAMENTO'
              AND movimentacao_origem_id IS NULL
            ORDER BY id
            LIMIT 10
        """)).fetchall()

        total_lotes = db.session.execute(text("""
            SELECT COUNT(*), SUM(valor)
            FROM movimentacao_financeira
            WHERE categoria = 'Lote Comissão'
              AND tipo = 'PAGAMENTO'
              AND movimentacao_origem_id IS NULL
        """)).fetchone()

        qtd_lotes = total_lotes[0]
        valor_lotes = Decimal(str(total_lotes[1] or 0))

        print(f"\n⚠️  Encontrados {qtd_lotes} lotes de comissão")
        print(f"   Valor total: R$ {float(valor_lotes):,.2f}\n")

        if qtd_lotes == 0:
            print("✅ Nenhum lote encontrado - já foram deletados!")
            return

        print("   EXEMPLOS:")
        for row in lotes:
            print(f"   ID={row[0]} | Valor=R$ {float(row[1]):,.2f} | Data={row[2]} | {row[3][:60]}")

        # 2. VERIFICAR COMISSÕES FILHAS
        print("\n2️⃣  VERIFICANDO COMISSÕES FILHAS...")
        print("=" * 120)

        filhas = db.session.execute(text("""
            SELECT COUNT(*), SUM(valor)
            FROM movimentacao_financeira
            WHERE categoria = 'Comissão'
              AND tipo = 'PAGAMENTO'
              AND movimentacao_origem_id IS NOT NULL
        """)).fetchone()

        qtd_filhas = filhas[0]
        valor_filhas = Decimal(str(filhas[1] or 0))

        print(f"\n   Comissões filhas vinculadas aos lotes: {qtd_filhas}")
        print(f"   Valor total: R$ {float(valor_filhas):,.2f}")

        # Verificar se valor bate
        diferenca = abs(valor_lotes - valor_filhas)
        if diferenca < Decimal('1.00'):
            print(f"   ✅ Valores batem! (diferença: R$ {float(diferenca):,.2f})")
        else:
            print(f"   ⚠️  DIFERENÇA: R$ {float(diferenca):,.2f}")

        # 3. CONFIRMAR
        print("\n" + "=" * 120)
        print("📋 OPERAÇÕES QUE SERÃO REALIZADAS:")
        print("=" * 120)
        print(f"   1. Desvincular {qtd_filhas} comissões filhas dos lotes (movimentacao_origem_id = NULL)")
        print(f"   2. Deletar {qtd_lotes} lotes de comissão (categoria='Lote Comissão')")
        print(f"   3. O extrato passará a mostrar apenas as comissões individuais")
        print(f"\n   IMPACTO NO EXTRATO:")
        print(f"   - Valor ANTES (com lotes): -R$ 3.667.619,19")
        print(f"   - Valor DEPOIS (sem lotes): -R$ {float(valor_filhas + Decimal('121671.51')):,.2f}")

        print("\n⚠️  VOCÊ DESEJA PROSSEGUIR?")
        confirmacao = input("Digite 'SIM' para confirmar: ").strip().upper()

        if confirmacao != 'SIM':
            print("\n❌ Operação cancelada.")
            return

        # 4. EXECUTAR
        print("\n3️⃣  EXECUTANDO OPERAÇÕES...")
        print("=" * 120)

        try:
            # Desvincular comissões filhas
            print("\n   Desvinculando comissões filhas dos lotes...")
            db.session.execute(text("""
                UPDATE movimentacao_financeira
                SET movimentacao_origem_id = NULL
                WHERE categoria = 'Comissão'
                  AND tipo = 'PAGAMENTO'
                  AND movimentacao_origem_id IS NOT NULL
            """))

            afetados = db.session.execute(text("""
                SELECT COUNT(*)
                FROM movimentacao_financeira
                WHERE categoria = 'Comissão'
                  AND tipo = 'PAGAMENTO'
                  AND movimentacao_origem_id IS NULL
            """)).scalar()

            print(f"   ✅ {afetados} comissões desvinculadas")

            # Deletar lotes
            print("\n   Deletando lotes de comissão...")
            db.session.execute(text("""
                DELETE FROM movimentacao_financeira
                WHERE categoria = 'Lote Comissão'
                  AND tipo = 'PAGAMENTO'
                  AND movimentacao_origem_id IS NULL
            """))

            # Verificar
            restantes = db.session.execute(text("""
                SELECT COUNT(*)
                FROM movimentacao_financeira
                WHERE categoria = 'Lote Comissão'
            """)).scalar()

            print(f"   ✅ {qtd_lotes} lotes deletados (restantes: {restantes})")

            # COMMIT
            db.session.commit()

            print("\n" + "=" * 120)
            print("✅✅✅ LIMPEZA CONCLUÍDA COM SUCESSO! ✅✅✅")
            print("=" * 120)
            print(f"\n📊 RESULTADO:")
            print(f"   - Lotes deletados: {qtd_lotes}")
            print(f"   - Comissões individuais mantidas: {qtd_filhas}")
            print(f"   - Valor removido do extrato: R$ {float(valor_lotes):,.2f}")
            print(f"\n✅ Agora o extrato deve mostrar o valor correto!")
            print(f"   Atualize a página do extrato para ver a mudança.")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            print(traceback.format_exc())


if __name__ == '__main__':
    main()
