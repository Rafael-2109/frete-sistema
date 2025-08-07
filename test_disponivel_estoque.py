#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar a nova coluna Disponível no saldo-estoque
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.estoque.routes import converter_projecao_para_resumo

def testar_disponibilidade():
    """Testa a nova funcionalidade de disponibilidade"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE DA COLUNA DISPONÍVEL (SEM QUANTIDADE DO PEDIDO)")
        print("="*60)
        
        # Testar alguns produtos
        produtos_teste = ['4310164', '4520145', '4240211']
        
        for cod_produto in produtos_teste:
            print(f"\n🔍 Testando produto: {cod_produto}")
            print("-" * 40)
            
            # Obter projeção
            projecao = ServicoEstoqueTempoReal.get_projecao_completa(cod_produto, dias=28)
            
            if projecao:
                # Converter para resumo
                resumo = converter_projecao_para_resumo(projecao)
                
                print(f"📊 Estoque Atual: {resumo['estoque_atual']:.0f}")
                print(f"📉 Menor Estoque D7: {resumo['menor_estoque_d7']:.0f}")
                print(f"🚨 Status: {resumo['status_ruptura']}")
                
                # Nova informação de disponibilidade
                if resumo.get('qtd_disponivel') and resumo['qtd_disponivel'] > 0:
                    print(f"\n✅ DISPONÍVEL:")
                    print(f"   Quantidade: {resumo['qtd_disponivel']:.0f} unidades")
                    print(f"   Data: {resumo['data_disponivel']}")
                    if resumo.get('dias_disponivel') is not None:
                        print(f"   Quando: D+{resumo['dias_disponivel']}")
                elif resumo['estoque_atual'] > 0:
                    print(f"\n✅ DISPONÍVEL AGORA: {resumo['estoque_atual']:.0f} unidades")
                else:
                    print(f"\n❌ INDISPONÍVEL")
                
                # Mostrar projeção resumida
                print(f"\n📅 Projeção próximos dias:")
                projecao_lista = resumo.get('projecao', [])[:5]  # Primeiros 5 dias
                for dia in projecao_lista:
                    saldo = dia.get('saldo_inicial', 0) - dia.get('saida', 0)
                    print(f"   D{dia.get('dia', '?'):2}: Saldo = {saldo:7.0f} | Est.Final = {dia.get('saldo_final', 0):7.0f}")
            else:
                print(f"❌ Sem dados de projeção para o produto")
        
        print("\n" + "="*60)
        print("CRITÉRIOS DOS BADGES:")
        print("="*60)
        print("🔴 CRÍTICO: Quando há ruptura prevista (estoque vai zerar)")
        print("🟡 ATENÇÃO: Quando menor_estoque_d7 < 100")
        print("🟢 OK: Todos os outros casos")
        
        print("\n" + "="*60)
        print("TESTE CONCLUÍDO")
        print("="*60 + "\n")

if __name__ == "__main__":
    testar_disponibilidade()