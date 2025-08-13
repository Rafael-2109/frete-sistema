#!/usr/bin/env python3
"""
Teste do AgrupamentoService com pedidos FATURADOS
=================================================

Valida que separações de pedidos FATURADOS são consideradas quando
EmbarqueItem.erro_validacao != None

Autor: Sistema de Fretes
Data: 2025-08-13
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app import create_app, db
from app.carteira.services.agrupamento_service import AgrupamentoService
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from sqlalchemy import text

def testar_agrupamento():
    """Testa o agrupamento com diferentes cenários"""
    
    app = create_app()
    
    with app.app_context():
        service = AgrupamentoService()
        
        print("🔍 TESTE DO AGRUPAMENTO COM PEDIDOS FATURADOS")
        print("=" * 60)
        
        # 1. Buscar pedidos FATURADOS que têm separações
        query = """
        SELECT DISTINCT 
            s.num_pedido,
            p.status as status_pedido,
            s.separacao_lote_id,
            ei.nota_fiscal,
            ei.erro_validacao,
            COUNT(*) OVER (PARTITION BY s.num_pedido) as qtd_itens
        FROM separacao s
        INNER JOIN pedidos p ON s.separacao_lote_id = p.separacao_lote_id
        LEFT JOIN embarque_item ei ON ei.separacao_lote_id = s.separacao_lote_id
        WHERE p.status = 'FATURADO'
        ORDER BY s.num_pedido
        LIMIT 10
        """
        
        pedidos_faturados = db.session.execute(text(query)).fetchall()
        
        print(f"\n📊 Encontrados {len(pedidos_faturados)} pedidos FATURADOS com separações\n")
        
        # 2. Testar cada pedido
        for pedido in pedidos_faturados[:5]:  # Testar apenas 5 primeiros
            num_pedido = pedido[0]
            status = pedido[1]
            lote = pedido[2]
            nf = pedido[3]
            erro = pedido[4]
            qtd_itens = pedido[5]
            
            print(f"📦 Pedido: {num_pedido}")
            print(f"   Status: {status}")
            print(f"   Lote: {lote}")
            print(f"   NF: {nf or 'Sem NF'}")
            print(f"   Erro Validação: {erro or 'Nenhum'}")
            print(f"   Qtd Itens: {qtd_itens}")
            
            # Calcular separações usando o método privado
            qtd_sep, valor_sep, expedit = service._calcular_separacoes(num_pedido)
            
            print(f"   📈 Qtd Separações Calculada: {qtd_sep}")
            print(f"   💰 Valor Separações: R$ {valor_sep:.2f}")
            
            # Validar lógica
            if status == 'FATURADO' and erro:
                if qtd_sep > 0:
                    print(f"   ✅ CORRETO: Pedido FATURADO com erro_validacao={erro} tem separações contadas")
                else:
                    print(f"   ❌ ERRO: Pedido FATURADO com erro_validacao={erro} deveria ter separações!")
            elif status == 'FATURADO' and not erro:
                if qtd_sep == 0:
                    print(f"   ✅ CORRETO: Pedido FATURADO sem erro não conta separações")
                else:
                    print(f"   ⚠️ ATENÇÃO: Pedido FATURADO sem erro está contando separações")
            
            print("-" * 40)
        
        # 3. Testar agrupamento completo
        print("\n🔄 Testando agrupamento completo...")
        pedidos_agrupados = service.obter_pedidos_agrupados()
        
        # Contar pedidos com separações
        pedidos_com_sep = [p for p in pedidos_agrupados if p.get('qtd_separacoes', 0) > 0]
        pedidos_faturados_com_sep = [
            p for p in pedidos_com_sep 
            if 'FATURADO' in str(p.get('status_pedido', ''))
        ]
        
        print(f"\n📊 ESTATÍSTICAS FINAIS:")
        print(f"   Total de pedidos agrupados: {len(pedidos_agrupados)}")
        print(f"   Pedidos com separações: {len(pedidos_com_sep)}")
        print(f"   Pedidos FATURADOS com separações: {len(pedidos_faturados_com_sep)}")
        
        if pedidos_faturados_com_sep:
            print(f"\n✅ SUCESSO: Encontrados {len(pedidos_faturados_com_sep)} pedidos FATURADOS com separações!")
            print("   Isso indica que a lógica está funcionando corretamente.")
        else:
            print("\n⚠️ ATENÇÃO: Nenhum pedido FATURADO com separações encontrado.")
            print("   Pode não haver dados de teste ou a lógica precisa revisão.")
        
        # 4. Exemplo específico de pedido FATURADO com erro
        print("\n🔎 Buscando exemplo específico...")
        exemplo = db.session.execute(text("""
            SELECT 
                s.num_pedido,
                p.status,
                ei.erro_validacao,
                COUNT(DISTINCT s.separacao_lote_id) as qtd_lotes
            FROM separacao s
            INNER JOIN pedidos p ON s.separacao_lote_id = p.separacao_lote_id
            INNER JOIN embarque_item ei ON ei.separacao_lote_id = s.separacao_lote_id
            WHERE p.status = 'FATURADO'
            AND ei.erro_validacao IS NOT NULL
            GROUP BY s.num_pedido, p.status, ei.erro_validacao
            LIMIT 1
        """)).fetchone()
        
        if exemplo:
            print(f"\n📌 Exemplo encontrado:")
            print(f"   Pedido: {exemplo[0]}")
            print(f"   Status: {exemplo[1]}")
            print(f"   Erro: {exemplo[2]}")
            print(f"   Lotes esperados: {exemplo[3]}")
            
            # Testar este pedido específico
            qtd_calc, _, _ = service._calcular_separacoes(exemplo[0])
            print(f"   Lotes calculados: {qtd_calc}")
            
            if qtd_calc == exemplo[3]:
                print(f"   ✅ PERFEITO: Cálculo correto!")
            else:
                print(f"   ❌ DIVERGÊNCIA: Esperado {exemplo[3]}, calculado {qtd_calc}")
        
        print("\n" + "=" * 60)
        print("🏁 TESTE CONCLUÍDO")
        
        return True

if __name__ == "__main__":
    try:
        testar_agrupamento()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)