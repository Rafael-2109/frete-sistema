#!/usr/bin/env python
"""Debug específico para entender o problema do CT-e fixo"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.models import Frete
from app.utils.tabela_frete_manager import TabelaFreteManager
from app.utils.calculadora_frete import CalculadoraFrete

app = create_app()

with app.app_context():
    # Buscar um frete e forçar um valor de CT-e para teste
    frete = Frete.query.order_by(Frete.id.desc()).first()
    
    print(f"\n📊 TESTE CT-e FIXO - Frete ID: {frete.id}")
    print("="*60)
    
    # Forçar um valor de CT-e para teste
    print("CONFIGURANDO CT-e FIXO PARA TESTE:")
    frete.tabela_valor_cte = 15.00  # R$ 15,00 de taxa CT-e
    db.session.commit()
    
    print(f"  tabela_valor_cte configurado: R$ {frete.tabela_valor_cte}")
    
    # Preparar dados
    tabela_dados = TabelaFreteManager.preparar_dados_tabela(frete)
    print(f"\nDADOS PREPARADOS:")
    print(f"  valor_cte: R$ {tabela_dados.get('valor_cte', 0)}")
    print(f"  valor_despacho: R$ {tabela_dados.get('valor_despacho', 0)}")
    print(f"  valor_tas: R$ {tabela_dados.get('valor_tas', 0)}")
    
    # Configuração
    transportadora_config = {
        'aplica_gris_pos_minimo': False,
        'aplica_adv_pos_minimo': False,
        'aplica_rca_pos_minimo': False,
        'aplica_pedagio_pos_minimo': False,
        'aplica_despacho_pos_minimo': False,
        'aplica_cte_pos_minimo': False,
        'aplica_tas_pos_minimo': False,
        'pedagio_por_fracao': True
    }
    
    # Calcular
    resultado = CalculadoraFrete.calcular_frete_unificado(
        peso=frete.peso_total,
        valor_mercadoria=frete.valor_total_nfs,
        tabela_dados=tabela_dados,
        transportadora_optante=True,
        transportadora_config=transportadora_config,
        cidade={'icms': 0}
    )
    
    print("\nRESULTADO DA CALCULADORA:")
    detalhes = resultado.get('detalhes', {})
    print(f"  valor_cte: R$ {detalhes.get('valor_cte', 0)}")
    print(f"  valor_despacho: R$ {detalhes.get('valor_despacho', 0)}")
    print(f"  valor_tas: R$ {detalhes.get('valor_tas', 0)}")
    print(f"  componentes_antes_minimo: R$ {detalhes.get('componentes_antes_minimo', 0)}")
    
    # Simular montagem dos componentes como em routes.py
    print("\nMONTAGEM DOS COMPONENTES (como em routes.py):")
    valor_cte_tabela = detalhes.get('valor_cte', 0)
    tas = detalhes.get('valor_tas', 0)
    despacho = detalhes.get('valor_despacho', 0)
    
    print("\nValores fixos que seriam exibidos:")
    for nome, valor in [
        ('TAS', tas),
        ('Despacho', despacho),
        ('CT-e', valor_cte_tabela)
    ]:
        if valor > 0:
            print(f"  {nome} (fixo): R$ {valor:.2f}")
    
    print("\n" + "="*60)
    print("ANÁLISE:")
    if valor_cte_tabela > 0:
        print(f"✅ CT-e fixo deveria aparecer com R$ {valor_cte_tabela:.2f}")
    else:
        print(f"❌ CT-e fixo NÃO apareceria (valor = {valor_cte_tabela})")
    
    # Verificar se está sendo somado em algum lugar
    print(f"\nComponentes antes do mínimo: R$ {detalhes.get('componentes_antes_minimo', 0)}")
    print("Detalhamento:")
    print(f"  GRIS: R$ {detalhes.get('gris', 0)}")
    print(f"  ADV: R$ {detalhes.get('adv', 0)}")
    print(f"  RCA: R$ {detalhes.get('rca', 0)}")
    print(f"  Pedágio: R$ {detalhes.get('pedagio', 0)}")
    print(f"  TAS: R$ {detalhes.get('valor_tas', 0)}")
    print(f"  Despacho: R$ {detalhes.get('valor_despacho', 0)}")
    print(f"  CT-e: R$ {detalhes.get('valor_cte', 0)}")
    
    # Calcular soma manual
    soma_manual = (
        detalhes.get('gris', 0) +
        detalhes.get('adv', 0) +
        detalhes.get('rca', 0) +
        detalhes.get('pedagio', 0) +
        detalhes.get('valor_tas', 0) +
        detalhes.get('valor_despacho', 0) +
        detalhes.get('valor_cte', 0)
    )
    
    print(f"\nSoma manual dos componentes: R$ {soma_manual:.2f}")
    print(f"Componentes_antes_minimo da calculadora: R$ {detalhes.get('componentes_antes_minimo', 0)}")
    
    if abs(soma_manual - detalhes.get('componentes_antes_minimo', 0)) < 0.01:
        print("✅ Valores conferem - CT-e está sendo somado corretamente")
    else:
        print("❌ PROBLEMA: Valores não conferem!")