#!/usr/bin/env python
"""
Script para gerar modelo Excel de importação de Cadastro de Palletização
com os novos campos de subcategorias
"""

import pandas as pd
from datetime import datetime

# Criar dados de exemplo
dados_exemplo = {
    'Cód.Produto': ['1001', '1002', '1003', '1004', '1005'],
    'Descrição Produto': [
        'PALMITO PUPUNHA INTEIRO 300G',
        'AZEITONA VERDE S/C 200G',
        'MOLHO DE TOMATE TRADICIONAL 340G',
        'ÓLEO MISTO 900ML',
        'CEBOLINHA EM CONSERVA 150G'
    ],
    'PALLETIZACAO': [144, 120, 180, 96, 200],
    'PESO BRUTO': [0.35, 0.22, 0.38, 0.95, 0.17],
    'altura_cm': [15, 10, 12, 25, 8],
    'largura_cm': [8, 7, 8, 10, 6],
    'comprimento_cm': [8, 7, 8, 10, 6],
    # Novos campos de subcategorias
    'CATEGORIA': ['PALMITO', 'CONSERVAS', 'MOLHOS', 'ÓLEOS'],
    'MATERIA_PRIMA': ['PALMITO', 'AZ VSC', 'OL. MISTO', 'CEBOLINHA'],
    'EMBALAGEM': ['VD 12X500', 'BD 6X2', 'GARRAFA 12X500', 'POUCH 18X150'],
    'LINHA_PRODUCAO': ['1106', '1101 1/6', 'LF', 'VALE SUL']
}

# Criar DataFrame
df = pd.DataFrame(dados_exemplo)

# Criar arquivo Excel com múltiplas abas
with pd.ExcelWriter('modelo_palletizacao_com_subcategorias.xlsx', engine='openpyxl') as writer:
    # Aba com dados de exemplo
    df.to_excel(writer, sheet_name='Dados', index=False)
    
    # Aba com instruções
    instrucoes_df = pd.DataFrame({
        'Instruções para Importação': [
            '1. COLUNAS OBRIGATÓRIAS:',
            '   - Cód.Produto: Código único do produto',
            '   - Descrição Produto: Nome/descrição do produto',
            '   - PALLETIZACAO: Quantidade de unidades por pallet',
            '   - PESO BRUTO: Peso unitário em kg',
            '',
            '2. COLUNAS OPCIONAIS DE DIMENSÕES:',
            '   - altura_cm: Altura em centímetros',
            '   - largura_cm: Largura em centímetros',
            '   - comprimento_cm: Comprimento em centímetros',
            '',
            '3. NOVAS COLUNAS DE SUBCATEGORIAS (OPCIONAIS):',
            '   - CATEGORIA: PALMITO / CONSERVAS / MOLHOS / ÓLEOS',
            '   - MATERIA_PRIMA: AZ VSC / AZ VF / CEBOLINHA / OL. MISTO...',
            '   - EMBALAGEM: BD 6X2 / VD 12X500 / GARRAFA 12X500 / PET 12X200 / POUCH 18X150...',
            '   - LINHA_PRODUCAO: 1106 / 1101 1/6 / LF / VALE SUL...',
            '',
            '4. COMPORTAMENTO:',
            '   - Se o produto já existe, será ATUALIZADO',
            '   - Se não existe, será CRIADO',
            '',
            '5. SIGNIFICADO DAS ABREVIAÇÕES:',
            '   MATÉRIA-PRIMA:',
            '   - AZ = Azeitona',
            '   - VSC = Verde Sem Caroço',
            '   - VF = Verde Fatiada',
            '   - OL = Óleo',
            '',
            '   EMBALAGEM:',
            '   - BD = Balde',
            '   - VD = Vidro',
            '   - PET = Frasco PET',
            '',
            '   LINHA DE PRODUÇÃO:',
            '   - LF = La Famiglia (empresa do grupo)',
            '   - VALE SUL = Produto terceirizado',
            '   - 1/6 = Pode produzir na máquina 1 ou 6',
            '',
            f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
        ]
    })
    instrucoes_df.to_excel(writer, sheet_name='Instruções', index=False)
    
    # Aba com valores válidos
    valores_validos = pd.DataFrame({
        'CATEGORIA': ['PALMITO', 'CONSERVAS', 'MOLHOS', 'ÓLEOS', '', ''],
        'MATERIA_PRIMA': ['AZ VSC', 'AZ VF', 'CEBOLINHA', 'OL. MISTO', 'PALMITO', 'TOMATE'],
        'EMBALAGEM': ['BD 6X2', 'VD 12X500', 'GARRAFA 12X500', 'PET 12X200', 'POUCH 18X150', ''],
        'LINHA_PRODUCAO': ['1106', '1101 1/6', 'LF', 'VALE SUL', '', '']
    })
    valores_validos.to_excel(writer, sheet_name='Valores Válidos', index=False)

print("✅ Modelo Excel criado: modelo_palletizacao_com_subcategorias.xlsx")
print("\nO arquivo contém:")
print("1. Aba 'Dados' - Exemplo de dados para importação")
print("2. Aba 'Instruções' - Guia completo de importação")
print("3. Aba 'Valores Válidos' - Lista de valores aceitos para cada subcategoria")