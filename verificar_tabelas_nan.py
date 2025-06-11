#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Verificar Valores NaN nas Tabelas
"""

from app import create_app, db
from app.tabelas.models import TabelaFrete

def verificar_tabelas():
    app = create_app()
    
    with app.app_context():
        print("🔍 Verificando valores NaN nas tabelas de frete...")
        
        tabelas = TabelaFrete.query.limit(10).all()
        
        if not tabelas:
            print("⚠️ Nenhuma tabela de frete encontrada!")
            return
        
        print(f"📊 Verificando {len(tabelas)} tabelas...")
        
        campos_problematicos = []
        
        for i, tabela in enumerate(tabelas):
            print(f"\n🔍 Tabela {i+1} (ID: {tabela.id}):")
            print(f"   Transportadora: {tabela.transportadora.razao_social}")
            print(f"   Nome tabela: {repr(tabela.nome_tabela)}")
            print(f"   Modalidade: {repr(tabela.modalidade)}")
            
            # Verificar campos numéricos
            campos = {
                'valor_kg': tabela.valor_kg,
                'frete_minimo_valor': tabela.frete_minimo_valor,
                'frete_minimo_peso': tabela.frete_minimo_peso,
                'percentual_valor': tabela.percentual_valor,
                'percentual_gris': tabela.percentual_gris,
                'percentual_adv': tabela.percentual_adv,
                'valor_despacho': tabela.valor_despacho,
                'valor_cte': tabela.valor_cte,
                'criado_por': tabela.criado_por
            }
            
            for campo, valor in campos.items():
                valor_str = str(valor)
                if 'nan' in valor_str.lower() or valor is None:
                    print(f"   ❌ {campo}: {repr(valor)} ({type(valor)})")
                    campos_problematicos.append(f"Tabela {tabela.id}.{campo}")
                else:
                    print(f"   ✅ {campo}: {repr(valor)}")
        
        if campos_problematicos:
            print(f"\n❌ PROBLEMAS ENCONTRADOS:")
            for campo in campos_problematicos:
                print(f"   • {campo}")
        else:
            print(f"\n✅ Todas as tabelas verificadas estão OK!")

if __name__ == "__main__":
    verificar_tabelas() 