"""
Script para testar o mapeamento correto dos campos do faturamento
==================================================================

Este script valida se os campos estão sendo mapeados corretamente do Odoo:
- numero_nf = invoice_line_ids/x_studio_nf_e (ou name como fallback)
- cod_produto = product_id/code (não default_code)
- valor_produto_faturado = l10n_br_total_nfe (ou price_total como fallback)

Autor: Sistema de Fretes
Data: 2025-07-15
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from app.odoo.services.faturamento_service import FaturamentoService

def testar_mapeamento_faturamento():
    """Testa o mapeamento dos campos do faturamento"""
    
    print("=" * 80)
    print("TESTE DE MAPEAMENTO DO FATURAMENTO")
    print("=" * 80)
    
    try:
        # Criar serviço
        service = FaturamentoService()
        
        # Buscar apenas 5 registros para teste
        print("\n🔍 Buscando dados do faturamento (limite: 5 registros)...")
        resultado = service.obter_faturamento_otimizado(
            usar_filtro_postado=True,
            limite=5
        )
        
        if not resultado['sucesso']:
            print(f"❌ Erro: {resultado.get('erro')}")
            return
        
        dados = resultado.get('dados', [])
        
        if not dados:
            print("⚠️ Nenhum dado encontrado")
            return
        
        print(f"\n✅ {len(dados)} registros encontrados para análise")
        
        # Validar mapeamento de cada registro
        for i, item in enumerate(dados, 1):
            print(f"\n📋 REGISTRO {i}:")
            print("-" * 40)
            
            # Campos críticos para validar
            campos_criticos = {
                'numero_nf': 'Número NF (x_studio_nf_e ou name)',
                'data_fatura': 'Data da Fatura',
                'cnpj_cliente': 'CNPJ Cliente',
                'nome_cliente': 'Nome Cliente',
                'municipio': 'Município',
                'estado': 'Estado (UF)',
                'vendedor': 'Vendedor',
                'incoterm': 'Incoterm',
                'cod_produto': 'Código Produto (code)',
                'nome_produto': 'Nome Produto',
                'qtd_produto_faturado': 'Quantidade',
                'preco_produto_faturado': 'Preço Unitário',
                'valor_produto_faturado': 'Valor Total (l10n_br_total_nfe)',
                'peso_unitario_produto': 'Peso Unitário',
                'peso_total': 'Peso Total',
                'origem': 'Origem (invoice_origin)',
                'status_nf': 'Status'
            }
            
            for campo, descricao in campos_criticos.items():
                valor = item.get(campo)
                
                # Verificar tipo de dado
                tipo = type(valor).__name__
                
                # Validações específicas
                if campo == 'numero_nf':
                    # Deve ter valor
                    if valor:
                        print(f"  ✅ {descricao}: '{valor}' ({tipo})")
                    else:
                        print(f"  ❌ {descricao}: VAZIO!")
                
                elif campo == 'cod_produto':
                    # Verificar se está vindo o código correto
                    if valor:
                        print(f"  ✅ {descricao}: '{valor}' ({tipo})")
                    else:
                        print(f"  ⚠️ {descricao}: VAZIO - verificar se produto tem 'code'")
                
                elif campo == 'estado':
                    # Deve ter apenas 2 caracteres
                    if valor and len(str(valor)) > 2:
                        print(f"  ⚠️ {descricao}: '{valor}' [MAIS DE 2 CARACTERES!]")
                    elif isinstance(valor, (int, float)):
                        print(f"  ❌ {descricao}: {valor} [ERRO: É NÚMERO!]")
                    else:
                        print(f"  ✅ {descricao}: '{valor}' ({tipo})")
                
                elif campo == 'incoterm':
                    # Deve ser apenas o código, não a descrição completa
                    if valor and len(str(valor)) > 20:
                        print(f"  ⚠️ {descricao}: '{valor}' [MUITO LONGO!]")
                    else:
                        print(f"  ✅ {descricao}: '{valor}' ({tipo})")
                
                elif campo == 'valor_produto_faturado':
                    # Deve ser numérico
                    if isinstance(valor, (int, float)) and valor > 0:
                        print(f"  ✅ {descricao}: {valor:.2f} ({tipo})")
                    else:
                        print(f"  ⚠️ {descricao}: {valor} ({tipo})")
                
                elif campo == 'peso_total':
                    # Campo calculado
                    qtd = item.get('qtd_produto_faturado', 0)
                    peso_unit = item.get('peso_unitario_produto', 0)
                    esperado = qtd * peso_unit
                    if abs(valor - esperado) < 0.01:  # Tolerância para float
                        print(f"  ✅ {descricao}: {valor:.3f} (calculado: {qtd} x {peso_unit})")
                    else:
                        print(f"  ⚠️ {descricao}: {valor:.3f} (esperado: {esperado:.3f})")
                
                else:
                    if valor not in [None, '', 0, 0.0]:
                        print(f"  ✅ {descricao}: '{valor}' ({tipo})")
                    else:
                        print(f"  ⚠️ {descricao}: VAZIO/ZERO")
        
        # Estatísticas finais
        print("\n" + "=" * 80)
        print("RESUMO DO TESTE:")
        print(f"• Total de registros analisados: {len(dados)}")
        print(f"• Campos críticos validados: {len(campos_criticos)}")
        
        # Verificar problemas comuns
        problemas = []
        for item in dados:
            if not item.get('numero_nf'):
                problemas.append("numero_nf vazio")
            if not item.get('cod_produto'):
                problemas.append("cod_produto vazio")
            if isinstance(item.get('estado'), (int, float)):
                problemas.append("estado é número")
        
        if problemas:
            print("\n⚠️ PROBLEMAS ENCONTRADOS:")
            for p in set(problemas):
                print(f"  • {p}")
        else:
            print("\n✅ Nenhum problema crítico encontrado!")
        
        # Mostrar estatísticas da consulta
        stats = resultado.get('estatisticas', {})
        if stats:
            print(f"\n📊 ESTATÍSTICAS DA CONSULTA:")
            print(f"  • Queries executadas: {stats.get('queries_executadas', 'N/A')}")
            print(f"  • Linhas brutas Odoo: {stats.get('linhas_brutas', 'N/A')}")
            print(f"  • Linhas processadas: {stats.get('total_linhas', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    testar_mapeamento_faturamento() 