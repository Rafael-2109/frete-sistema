#!/usr/bin/env python
"""Script para testar o template analise_diferencas.html"""

from jinja2 import Template, Environment, FileSystemLoader
import os
import json

# Configurar o Jinja2
env = Environment(loader=FileSystemLoader('app/templates'))

# Tentar carregar o template
try:
    template = env.get_template('fretes/analise_diferencas.html')
    print("✅ Template carregado com sucesso!")
    
    # Dados de teste simulados
    test_data = {
        'frete': {
            'id': 1,
            'peso_considerado': 1000,
            'peso_total': 1000,
            'valor_total_nfs': 50000,
            'valor_cte': 2000,
            'nome_cliente': 'Cliente Teste',
            'cnpj_cliente': '00.000.000/0001-00',
            'modalidade': 'TRUCK',
            'transportadora': {
                'razao_social': 'Transportadora Teste'
            },
            'embarque': {
                'numero': 123
            }
        },
        'componentes': [
            {
                'nome': 'Frete por Peso',
                'tipo': 'valor',
                'input_index': 0,
                'valor_calculado': 500,
                'valor_tabela': 'R$ 0.50/kg',
                'valor_usado': '1000 kg',
                'formula': '1000 × 0.50',
                'unidade': 'R$'
            },
            {
                'nome': 'GRIS',
                'tipo': 'valor',
                'input_index': 1,
                'valor_calculado': 100,
                'valor_tabela': '0.20%',
                'valor_usado': 'R$ 50000',
                'formula': '50000 × 0.20%',
                'unidade': 'R$'
            }
        ],
        'resumo_cotacao': {
            'total_liquido': 1500,
            'total_bruto': 1800,
            'percentual_icms': 0.12,
            'valor_icms': 300
        },
        'tabela_dados': {
            'nome_tabela': 'Tabela SP-RJ'
        },
        'configuracao_info': {},
        'transportadora_config': {}
    }
    
    # Renderizar template
    html = template.render(**test_data)
    
    # Verificar se tem erros óbvios no JavaScript
    if '{{' in html and '}}' in html:
        # Contar variáveis Jinja2 não processadas
        import re
        unprocessed = re.findall(r'\{\{.*?\}\}', html)
        if unprocessed:
            print(f"⚠️  AVISO: {len(unprocessed)} variáveis Jinja2 não processadas encontradas")
            for var in unprocessed[:5]:
                print(f"   - {var}")
    
    # Salvar HTML para inspeção
    with open('test_output.html', 'w') as f:
        f.write(html)
    
    print("✅ Template renderizado com sucesso!")
    print("📄 HTML salvo em test_output.html")
    
    # Verificar se o JavaScript está correto
    if 'const pesoConsiderado =' in html:
        print("✅ Variáveis JavaScript encontradas")
    
    if '.includes(' in html:
        print("✅ Método includes() está sendo usado")
        
    # Verificar duplicação de variáveis
    js_section = html[html.find('<script'):html.find('</script>')]
    if js_section.count('const valorMercadoria =') > 1:
        print("❌ ERRO: Variável valorMercadoria declarada múltiplas vezes!")
    else:
        print("✅ Sem duplicação de variáveis")
    
except Exception as e:
    print(f"❌ Erro ao processar template: {e}")
    import traceback
    traceback.print_exc()