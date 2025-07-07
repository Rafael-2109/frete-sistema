#!/usr/bin/env python3
"""
📊 COMPARAÇÃO ESTRUTURAS CLAUDE AI
Script para comparar estrutura original vs nova
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple

def listar_arquivos_python(diretorio: str) -> List[Tuple[str, int, int]]:
    """Lista todos os arquivos Python com tamanho e linhas"""
    arquivos = []
    
    if not os.path.exists(diretorio):
        return arquivos
    
    for root, dirs, files in os.walk(diretorio):
        for file in files:
            if file.endswith('.py'):
                caminho_completo = os.path.join(root, file)
                try:
                    # Tamanho em bytes
                    tamanho = os.path.getsize(caminho_completo)
                    
                    # Número de linhas
                    with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
                        linhas = len(f.readlines())
                    
                    # Caminho relativo
                    caminho_relativo = os.path.relpath(caminho_completo, diretorio)
                    
                    arquivos.append((caminho_relativo, tamanho, linhas))
                except Exception as e:
                    print(f"Erro ao processar {caminho_completo}: {e}")
    
    return sorted(arquivos)

def formatar_tamanho(bytes_size: int) -> str:
    """Formata tamanho em bytes para formato legível"""
    if bytes_size >= 1024*1024:
        return f"{bytes_size/(1024*1024):.1f}MB"
    elif bytes_size >= 1024:
        return f"{bytes_size/1024:.1f}KB"
    else:
        return f"{bytes_size}B"

def comparar_estruturas():
    """Compara as estruturas original e nova"""
    print("📊 COMPARAÇÃO DETALHADA - ESTRUTURAS CLAUDE AI")
    print("=" * 80)
    
    # Diretórios a comparar
    dir_original = "app/claude_ai"
    dir_novo = "app/claude_ai_novo"
    dir_backup = "app/claude_ai_backup_20250706_221126"
    
    # Listar arquivos de cada estrutura
    print("🔍 LISTANDO ARQUIVOS...")
    arquivos_original = listar_arquivos_python(dir_original)
    arquivos_novo = listar_arquivos_python(dir_novo)
    arquivos_backup = listar_arquivos_python(dir_backup)
    
    print(f"\n📁 ESTRUTURA ORIGINAL ({dir_original}):")
    print("-" * 50)
    total_linhas_original = 0
    total_tamanho_original = 0
    
    for arquivo, tamanho, linhas in arquivos_original:
        print(f"  {arquivo:<40} {formatar_tamanho(tamanho):>8} {linhas:>6} linhas")
        total_linhas_original += linhas
        total_tamanho_original += tamanho
    
    print(f"\n📊 RESUMO ORIGINAL:")
    print(f"  Total de arquivos: {len(arquivos_original)}")
    print(f"  Total de linhas: {total_linhas_original:,}")
    print(f"  Tamanho total: {formatar_tamanho(total_tamanho_original)}")
    
    print(f"\n📁 NOVA ESTRUTURA ({dir_novo}):")
    print("-" * 50)
    total_linhas_novo = 0
    total_tamanho_novo = 0
    
    for arquivo, tamanho, linhas in arquivos_novo:
        print(f"  {arquivo:<40} {formatar_tamanho(tamanho):>8} {linhas:>6} linhas")
        total_linhas_novo += linhas
        total_tamanho_novo += tamanho
    
    print(f"\n📊 RESUMO NOVA ESTRUTURA:")
    print(f"  Total de arquivos: {len(arquivos_novo)}")
    print(f"  Total de linhas: {total_linhas_novo:,}")
    print(f"  Tamanho total: {formatar_tamanho(total_tamanho_novo)}")
    
    # Verificar integridade do backup
    print(f"\n💾 VERIFICAÇÃO DO BACKUP:")
    print("-" * 50)
    if len(arquivos_backup) == len(arquivos_original):
        print("✅ Backup contém o mesmo número de arquivos que o original")
    else:
        print(f"⚠️ Backup tem {len(arquivos_backup)} arquivos, original tem {len(arquivos_original)}")
    
    # Análise de migração
    print(f"\n🔄 ANÁLISE DE MIGRAÇÃO:")
    print("-" * 50)
    
    # Criar sets com nomes de arquivos para comparação
    nomes_original = {os.path.basename(arq[0]) for arq in arquivos_original}
    nomes_novo = {os.path.basename(arq[0]) for arq in arquivos_novo}
    
    # Arquivos migrados (com mesmo nome)
    migrados = nomes_original.intersection(nomes_novo)
    
    # Arquivos não migrados
    nao_migrados = nomes_original - nomes_novo
    
    # Arquivos novos
    novos = nomes_novo - nomes_original
    
    print(f"📋 ARQUIVOS MIGRADOS ({len(migrados)}):")
    for nome in sorted(migrados):
        print(f"  ✅ {nome}")
    
    print(f"\n❌ ARQUIVOS NÃO MIGRADOS ({len(nao_migrados)}):")
    for nome in sorted(nao_migrados):
        # Encontrar arquivo original para mostrar tamanho
        for arq, tam, lin in arquivos_original:
            if os.path.basename(arq) == nome:
                print(f"  📄 {nome:<40} {formatar_tamanho(tam):>8} {lin:>6} linhas")
                break
    
    print(f"\n🆕 ARQUIVOS NOVOS CRIADOS ({len(novos)}):")
    for nome in sorted(novos):
        # Encontrar arquivo novo para mostrar tamanho
        for arq, tam, lin in arquivos_novo:
            if os.path.basename(arq) == nome:
                print(f"  ✨ {nome:<40} {formatar_tamanho(tam):>8} {lin:>6} linhas")
                break
    
    # Análise dos maiores arquivos não migrados
    print(f"\n🚨 MAIORES ARQUIVOS NÃO MIGRADOS:")
    print("-" * 50)
    
    nao_migrados_detalhes = []
    for arquivo, tamanho, linhas in arquivos_original:
        nome = os.path.basename(arquivo)
        if nome in nao_migrados:
            nao_migrados_detalhes.append((arquivo, tamanho, linhas))
    
    # Ordenar por tamanho (maior primeiro)
    nao_migrados_detalhes.sort(key=lambda x: x[1], reverse=True)
    
    for i, (arquivo, tamanho, linhas) in enumerate(nao_migrados_detalhes[:10], 1):
        print(f"  {i:2d}. {os.path.basename(arquivo):<35} {formatar_tamanho(tamanho):>8} {linhas:>6} linhas")
    
    # Estatísticas comparativas
    print(f"\n📊 COMPARAÇÃO ESTATÍSTICA:")
    print("-" * 50)
    
    reducao_arquivos = len(arquivos_original) - len(arquivos_novo)
    reducao_linhas = total_linhas_original - total_linhas_novo
    reducao_tamanho = total_tamanho_original - total_tamanho_novo
    
    print(f"Arquivos:  {len(arquivos_original):3d} → {len(arquivos_novo):3d} ({reducao_arquivos:+d})")
    print(f"Linhas:    {total_linhas_original:,} → {total_linhas_novo:,} ({reducao_linhas:+,})")
    print(f"Tamanho:   {formatar_tamanho(total_tamanho_original)} → {formatar_tamanho(total_tamanho_novo)} ({reducao_tamanho:+,} bytes)")
    
    if reducao_linhas > 0:
        percentual_reducao = (reducao_linhas / total_linhas_original) * 100
        print(f"\n✅ REDUÇÃO: {percentual_reducao:.1f}% menos linhas de código")
    
    # Recomendações
    print(f"\n🎯 RECOMENDAÇÕES:")
    print("-" * 50)
    
    if len(nao_migrados) > 10:
        print("📋 PRÓXIMO PASSO: Analisar e migrar arquivos críticos não migrados")
        print("   Priorizar arquivos grandes com funcionalidades importantes")
    
    if len(migrados) < 5:
        print("⚠️ ATENÇÃO: Poucos arquivos migrados - considerar migração gradual")
    
    print("\n🚀 STATUS: Nova estrutura criada com arquivos base")
    print("   Pronta para migração gradual das funcionalidades específicas")

if __name__ == "__main__":
    comparar_estruturas() 