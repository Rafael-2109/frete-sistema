#!/usr/bin/env python
"""Debug simplificado para verificar valores do frete"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.models import Frete
from app.utils.tabela_frete_manager import TabelaFreteManager

app = create_app()

with app.app_context():
    # Buscar o frete mais recente
    frete = Frete.query.order_by(Frete.id.desc()).first()
    
    if not frete:
        print("❌ Nenhum frete encontrado")
        sys.exit(1)
    
    print(f"\n📊 Frete ID: {frete.id}")
    print(f"   Cliente: {frete.nome_cliente}")
    print(f"   Peso Total: {frete.peso_total} kg")
    print(f"   Valor NFs: R$ {frete.valor_total_nfs}")
    print("\n" + "="*60)
    
    # Verificar campos da tabela no objeto frete
    print("CAMPOS DA TABELA NO FRETE:")
    print(f"  tabela_valor_kg: {frete.tabela_valor_kg}")
    print(f"  tabela_percentual_valor: {frete.tabela_percentual_valor}")
    print(f"  tabela_percentual_gris: {frete.tabela_percentual_gris}")
    print(f"  tabela_gris_minimo: {frete.tabela_gris_minimo}")
    print(f"  tabela_percentual_adv: {frete.tabela_percentual_adv}")
    print(f"  tabela_adv_minimo: {frete.tabela_adv_minimo}")
    print(f"  tabela_percentual_rca: {frete.tabela_percentual_rca}")
    print(f"  tabela_pedagio_por_100kg: {frete.tabela_pedagio_por_100kg}")
    print(f"  tabela_valor_tas: {frete.tabela_valor_tas}")
    print(f"  tabela_valor_despacho: {frete.tabela_valor_despacho}")
    print(f"  tabela_valor_cte: {frete.tabela_valor_cte}")
    print(f"  tabela_frete_minimo_valor: {frete.tabela_frete_minimo_valor}")
    print(f"  tabela_frete_minimo_peso: {frete.tabela_frete_minimo_peso}")
    
    print("\n" + "="*60)
    print("DADOS PREPARADOS PELO MANAGER:")
    
    # Usar o TabelaFreteManager para preparar dados
    tabela_dados = TabelaFreteManager.preparar_dados_tabela(frete)
    
    for campo, valor in tabela_dados.items():
        print(f"  {campo}: {valor}")
    
    print("\n" + "="*60)
    print("CÁLCULOS ESPERADOS:")
    
    # Cálculo esperado de GRIS
    if tabela_dados.get('percentual_gris', 0) > 0:
        gris_calc = frete.valor_total_nfs * (tabela_dados['percentual_gris'] / 100)
        gris_min = tabela_dados.get('gris_minimo', 0)
        gris_final = max(gris_calc, gris_min)
        print(f"  GRIS: {frete.valor_total_nfs} × {tabela_dados['percentual_gris']}% = R$ {gris_calc:.2f}")
        print(f"        Mínimo: R$ {gris_min:.2f}")
        print(f"        Final: R$ {gris_final:.2f}")
    else:
        print(f"  GRIS: Não configurado (percentual = {tabela_dados.get('percentual_gris', 0)})")
    
    # Cálculo esperado de Pedágio
    if tabela_dados.get('pedagio_por_100kg', 0) > 0:
        peso_minimo = tabela_dados.get('frete_minimo_peso', 0)
        peso_calc = max(frete.peso_total, peso_minimo)
        fracoes = int((peso_calc - 1) // 100) + 1
        pedagio_final = fracoes * tabela_dados['pedagio_por_100kg']
        print(f"  PEDÁGIO: {peso_calc} kg = {fracoes} frações × R$ {tabela_dados['pedagio_por_100kg']:.2f}")
        print(f"           Final: R$ {pedagio_final:.2f}")
    else:
        print(f"  PEDÁGIO: Não configurado (valor = {tabela_dados.get('pedagio_por_100kg', 0)})")
    
    # Cálculo do frete base
    peso_minimo = tabela_dados.get('frete_minimo_peso', 0)
    peso_calc = max(frete.peso_total, peso_minimo)
    frete_peso = peso_calc * tabela_dados.get('valor_kg', 0)
    frete_valor = frete.valor_total_nfs * (tabela_dados.get('percentual_valor', 0) / 100)
    frete_base = frete_peso + frete_valor
    print(f"  FRETE BASE:")
    print(f"    Peso: {peso_calc} × {tabela_dados.get('valor_kg', 0)} = R$ {frete_peso:.2f}")
    print(f"    Valor: {frete.valor_total_nfs} × {tabela_dados.get('percentual_valor', 0)}% = R$ {frete_valor:.2f}")
    print(f"    Total Base: R$ {frete_base:.2f}")