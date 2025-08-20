#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a integração do cálculo de frete
Compara resultados antes e depois da integração
"""

import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.utils.frete_simulador import calcular_fretes_possiveis
from app.localidades.models import Cidade

# Cria a aplicação Flask
app = create_app()

def testar_calculo_frete():
    """
    Testa o cálculo de frete com a nova integração
    """
    with app.app_context():
        print("=" * 60)
        print("TESTE DE INTEGRAÇÃO - CÁLCULO DE FRETE")
        print("=" * 60)
        
        # Buscar uma cidade para teste (ex: São Paulo)
        cidade = Cidade.query.filter_by(nome='SAO PAULO', uf='SP').first()
        
        if not cidade:
            print("❌ Cidade de teste não encontrada")
            return
            
        print(f"\n📍 Cidade de teste: {cidade.nome}/{cidade.uf}")
        print(f"   ICMS: {cidade.icms * 100:.0f}%")
        
        # Parâmetros de teste
        peso_teste = 1000  # 1000 kg
        valor_teste = 10000  # R$ 10.000
        
        print(f"\n📦 Parâmetros de teste:")
        print(f"   Peso: {peso_teste} kg")
        print(f"   Valor: R$ {valor_teste:.2f}")
        
        # Calcular fretes possíveis
        print("\n🔄 Calculando fretes possíveis...")
        
        try:
            resultados = calcular_fretes_possiveis(
                cidade_destino_id=cidade.id,
                peso_utilizado=peso_teste,
                valor_carga=valor_teste,
                tipo_carga="FRACIONADA"
            )
            
            print(f"\n✅ {len(resultados)} opções de frete encontradas")
            
            # Mostrar primeiras 3 opções
            for i, opcao in enumerate(resultados[:3], 1):
                print(f"\n📊 Opção {i}:")
                print(f"   Transportadora: {opcao['transportadora']}")
                print(f"   Tabela: {opcao['nome_tabela']}")
                print(f"   Valor com ICMS: R$ {opcao['valor_total']:.2f}")
                print(f"   Valor líquido: R$ {opcao['valor_liquido']:.2f}")
                
                # Verificar se novos campos estão presentes
                if 'gris_minimo' in opcao:
                    print(f"   ✅ GRIS Mínimo: R$ {opcao['gris_minimo']:.2f}")
                if 'adv_minimo' in opcao:
                    print(f"   ✅ ADV Mínimo: R$ {opcao['adv_minimo']:.2f}")
                if 'icms_proprio' in opcao:
                    print(f"   ✅ ICMS Próprio: {opcao['icms_proprio']}%")
                
                # Mostrar detalhes do cálculo se disponível
                if 'detalhes_calculo' in opcao and opcao['detalhes_calculo']:
                    detalhes = opcao['detalhes_calculo']
                    print(f"\n   📝 Detalhes do cálculo:")
                    print(f"      Frete base: R$ {detalhes.get('frete_base', 0):.2f}")
                    print(f"      GRIS: R$ {detalhes.get('gris', 0):.2f}")
                    print(f"      ADV: R$ {detalhes.get('adv', 0):.2f}")
                    print(f"      Pedágio: R$ {detalhes.get('pedagio', 0):.2f}")
                    
                    if detalhes.get('componentes_antes_minimo'):
                        print(f"      Componentes antes mínimo: R$ {detalhes['componentes_antes_minimo']:.2f}")
                    if detalhes.get('componentes_apos_minimo'):
                        print(f"      Componentes após mínimo: R$ {detalhes['componentes_apos_minimo']:.2f}")
            
            # Testar carga DIRETA
            print("\n" + "=" * 40)
            print("🚚 Testando carga DIRETA (tabela mais cara)...")
            
            resultados_direta = calcular_fretes_possiveis(
                cidade_destino_id=cidade.id,
                peso_utilizado=peso_teste * 10,  # 10 toneladas
                valor_carga=valor_teste * 10,     # R$ 100.000
                tipo_carga="DIRETA"
            )
            
            print(f"✅ {len(resultados_direta)} opções de frete DIRETA")
            
            # Verificar se tem critério de seleção
            for opcao in resultados_direta[:2]:
                if 'criterio_selecao' in opcao:
                    print(f"\n📊 {opcao['transportadora']}:")
                    print(f"   {opcao['criterio_selecao']}")
                    print(f"   Valor: R$ {opcao['valor_liquido']:.2f}")
            
            print("\n" + "=" * 60)
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO NO TESTE: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    if testar_calculo_frete():
        sys.exit(0)
    else:
        sys.exit(1)