#!/usr/bin/env python3
"""
Script para atualizar formatação de valores nos templates MotoChefe
Converte formato americano (%.2f|format) para formato brasileiro (valor_br)
Data: 2025-01-10
"""

import os
import re
from pathlib import Path

# Diretório base dos templates motochefe
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / 'app' / 'templates' / 'motochefe'

# Padrões de substituição
PADROES = [
    # Padrão 1: {{ "%.2f"|format(variavel) }}  →  {{ variavel|valor_br }}
    (r'\{\{\s*"%.2f"\|format\(([^)]+?)\)\s*\}\}', r'{{ \1|valor_br }}'),

    # Padrão 2: {{ "%.0f"|format(variavel) }}  →  {{ variavel|valor_br(0) }}
    (r'\{\{\s*"%.0f"\|format\(([^)]+?)\)\s*\}\}', r'{{ \1|valor_br(0) }}'),

    # Padrão 3: {{ "%02d"|format(variavel) }} → MANTER (não é valor monetário)
    # NÃO substituir padrões de data/número que não são monetários
]

def processar_arquivo(caminho):
    """Processa um arquivo HTML substituindo os padrões"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        conteudo_original = conteudo
        substituicoes = 0

        for padrao, substituicao in PADROES:
            conteudo, n = re.subn(padrao, substituicao, conteudo)
            substituicoes += n

        if substituicoes > 0:
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(conteudo)
            return True, substituicoes

        return False, 0

    except Exception as e:
        print(f"❌ Erro ao processar {caminho}: {e}")
        return False, 0

def main():
    """Função principal"""
    print("🔧 Iniciando atualização de formatação de valores...\n")

    arquivos_processados = 0
    total_substituicoes = 0

    # Percorrer todos os arquivos .html no diretório motochefe
    for arquivo in TEMPLATES_DIR.rglob('*.html'):
        modificado, n_subs = processar_arquivo(arquivo)

        if modificado:
            arquivos_processados += 1
            total_substituicoes += n_subs
            caminho_relativo = arquivo.relative_to(BASE_DIR)
            print(f"✅ {caminho_relativo}: {n_subs} substituições")

    print(f"\n📊 RESUMO:")
    print(f"   Arquivos modificados: {arquivos_processados}")
    print(f"   Total de substituições: {total_substituicoes}")
    print(f"\n✅ Processo concluído!")

if __name__ == '__main__':
    main()
