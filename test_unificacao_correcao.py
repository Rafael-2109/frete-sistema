#!/usr/bin/env python3
"""
Teste para verificar se UnificacaoCodigos está funcionando corretamente
no saldo de estoque, carteira e produção
"""

from app import create_app, db
from app.estoque.models import UnificacaoCodigos
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.carteira.models import CarteiraPrincipal
from app.producao.models import ProgramacaoProducao
from datetime import date, timedelta
from decimal import Decimal

def testar_unificacao():
    """Testa se UnificacaoCodigos está sendo considerado em todos os cálculos"""
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔍 TESTE DE UNIFICAÇÃO DE CÓDIGOS")
        print("="*60)
        
        # 1. Verificar um produto com unificação
        print("\n📋 Buscando produtos com unificação...")
        unificacoes = UnificacaoCodigos.query.limit(5).all()
        
        if not unificacoes:
            print("⚠️  Nenhuma unificação encontrada no banco")
            return
        
        for unif in unificacoes:
            print(f"\n🔍 Testando produto: {unif.cod_produto}")
            print(f"   Código alternativo: {unif.cod_produto_alternativo}")
            
            # Obter todos os códigos relacionados
            codigos = UnificacaoCodigos.get_todos_codigos_relacionados(unif.cod_produto)
            print(f"   Códigos relacionados: {codigos}")
            
            # Testar projeção completa
            projecao = ServicoEstoqueTempoReal.get_projecao_completa(unif.cod_produto, dias=7)
            
            if projecao:
                print(f"   ✅ Estoque atual: {projecao.get('estoque_atual', 0):.2f}")
                print(f"   ✅ Menor estoque D7: {projecao.get('menor_estoque_d7', 0):.2f}")
                
                # Verificar carteira
                carteira_total = 0
                for codigo in codigos:
                    carteira = CarteiraPrincipal.query.filter_by(
                        cod_produto=codigo
                    ).all()
                    for item in carteira:
                        carteira_total += float(item.qtd_saldo_produto_pedido or 0)
                
                print(f"   📦 Total na carteira (todos os códigos): {carteira_total:.2f}")
                
                # Verificar produção
                hoje = date.today()
                producao_total = 0
                for codigo in codigos:
                    producoes = ProgramacaoProducao.query.filter(
                        ProgramacaoProducao.cod_produto == codigo,
                        ProgramacaoProducao.data_programacao >= hoje
                    ).all()
                    for prod in producoes:
                        producao_total += float(prod.qtd_programada or 0)
                
                print(f"   🏭 Total na produção (todos os códigos): {producao_total:.2f}")
                
                # Verificar se a projeção está considerando todos
                print(f"\n   📊 Projeção dos próximos 3 dias:")
                for dia in projecao.get('projecao', [])[:3]:
                    print(f"      D+{dia.get('dia')}: Entrada={dia.get('entrada', 0):.2f}, "
                          f"Saída={dia.get('saida', 0):.2f}, "
                          f"Saldo={dia.get('saldo_final', 0):.2f}")
            else:
                print(f"   ❌ Produto não encontrado no EstoqueTempoReal")
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO")
        print("="*60)


if __name__ == '__main__':
    testar_unificacao()