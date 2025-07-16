"""
Script para buscar todos os produtos de uma NF específica
========================================================

Busca todos os itens da NF 137275 para análise completa

Autor: Sistema de Fretes
Data: 2025-07-15
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.services.faturamento_service import FaturamentoService

def buscar_nf_completa():
    """Busca todos os itens de uma NF específica"""
    
    print("=" * 80)
    print("ANÁLISE COMPLETA DA NF 137275")
    print("=" * 80)
    
    try:
        # Criar serviço
        service = FaturamentoService()
        
        # Buscar mais registros para pegar todos os itens da NF
        print("\n🔍 Buscando dados do faturamento (limite: 100 registros)...")
        resultado = service.obter_faturamento_otimizado(
            usar_filtro_postado=True,
            limite=100  # Aumentar para 100 registros
        )
        
        if not resultado['sucesso']:
            print(f"❌ Erro: {resultado.get('erro')}")
            return
        
        dados = resultado.get('dados', [])
        
        if not dados:
            print("⚠️ Nenhum dado encontrado")
            return
        
        # Filtrar apenas a NF 137275
        nf_137275 = [item for item in dados if item.get('numero_nf') == '137275']
        
        print(f"\n✅ {len(nf_137275)} itens encontrados para NF 137275")
        print(f"📊 Total de registros buscados: {len(dados)}")
        
        if not nf_137275:
            print("❌ NF 137275 não encontrada nos dados")
            # Mostrar as NFs que foram encontradas
            nfs_encontradas = set([item.get('numero_nf') for item in dados if item.get('numero_nf')])
            print(f"NFs encontradas: {sorted(nfs_encontradas)}")
            return
        
        # Analisar cada item da NF
        produtos_com_dados = 0
        produtos_sem_dados = 0
        
        for i, item in enumerate(nf_137275, 1):
            print(f"\n📋 ITEM {i} da NF 137275:")
            print("-" * 40)
            
            # Dados principais
            cod_produto = item.get('cod_produto', '')
            nome_produto = item.get('nome_produto', '')
            quantidade = item.get('qtd_produto_faturado', 0)
            valor = item.get('valor_produto_faturado', 0)
            peso_unit = item.get('peso_unitario_produto', 0)
            
            print(f"  • Código: '{cod_produto}'")
            print(f"  • Nome: '{nome_produto}'")
            print(f"  • Quantidade: {quantidade}")
            print(f"  • Valor: {valor}")
            print(f"  • Peso Unit: {peso_unit}")
            
            # Verificar se tem dados completos
            if cod_produto and nome_produto and quantidade > 0:
                produtos_com_dados += 1
                print(f"  ✅ PRODUTO COMPLETO")
            else:
                produtos_sem_dados += 1
                print(f"  ❌ PRODUTO INCOMPLETO")
                
                # Mostrar dados brutos da linha para debug
                print(f"  🔍 DEBUG:")
                print(f"    - product_id original: {item.get('debug_product_id', 'N/A')}")
                print(f"    - template_id: {item.get('debug_template_id', 'N/A')}")
        
        # Resumo
        print(f"\n" + "=" * 80)
        print(f"RESUMO DA NF 137275:")
        print(f"• Total de itens: {len(nf_137275)}")
        print(f"• Produtos completos: {produtos_com_dados}")
        print(f"• Produtos incompletos: {produtos_sem_dados}")
        print(f"• Taxa de sucesso: {(produtos_com_dados/len(nf_137275)*100):.1f}%")
        
        # Se não encontrou os 15, sugerir buscar mais
        if len(nf_137275) < 15:
            print(f"\n⚠️ Esperado: 15 produtos, Encontrado: {len(nf_137275)}")
            print("💡 Pode precisar aumentar o limite de busca ou ajustar filtros")
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    buscar_nf_completa() 