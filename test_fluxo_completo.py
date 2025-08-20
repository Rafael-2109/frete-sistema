#!/usr/bin/env python
"""Teste do fluxo completo: Cotação → Embarque → Frete → Análise"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.models import Frete
from app.embarques.models import Embarque, EmbarqueItem
from app.tabelas.models import TabelaFrete
from app.utils.tabela_frete_manager import TabelaFreteManager

app = create_app()

with app.app_context():
    print("="*70)
    print("ANÁLISE DO FLUXO COMPLETO DE DADOS")
    print("="*70)
    
    # 1. VERIFICAR TABELA DE FRETE
    print("\n1️⃣ TABELA DE FRETE (origem da cotação):")
    tabela = TabelaFrete.query.filter(TabelaFrete.valor_cte > 0).first()
    if tabela:
        print(f"  Tabela: {tabela.nome_tabela}")
        print(f"  valor_cte: R$ {tabela.valor_cte}")
    else:
        print("  ❌ Nenhuma tabela tem valor_cte configurado")
    
    # 2. VERIFICAR EMBARQUE
    print("\n2️⃣ EMBARQUE (carga DIRETA):")
    embarque = Embarque.query.filter(
        Embarque.tipo_carga == 'DIRETA',
        Embarque.status == 'ativo'
    ).order_by(Embarque.id.desc()).first()
    
    if embarque:
        print(f"  Embarque #{embarque.numero} - {embarque.tipo_carga}")
        print(f"  tabela_valor_cte: R$ {embarque.tabela_valor_cte}")
        
        # Testar manager com embarque
        dados_embarque = TabelaFreteManager.preparar_dados_tabela(embarque)
        print(f"  Manager retorna valor_cte: R$ {dados_embarque.get('valor_cte', 0)}")
    else:
        print("  ❌ Nenhum embarque DIRETA ativo encontrado")
    
    # 3. VERIFICAR EMBARQUE ITEM
    print("\n3️⃣ EMBARQUE ITEM (carga FRACIONADA):")
    item = EmbarqueItem.query.join(Embarque).filter(
        Embarque.tipo_carga == 'FRACIONADA',
        EmbarqueItem.status == 'ativo'
    ).first()
    
    if item:
        print(f"  Item do Embarque #{item.embarque.numero} - NF {item.nota_fiscal}")
        print(f"  tabela_valor_cte: R$ {item.tabela_valor_cte}")
        
        # Testar manager com item
        dados_item = TabelaFreteManager.preparar_dados_tabela(item)
        print(f"  Manager retorna valor_cte: R$ {dados_item.get('valor_cte', 0)}")
    else:
        print("  ❌ Nenhum item de embarque FRACIONADA encontrado")
    
    # 4. VERIFICAR FRETE
    print("\n4️⃣ FRETE (lançado do embarque):")
    frete = Frete.query.order_by(Frete.id.desc()).first()
    
    if frete:
        print(f"  Frete ID {frete.id} - {frete.tipo_carga}")
        print(f"  valor_cte: {frete.valor_cte} (valor total do CTe)")
        print(f"  tabela_valor_cte: R$ {frete.tabela_valor_cte} (taxa de emissão)")
        
        # Testar manager com frete
        dados_frete = TabelaFreteManager.preparar_dados_tabela(frete)
        print(f"  Manager retorna valor_cte: R$ {dados_frete.get('valor_cte', 0)}")
    
    # 5. ANÁLISE DE DIFERENÇAS
    print("\n5️⃣ ANÁLISE DE DIFERENÇAS:")
    print(f"  Frete.valor_cte (total CTe): {frete.valor_cte}")
    print(f"  Frete.tabela_valor_cte (taxa): R$ {frete.tabela_valor_cte}")
    
    # Verificar se o manager está funcionando corretamente
    print("\n" + "="*70)
    print("DIAGNÓSTICO DO MANAGER:")
    
    # Testar com diferentes objetos
    for obj, nome in [(embarque, "Embarque"), (item, "EmbarqueItem"), (frete, "Frete")]:
        if obj:
            print(f"\n{nome}:")
            print(f"  hasattr(obj, 'valor_cte'): {hasattr(obj, 'valor_cte')}")
            print(f"  hasattr(obj, 'tabela_valor_cte'): {hasattr(obj, 'tabela_valor_cte')}")
            
            if hasattr(obj, 'valor_cte'):
                print(f"  obj.valor_cte: {getattr(obj, 'valor_cte', None)}")
            if hasattr(obj, 'tabela_valor_cte'):
                print(f"  obj.tabela_valor_cte: {getattr(obj, 'tabela_valor_cte', None)}")
    
    print("\n" + "="*70)
    print("CONCLUSÃO:")
    
    if frete and frete.tabela_valor_cte:
        dados_test = TabelaFreteManager.preparar_dados_tabela(frete)
        if dados_test.get('valor_cte', 0) == frete.tabela_valor_cte:
            print("✅ Manager está pegando o campo correto (tabela_valor_cte)")
        else:
            print("❌ Manager está pegando o campo errado!")
            print(f"   Esperado: R$ {frete.tabela_valor_cte}")
            print(f"   Retornado: R$ {dados_test.get('valor_cte', 0)}")