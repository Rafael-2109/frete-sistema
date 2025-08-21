#!/usr/bin/env python
"""
Script para limpar caracteres Unicode problemáticos do arquivo
"""

import re

# Ler o arquivo
with open('app/portal/atacadao/playwright_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Mapeamento de substituições
replacements = {
    '✅': '',
    '❌': '',
    '🔍': '',
    '🚀': '',
    '✋': '',
    'é': 'e',
    'É': 'E',
    'ê': 'e',
    'Ê': 'E',
    'á': 'a',
    'Á': 'A',
    'à': 'a',
    'À': 'A',
    'ã': 'a',
    'Ã': 'A',
    'â': 'a',
    'Â': 'A',
    'ó': 'o',
    'Ó': 'O',
    'õ': 'o',
    'Õ': 'O',
    'ô': 'o',
    'Ô': 'O',
    'ú': 'u',
    'Ú': 'U',
    'ü': 'u',
    'Ü': 'U',
    'í': 'i',
    'Í': 'I',
    'ç': 'c',
    'Ç': 'C',
    'º': '',
    'ª': '',
    '°': '',
    '\u2705': '',  # Check mark
    '\u274c': '',  # X mark
    '\u1f50d': '',  # Magnifying glass
    '\u1f680': '',  # Rocket
    '\u270b': '',  # Hand
}

# Aplicar substituições
for old, new in replacements.items():
    content = content.replace(old, new)

# Salvar o arquivo limpo
with open('app/portal/atacadao/playwright_client.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Arquivo limpo com sucesso!")