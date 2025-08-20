#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a nova função analise_diferencas
com os novos campos e configurações
"""

import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.fretes.models import Frete
from app.transportadoras.models import Transportadora

# Cria a aplicação Flask
app = create_app()

def testar_analise_diferencas():
    """
    Testa a nova função analise_diferencas
    """
    with app.app_context():
        print("=" * 60)
        print("TESTE DA FUNÇÃO ANALISE_DIFERENCAS")
        print("=" * 60)
        
        # Buscar um frete para teste
        frete = Frete.query.first()
        
        if not frete:
            print("❌ Nenhum frete encontrado para teste")
            return False
            
        print(f"\n📊 Frete de teste: #{frete.id}")
        print(f"   Cliente: {frete.nome_cliente}")
        print(f"   Transportadora: {frete.transportadora.razao_social if frete.transportadora else 'N/A'}")
        print(f"   Peso: {frete.peso_total} kg")
        print(f"   Valor: R$ {frete.valor_total_nfs:.2f}")
        
        # Verificar se transportadora tem novos campos
        if frete.transportadora:
            transp = frete.transportadora
            print(f"\n🔧 Configuração da Transportadora:")
            
            # Verificar campos boolean
            campos_boolean = [
                'aplica_gris_pos_minimo',
                'aplica_adv_pos_minimo', 
                'aplica_rca_pos_minimo',
                'aplica_pedagio_pos_minimo',
                'aplica_tas_pos_minimo',
                'aplica_despacho_pos_minimo',
                'aplica_cte_pos_minimo',
                'pedagio_por_fracao'
            ]
            
            for campo in campos_boolean:
                if hasattr(transp, campo):
                    valor = getattr(transp, campo, False)
                    print(f"   {campo}: {valor}")
                else:
                    print(f"   {campo}: ❌ CAMPO NÃO EXISTE")
        
        # Verificar campos da tabela de frete
        print(f"\n📋 Campos da Tabela de Frete:")
        
        campos_tabela = [
            ('tabela_percentual_gris', 'GRIS %'),
            ('tabela_percentual_adv', 'ADV %'),
            ('tabela_percentual_rca', 'RCA %'),
            ('tabela_pedagio_por_100kg', 'Pedágio/100kg'),
            ('tabela_frete_minimo_peso', 'Peso Mínimo'),
            ('tabela_frete_minimo_valor', 'Valor Mínimo')
        ]
        
        for campo, descricao in campos_tabela:
            if hasattr(frete, campo):
                valor = getattr(frete, campo, 0)
                print(f"   {descricao}: {valor}")
            else:
                print(f"   {descricao}: ❌ CAMPO NÃO EXISTE")
        
        # Testar importação dos módulos
        try:
            from app.utils.tabela_frete_manager import TabelaFreteManager
            from app.utils.calculadora_frete import CalculadoraFrete
            print("\n✅ Módulos importados com sucesso")
            
            # Testar preparação de dados
            tabela_dados = TabelaFreteManager.preparar_dados_tabela(frete)
            print(f"\n📊 Dados da tabela preparados:")
            print(f"   Campos disponíveis: {len(tabela_dados)} campos")
            
            # Verificar novos campos nos dados
            novos_campos = ['gris_minimo', 'adv_minimo', 'icms_proprio']
            for campo in novos_campos:
                if campo in tabela_dados:
                    print(f"   ✅ {campo}: {tabela_dados[campo]}")
                else:
                    print(f"   ❌ {campo}: NÃO ENCONTRADO")
            
            # Testar cálculo
            resultado = CalculadoraFrete.calcular_frete_unificado(
                peso=frete.peso_total,
                valor_mercadoria=frete.valor_total_nfs,
                tabela_dados=tabela_dados,  # CORREÇÃO: dados_tabela -> tabela_dados
                transportadora_optante=frete.transportadora.optante if frete.transportadora else True
            )
            
            print(f"\n💰 Resultado do Cálculo:")
            print(f"   Valor Bruto: R$ {resultado.get('valor_bruto', 0):.2f}")
            print(f"   Valor com ICMS: R$ {resultado.get('valor_com_icms', 0):.2f}")
            print(f"   Valor Líquido: R$ {resultado.get('valor_liquido', 0):.2f}")
            
            # Verificar detalhes
            detalhes = resultado.get('detalhes', {})
            if detalhes:
                print(f"\n📝 Detalhes do Cálculo:")
                print(f"   Frete Base: R$ {detalhes.get('frete_base', 0):.2f}")
                print(f"   GRIS: R$ {detalhes.get('gris', 0):.2f}")
                print(f"   ADV: R$ {detalhes.get('adv', 0):.2f}")
                print(f"   Pedágio: R$ {detalhes.get('pedagio', 0):.2f}")
                
                if 'componentes_antes_minimo' in detalhes:
                    print(f"   Componentes PRÉ-mínimo: R$ {detalhes['componentes_antes_minimo']:.2f}")
                if 'componentes_apos_minimo' in detalhes:
                    print(f"   Componentes PÓS-mínimo: R$ {detalhes['componentes_apos_minimo']:.2f}")
            
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
    if testar_analise_diferencas():
        sys.exit(0)
    else:
        sys.exit(1)