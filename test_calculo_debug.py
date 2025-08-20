#!/usr/bin/env python
"""Script para debugar o cálculo de frete e entender por que valores não aparecem"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.models import Frete
from app.utils.calculadora_frete import CalculadoraFrete
from app.utils.tabela_frete_manager import TabelaFreteManager

app = create_app()

with app.app_context():
    # Buscar um frete de teste
    frete = Frete.query.first()
    
    if not frete:
        print("❌ Nenhum frete encontrado para teste")
        sys.exit(1)
    
    print(f"📊 Testando com Frete ID: {frete.id}")
    print(f"   Peso: {frete.peso_total}")
    print(f"   Valor NFs: {frete.valor_total_nfs}")
    print(f"   Transportadora: {frete.transportadora.razao_social if frete.transportadora else 'N/A'}")
    print()
    
    # Preparar dados da tabela
    tabela_dados = TabelaFreteManager.preparar_dados_tabela(frete)
    
    print("📋 DADOS DA TABELA:")
    print(f"   valor_kg: {tabela_dados.get('valor_kg', 0)}")
    print(f"   percentual_valor: {tabela_dados.get('percentual_valor', 0)}")
    print(f"   percentual_gris: {tabela_dados.get('percentual_gris', 0)}")
    print(f"   gris_minimo: {tabela_dados.get('gris_minimo', 0)}")
    print(f"   percentual_adv: {tabela_dados.get('percentual_adv', 0)}")
    print(f"   adv_minimo: {tabela_dados.get('adv_minimo', 0)}")
    print(f"   percentual_rca: {tabela_dados.get('percentual_rca', 0)}")
    print(f"   pedagio_por_100kg: {tabela_dados.get('pedagio_por_100kg', 0)}")
    print(f"   frete_minimo_peso: {tabela_dados.get('frete_minimo_peso', 0)}")
    print(f"   frete_minimo_valor: {tabela_dados.get('frete_minimo_valor', 0)}")
    print()
    
    # Configuração da transportadora
    transportadora_config = {
        'aplica_gris_pos_minimo': False,
        'aplica_adv_pos_minimo': False,
        'aplica_rca_pos_minimo': False,
        'aplica_pedagio_pos_minimo': False,
        'aplica_tas_pos_minimo': False,
        'aplica_despacho_pos_minimo': False,
        'aplica_cte_pos_minimo': False,
        'pedagio_por_fracao': True
    }
    
    # Chamar calculadora
    resultado = CalculadoraFrete.calcular_frete_unificado(
        peso=frete.peso_total,
        valor_mercadoria=frete.valor_total_nfs,
        tabela_dados=tabela_dados,
        transportadora_optante=frete.transportadora.optante if frete.transportadora else True,
        transportadora_config=transportadora_config,
        cidade={'icms': tabela_dados.get('icms_destino', 0)}
    )
    
    print("🔍 RESULTADO DO CÁLCULO:")
    print(f"   valor_bruto (sem ICMS): R$ {resultado.get('valor_bruto', 0):.2f}")
    print(f"   valor_com_icms: R$ {resultado.get('valor_com_icms', 0):.2f}")
    print(f"   valor_liquido: R$ {resultado.get('valor_liquido', 0):.2f}")
    print()
    
    detalhes = resultado.get('detalhes', {})
    print("📊 DETALHES DO CÁLCULO:")
    print(f"   peso_para_calculo: {detalhes.get('peso_para_calculo', 0)}")
    print(f"   frete_base: R$ {detalhes.get('frete_base', 0):.2f}")
    print(f"   gris: R$ {detalhes.get('gris', 0):.2f}")
    print(f"   adv: R$ {detalhes.get('adv', 0):.2f}")
    print(f"   rca: R$ {detalhes.get('rca', 0):.2f}")
    print(f"   pedagio: R$ {detalhes.get('pedagio', 0):.2f}")
    print(f"   componentes_antes_minimo: R$ {detalhes.get('componentes_antes_minimo', 0):.2f}")
    print(f"   frete_liquido_antes_minimo: R$ {detalhes.get('frete_liquido_antes_minimo', 0):.2f}")
    print(f"   componentes_apos_minimo: R$ {detalhes.get('componentes_apos_minimo', 0):.2f}")
    print()
    
    # Verificar problemas específicos
    print("⚠️  ANÁLISE DE PROBLEMAS:")
    
    # GRIS
    if tabela_dados.get('percentual_gris', 0) > 0:
        gris_esperado = frete.valor_total_nfs * (tabela_dados.get('percentual_gris', 0) / 100)
        gris_minimo = tabela_dados.get('gris_minimo', 0)
        gris_final = max(gris_esperado, gris_minimo)
        print(f"   GRIS: Esperado R$ {gris_esperado:.2f} (mín: R$ {gris_minimo:.2f}) → Final: R$ {gris_final:.2f}")
        print(f"         Retornado: R$ {detalhes.get('gris', 0):.2f}")
        if abs(gris_final - detalhes.get('gris', 0)) > 0.01:
            print(f"         ❌ DIFERENÇA DETECTADA!")
    
    # Pedágio
    if tabela_dados.get('pedagio_por_100kg', 0) > 0:
        peso_calc = detalhes.get('peso_para_calculo', frete.peso_total)
        fracoes = int((peso_calc - 1) // 100) + 1
        pedagio_esperado = fracoes * tabela_dados.get('pedagio_por_100kg', 0)
        print(f"   PEDÁGIO: {peso_calc} kg = {fracoes} frações × R$ {tabela_dados.get('pedagio_por_100kg', 0):.2f}")
        print(f"            Esperado: R$ {pedagio_esperado:.2f}")
        print(f"            Retornado: R$ {detalhes.get('pedagio', 0):.2f}")
        if abs(pedagio_esperado - detalhes.get('pedagio', 0)) > 0.01:
            print(f"            ❌ DIFERENÇA DETECTADA!")
    
    # Subtotal antes do mínimo
    subtotal_esperado = detalhes.get('frete_base', 0) + detalhes.get('componentes_antes_minimo', 0)
    print(f"   SUBTOTAL ANTES MÍNIMO:")
    print(f"      Base: R$ {detalhes.get('frete_base', 0):.2f}")
    print(f"      + Componentes: R$ {detalhes.get('componentes_antes_minimo', 0):.2f}")
    print(f"      = Esperado: R$ {subtotal_esperado:.2f}")
    print(f"      Retornado: R$ {detalhes.get('frete_liquido_antes_minimo', 0):.2f}")
    if abs(subtotal_esperado - detalhes.get('frete_liquido_antes_minimo', 0)) > 0.01:
        print(f"      ❌ DIFERENÇA DETECTADA!")