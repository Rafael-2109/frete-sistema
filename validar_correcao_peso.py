"""
Script para validar correção de peso_total no faturamento
Compara dados atuais (com bug) vs dados que virão (corrigidos)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import text

app = create_app()

def validar_correcao():
    """Valida se a correção resolverá o problema"""
    with app.app_context():
        print("="*100)
        print(" 🔍 VALIDAÇÃO DA CORREÇÃO DE PESO")
        print("="*100)
        print()

        # Buscar uma amostra de NFs para validar (usar NFs do banco local)
        nfs_disponiveis = db.session.query(FaturamentoProduto.numero_nf).distinct().limit(3).all()
        nfs_teste = [nf[0] for nf in nfs_disponiveis] if nfs_disponiveis else []

        if not nfs_teste:
            print("❌ Nenhuma NF encontrada no banco para validar")
            return

        for nf in nfs_teste:
            print(f"\n{'─'*100}")
            print(f"📄 Analisando NF: {nf}")
            print(f"{'─'*100}")

            # Buscar produtos dessa NF
            produtos = FaturamentoProduto.query.filter_by(numero_nf=nf).all()

            if not produtos:
                print(f"⚠️  NF {nf} não encontrada no banco de dados")
                continue

            print(f"\n{'Produto':<12} {'Qtd':<8} {'Peso Unit':<12} {'Peso Total':<12} {'Peso Esperado':<15} {'Status':<10}")
            print("─"*100)

            peso_total_atual = 0
            peso_total_esperado = 0

            inconsistencias = 0

            for p in produtos:
                qtd = float(p.qtd_produto_faturado) if p.qtd_produto_faturado else 0
                peso_unit = float(p.peso_unitario_produto) if p.peso_unitario_produto else 0
                peso_total = float(p.peso_total) if p.peso_total else 0

                # Calcular peso esperado (corrigido)
                peso_esperado = qtd * peso_unit

                # Verificar consistência
                diferenca = abs(peso_total - peso_esperado)
                status = "✅ OK" if diferenca < 0.01 else "❌ ERRO"

                if diferenca >= 0.01:
                    inconsistencias += 1

                peso_total_atual += peso_total
                peso_total_esperado += peso_esperado

                print(f"{p.cod_produto:<12} {qtd:<8.1f} {peso_unit:<12.2f} {peso_total:<12.2f} {peso_esperado:<15.2f} {status:<10}")

            print("─"*100)
            print(f"\n📊 RESUMO NF {nf}:")
            print(f"   Peso Total ATUAL (com bug): {peso_total_atual:.2f} kg")
            print(f"   Peso Total ESPERADO (corrigido): {peso_total_esperado:.2f} kg")
            print(f"   Diferença: {abs(peso_total_atual - peso_total_esperado):.2f} kg")
            print(f"   Itens com inconsistência: {inconsistencias}/{len(produtos)}")

            if inconsistencias > 0:
                print(f"   ⚠️  {inconsistencias} itens precisam de correção!")
            else:
                print(f"   ✅ Todos os itens já estão corretos!")

        print("\n\n")
        print("="*100)
        print(" 📋 ORIENTAÇÕES")
        print("="*100)
        print()
        print("1. Se houver inconsistências, você precisa:")
        print("   a) Reimportar as NFs do Odoo (usando o botão 'Sincronizar Faturamento')")
        print("   b) OU rodar um script de correção no banco de dados")
        print()
        print("2. Após reimportar, rode este script novamente para validar")
        print()
        print("3. A exportação Excel agora mostrará as colunas 'Peso Unitário (kg)' e 'Peso Total (kg)'")
        print("   para facilitar a validação visual")
        print()

if __name__ == '__main__':
    try:
        validar_correcao()
    except Exception as e:
        print(f"\n❌ Erro na validação: {e}")
        import traceback
        traceback.print_exc()
