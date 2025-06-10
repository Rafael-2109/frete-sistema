#!/usr/bin/env python
"""
Script para Migrar Templates para Timezone Brasileiro
=====================================================

Este script encontra e substitui usos de .strftime() por filtros de timezone brasileiro.
"""

import os
import re
from pathlib import Path

def migrar_templates():
    """Migra templates para usar timezone brasileiro"""
    
    print("🔄 === MIGRAÇÃO DE TEMPLATES PARA TIMEZONE BRASILEIRO ===\n")
    
    # Padrões para encontrar e substituir
    padroes = [
        # Data e hora
        {
            'buscar': r'(\w+)\.strftime\([\'"]%d/%m/%Y %H:%M[:\%S]*[\'"][)]',
            'substituir': r'\1 | formatar_data_hora_brasil',
            'descricao': 'Data e hora completa'
        },
        # Só data
        {
            'buscar': r'(\w+)\.strftime\([\'"]%d/%m/%Y[\'"][)]',
            'substituir': r'\1 | formatar_data_segura',
            'descricao': 'Só data'
        },
        # Só hora
        {
            'buscar': r'(\w+)\.strftime\([\'"]%H:%M[:\%S]*[\'"][)]',
            'substituir': r'\1 | formatar_hora_brasil',
            'descricao': 'Só hora'
        },
        # Formatos diversos
        {
            'buscar': r'(\w+)\.strftime\([\'"]([^\'\"]*)[\'"][)]',
            'substituir': r'\1 | formatar_data_hora_brasil',
            'descricao': 'Outros formatos'
        }
    ]
    
    # Diretório de templates
    templates_dir = Path('app/templates')
    
    if not templates_dir.exists():
        print("❌ Diretório de templates não encontrado!")
        return
    
    arquivos_alterados = []
    total_substituicoes = 0
    
    # Processa todos os arquivos .html
    for arquivo_html in templates_dir.rglob('*.html'):
        print(f"📄 Processando: {arquivo_html}")
        
        try:
            with open(arquivo_html, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            conteudo_original = conteudo
            substituicoes_arquivo = 0
            
            # Aplica cada padrão
            for padrao in padroes:
                matches = re.findall(padrao['buscar'], conteudo)
                if matches:
                    print(f"  🔍 Encontrado {len(matches)} ocorrências de {padrao['descricao']}")
                    conteudo = re.sub(padrao['buscar'], padrao['substituir'], conteudo)
                    substituicoes_arquivo += len(matches)
            
            # Salva se houve mudanças
            if conteudo != conteudo_original:
                with open(arquivo_html, 'w', encoding='utf-8') as f:
                    f.write(conteudo)
                
                arquivos_alterados.append(str(arquivo_html))
                total_substituicoes += substituicoes_arquivo
                print(f"  ✅ {substituicoes_arquivo} substituições realizadas")
            else:
                print(f"  ℹ️ Nenhuma alteração necessária")
                
        except Exception as e:
            print(f"  ❌ Erro ao processar {arquivo_html}: {e}")
    
    # Relatório final
    print(f"\n📊 === RELATÓRIO FINAL ===")
    print(f"📄 Arquivos processados: {len(list(templates_dir.rglob('*.html')))}")
    print(f"✅ Arquivos alterados: {len(arquivos_alterados)}")
    print(f"🔄 Total de substituições: {total_substituicoes}")
    
    if arquivos_alterados:
        print(f"\n📋 Arquivos alterados:")
        for arquivo in arquivos_alterados:
            print(f"   • {arquivo}")
        
        print(f"\n🎯 PRÓXIMOS PASSOS:")
        print(f"1. Testar os templates alterados")
        print(f"2. Verificar se as datas estão no horário brasileiro")
        print(f"3. Fazer commit das alterações")
        print(f"4. Deploy para produção")
    else:
        print(f"\nℹ️ Nenhum template precisou ser alterado.")
    
    print(f"\n✅ MIGRAÇÃO CONCLUÍDA! 🇧🇷")

def verificar_templates():
    """Verifica quantos templates ainda usam .strftime()"""
    
    print("🔍 === VERIFICAÇÃO DE TEMPLATES ===\n")
    
    templates_dir = Path('app/templates')
    padrao_strftime = r'\.strftime\('
    
    arquivos_com_strftime = []
    total_ocorrencias = 0
    
    for arquivo_html in templates_dir.rglob('*.html'):
        try:
            with open(arquivo_html, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            matches = re.findall(padrao_strftime, conteudo)
            if matches:
                arquivos_com_strftime.append((str(arquivo_html), len(matches)))
                total_ocorrencias += len(matches)
                
        except Exception as e:
            print(f"❌ Erro ao ler {arquivo_html}: {e}")
    
    if arquivos_com_strftime:
        print(f"⚠️ Encontrados {total_ocorrencias} usos de .strftime() em {len(arquivos_com_strftime)} arquivos:")
        for arquivo, count in arquivos_com_strftime:
            print(f"   • {arquivo}: {count} ocorrências")
        print(f"\n💡 Execute: python migrar_templates_timezone.py para migrar automaticamente")
    else:
        print(f"✅ Nenhum uso de .strftime() encontrado! Todos os templates estão usando timezone brasileiro.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "verificar":
        verificar_templates()
    else:
        migrar_templates() 