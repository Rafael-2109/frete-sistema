#!/usr/bin/env python3
"""
Script para testar campos que excedem limites na carteira do Odoo
Identifica campos longos e mostra dados reais dos primeiros 10 registros
"""

import os
import sys
sys.path.append('.')

from app import create_app
from app.odoo.services.carteira_service import CarteiraService
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analisar_campos_longos():
    """
    Analisa campos que excedem os limites definidos no banco
    """
    print("🔍 ANÁLISE DE CAMPOS LONGOS NA CARTEIRA ODOO")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        try:
            service = CarteiraService()
            
            # Buscar dados limitados para análise
            print("📊 Buscando dados da carteira do Odoo (limite 10)...")
            resultado = service.obter_carteira_otimizada(
                usar_filtro_pendente=True,
                limite=10
            )
            
            if not resultado['sucesso']:
                print(f"❌ Erro: {resultado.get('erro')}")
                return
            
            dados = resultado.get('dados', [])
            print(f"✅ {len(dados)} registros encontrados\n")
            
            # Definir limites dos campos
            limites_campos = {
                # 2 caracteres
                'estado': 2,
                'cod_uf': 2,
                
                # 10 caracteres  
                'cliente_nec_agendamento': 10,
                'cep_endereco_ent': 10,
                
                # 20 caracteres
                'unid_medida_produto': 20,
                'incoterm': 20,
                'cnpj_cpf': 20,
                'cnpj_endereco_ent': 20,
                'endereco_ent': 20,
                'telefone_endereco_ent': 20,
                
                # 50 caracteres
                'num_pedido': 50,
                'cod_produto': 50,
                'status_pedido': 50,
                'protocolo': 50,
                'metodo_entrega_pedido': 50,
                
                # 100 caracteres
                'pedido_cliente': 100,
                'raz_social_red': 100,
                'municipio': 100,
                'vendedor': 100,
                'equipe_vendas': 100,
                'embalagem_produto': 100,
                'materia_prima_produto': 100,
                'categoria_produto': 100,
                'cond_pgto_pedido': 100,
                'forma_pgto_pedido': 100,
                'nome_cidade': 100,
                'bairro_endereco_ent': 100,
                'roteirizacao': 100,
                'created_by': 100,
                'updated_by': 100
            }
            
            # Analisar cada registro
            campos_problematicos = {}
            
            for i, registro in enumerate(dados):
                print(f"📋 REGISTRO {i+1}:")
                print(f"   Pedido: {registro.get('num_pedido', 'N/A')}")
                print(f"   Produto: {registro.get('cod_produto', 'N/A')}")
                print(f"   Cliente: {registro.get('raz_social', 'N/A')[:50]}...")
                
                # Verificar cada campo com limite
                for campo, limite in limites_campos.items():
                    valor = registro.get(campo)
                    if valor and isinstance(valor, str) and len(valor) > limite:
                        # Registrar campo problemático
                        if campo not in campos_problematicos:
                            campos_problematicos[campo] = []
                        
                        campos_problematicos[campo].append({
                            'registro': i+1,
                            'valor': valor,
                            'tamanho': len(valor),
                            'limite': limite,
                            'excesso': len(valor) - limite
                        })
                        
                        print(f"   ⚠️  {campo}: {len(valor)} chars (limite {limite}) - '{valor}'")
                
                print()
            
            # Resumo dos problemas
            print("🚨 RESUMO DOS CAMPOS PROBLEMÁTICOS:")
            print("=" * 60)
            
            if not campos_problematicos:
                print("✅ Nenhum campo excede os limites definidos!")
            else:
                for campo, problemas in campos_problematicos.items():
                    print(f"\n🔴 Campo: {campo}")
                    print(f"   Limite: {problemas[0]['limite']} caracteres")
                    print(f"   Ocorrências: {len(problemas)}")
                    
                    for problema in problemas:
                        print(f"   📍 Registro {problema['registro']}: {problema['tamanho']} chars (+{problema['excesso']})")
                        print(f"      Valor: '{problema['valor'][:100]}{'...' if len(problema['valor']) > 100 else ''}'")
            
            # Mostrar dados detalhados dos primeiros registros
            print("\n" + "=" * 60)
            print("📊 DADOS DETALHADOS DOS PRIMEIROS 3 REGISTROS:")
            print("=" * 60)
            
            for i, registro in enumerate(dados[:3]):
                print(f"\n🔸 REGISTRO {i+1}:")
                
                # Campos principais
                principais = [
                    'num_pedido', 'cod_produto', 'pedido_cliente', 'status_pedido',
                    'cnpj_cpf', 'raz_social', 'municipio', 'estado', 'vendedor',
                    'nome_produto', 'unid_medida_produto', 'qtd_produto_pedido',
                    'qtd_saldo_produto_pedido', 'preco_produto_pedido'
                ]
                
                for campo in principais:
                    valor = registro.get(campo, 'N/A')
                    if isinstance(valor, str):
                        tamanho = f" ({len(valor)} chars)" if len(valor) > 20 else ""
                        print(f"   {campo:25}: {str(valor)[:80]}{tamanho}")
                    else:
                        print(f"   {campo:25}: {valor}")
                
                # Endereço de entrega
                endereco_campos = [
                    'empresa_endereco_ent', 'cnpj_endereco_ent', 'cep_endereco_ent',
                    'nome_cidade', 'cod_uf', 'bairro_endereco_ent', 'rua_endereco_ent',
                    'endereco_ent', 'telefone_endereco_ent'
                ]
                
                print("   📍 ENDEREÇO DE ENTREGA:")
                for campo in endereco_campos:
                    valor = registro.get(campo, 'N/A')
                    if isinstance(valor, str) and len(valor) > 10:
                        tamanho = f" ({len(valor)} chars)"
                    else:
                        tamanho = ""
                    print(f"      {campo:20}: {str(valor)[:50]}{tamanho}")
            
            print("\n" + "=" * 60)
            print("✅ ANÁLISE CONCLUÍDA")
            
        except Exception as e:
            print(f"❌ Erro durante análise: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    analisar_campos_longos() 