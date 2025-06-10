#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Criar Modelo Excel para Importação de Cidades
==============================================

Este script cria um arquivo Excel modelo para importação de cidades.
"""

import pandas as pd
from datetime import datetime

def criar_modelo_excel():
    """Cria arquivo Excel modelo para importação de cidades"""
    
    # Dados de exemplo
    dados_exemplo = [
        {
            'CIDADE': 'Goiânia',
            'UF': 'GO',
            'IBGE': '5208707',
            'ICMS': '7,00%',
            'ISS': 'NÃO',
            'MICRORREGIAO': 'Goiânia',
            'MESORREGIAO': 'Centro Goiano'
        },
        {
            'CIDADE': 'Anápolis',
            'UF': 'GO',
            'IBGE': '5201108',
            'ICMS': '7,00%',
            'ISS': 'NÃO',
            'MICRORREGIAO': 'Anápolis',
            'MESORREGIAO': 'Centro Goiano'
        },
        {
            'CIDADE': 'São Paulo',
            'UF': 'SP',
            'IBGE': '3550308',
            'ICMS': '12,00%',
            'ISS': 'SIM',
            'MICRORREGIAO': 'São Paulo',
            'MESORREGIAO': 'Metropolitana de São Paulo'
        },
        {
            'CIDADE': 'Rio de Janeiro',
            'UF': 'RJ',
            'IBGE': '3304557',
            'ICMS': '18,00%',
            'ISS': 'SIM',
            'MICRORREGIAO': 'Rio de Janeiro',
            'MESORREGIAO': 'Metropolitana do Rio de Janeiro'
        },
        {
            'CIDADE': 'Brasília',
            'UF': 'DF',
            'IBGE': '5300108',
            'ICMS': '18,00%',
            'ISS': 'SIM',
            'MICRORREGIAO': 'Brasília',
            'MESORREGIAO': 'Distrito Federal'
        }
    ]
    
    # Criar DataFrame
    df = pd.DataFrame(dados_exemplo)
    
    # Salvar Excel
    nome_arquivo = f"modelo_cidades_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
        # Aba com dados de exemplo
        df.to_excel(writer, sheet_name='Dados de Exemplo', index=False)
        
        # Aba com template vazio
        df_vazio = pd.DataFrame(columns=df.columns)
        df_vazio.to_excel(writer, sheet_name='Template Vazio', index=False)
        
        # Aba com instruções
        instrucoes = pd.DataFrame({
            'INSTRUÇÕES PARA IMPORTAÇÃO DE CIDADES': [
                '',
                '📋 COLUNAS OBRIGATÓRIAS:',
                '• CIDADE - Nome da cidade',
                '• UF - Estado (2 letras)',
                '• IBGE - Código IBGE da cidade',
                '• ICMS - Alíquota ICMS (ex: 7,00% ou 0.07)',
                '',
                '📋 COLUNAS OPCIONAIS:',
                '• ISS - Se substitui ICMS por ISS (SIM/NÃO)',
                '• MICRORREGIAO - Microrregião IBGE',
                '• MESORREGIAO - Mesorregião IBGE',
                '',
                '💡 DICAS:',
                '• Use a aba "Template Vazio" para suas cidades',
                '• ICMS pode ser em % (7,00%) ou decimal (0.07)',
                '• ISS aceita: SIM, S, NÃO, N',
                '• UF sempre em maiúscula',
                '',
                '⚙️ COMO IMPORTAR:',
                '',
                '1️⃣ OPÇÃO 1 - Script Standalone:',
                '   python importar_cidades_unico.py arquivo.xlsx',
                '',
                '2️⃣ OPÇÃO 2 - Comando Flask:',
                '   flask importar-cidades-cli arquivo.xlsx',
                '',
                '✅ VERIFICAÇÃO:',
                '• O script verifica duplicatas',
                '• Pula linhas com erro',
                '• Mostra relatório detalhado',
                '',
                '🔍 EXEMPLO DE USO:',
                '   python importar_cidades_unico.py modelo_cidades_20241231.xlsx'
            ]
        })
        instrucoes.to_excel(writer, sheet_name='Instruções', index=False)
    
    print(f"✅ Modelo Excel criado: {nome_arquivo}")
    print()
    print("📋 Estrutura do arquivo:")
    print("• Aba 'Dados de Exemplo' - Exemplos de cidades")
    print("• Aba 'Template Vazio' - Template para suas cidades")
    print("• Aba 'Instruções' - Manual completo")
    print()
    print("🎯 Próximos passos:")
    print("1. Abra o arquivo Excel")
    print("2. Use a aba 'Template Vazio'")
    print("3. Preencha com suas cidades")
    print("4. Execute: python importar_cidades_unico.py arquivo.xlsx")
    
    return nome_arquivo

if __name__ == "__main__":
    criar_modelo_excel() 