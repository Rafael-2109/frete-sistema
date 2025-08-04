#!/usr/bin/env python
"""
Script de teste para verificar importação TagPlus com múltiplos itens
"""

from app import create_app, db
from app.faturamento.models import FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from app.carteira.models import CarteiraCopia
from sqlalchemy import func

def verificar_importacao_tagplus():
    """Verifica se a importação TagPlus está processando todos os itens"""
    
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("VERIFICAÇÃO DA IMPORTAÇÃO TAGPLUS")
        print("=" * 80)
        
        # 1. Buscar NFs TagPlus com múltiplos itens
        print("\n1. BUSCANDO NFs COM MÚLTIPLOS ITENS...")
        
        nfs_multiplos_itens = db.session.query(
            FaturamentoProduto.numero_nf,
            func.count(FaturamentoProduto.cod_produto).label('qtd_itens')
        ).filter(
            FaturamentoProduto.created_by == 'ImportTagPlus'
        ).group_by(
            FaturamentoProduto.numero_nf
        ).having(
            func.count(FaturamentoProduto.cod_produto) > 1
        ).limit(5).all()
        
        if not nfs_multiplos_itens:
            print("   ❌ Nenhuma NF com múltiplos itens encontrada")
            return
        
        print(f"   ✅ Encontradas {len(nfs_multiplos_itens)} NFs com múltiplos itens")
        
        # 2. Verificar cada NF
        for nf_numero, qtd_itens in nfs_multiplos_itens:
            print(f"\n2. ANALISANDO NF {nf_numero} ({qtd_itens} itens):")
            
            # Buscar todos os itens da NF
            itens_nf = FaturamentoProduto.query.filter_by(
                numero_nf=nf_numero
            ).all()
            
            print(f"   📦 Itens na NF:")
            for item in itens_nf:
                print(f"      - {item.cod_produto}: {item.nome_produto[:30]}... Qtd: {item.qtd_produto_faturado}")
            
            # 3. Verificar movimentações de estoque
            print(f"\n   🏭 MOVIMENTAÇÕES DE ESTOQUE:")
            movimentacoes = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.observacao.contains(f"NF {nf_numero}")
            ).all()
            
            if len(movimentacoes) == 0:
                print(f"      ❌ NENHUMA movimentação encontrada!")
            elif len(movimentacoes) < qtd_itens:
                print(f"      ⚠️  PROBLEMA: Apenas {len(movimentacoes)} movimentação(ões) para {qtd_itens} itens!")
                for mov in movimentacoes:
                    print(f"         - {mov.cod_produto}: {mov.qtd_movimentacao}")
            else:
                print(f"      ✅ {len(movimentacoes)} movimentações encontradas")
                for mov in movimentacoes:
                    print(f"         - {mov.cod_produto}: {mov.qtd_movimentacao}")
            
            # 4. Verificar baixas na CarteiraCopia
            print(f"\n   💰 BAIXAS NA CARTEIRA:")
            for item in itens_nf:
                if item.origem:
                    carteira = CarteiraCopia.query.filter_by(
                        num_pedido=item.origem,
                        cod_produto=item.cod_produto
                    ).first()
                    
                    if carteira:
                        # Calcular baixa dinamicamente
                        baixa_calculada = carteira.baixa_produto_pedido
                        print(f"      - Pedido {item.origem} / Produto {item.cod_produto}:")
                        print(f"        Baixa calculada: {baixa_calculada}")
                        print(f"        Qtd faturada: {item.qtd_produto_faturado}")
                    else:
                        print(f"      - Pedido {item.origem} / Produto {item.cod_produto}: CarteiraCopia não encontrada")
                else:
                    print(f"      - Produto {item.cod_produto}: Sem origem (num_pedido)")
            
            print("-" * 80)
        
        # 5. Estatísticas gerais
        print("\n📊 ESTATÍSTICAS GERAIS:")
        
        total_nfs = db.session.query(
            func.count(func.distinct(FaturamentoProduto.numero_nf))
        ).filter(
            FaturamentoProduto.created_by == 'ImportTagPlus'
        ).scalar()
        
        total_itens = FaturamentoProduto.query.filter(
            FaturamentoProduto.created_by == 'ImportTagPlus'
        ).count()
        
        total_movimentacoes = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO TAGPLUS'
        ).count()
        
        print(f"   Total NFs TagPlus: {total_nfs}")
        print(f"   Total itens importados: {total_itens}")
        print(f"   Total movimentações criadas: {total_movimentacoes}")
        
        if total_movimentacoes < total_itens:
            print(f"   ⚠️  ALERTA: Movimentações ({total_movimentacoes}) < Itens ({total_itens})")
        else:
            print(f"   ✅ Movimentações OK")
        
        print("=" * 80)

if __name__ == "__main__":
    verificar_importacao_tagplus()