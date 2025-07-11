#!/usr/bin/env python3
"""
Contagem detalhada e precisa de todos os módulos/arquivos Python no sistema claude_ai_novo.
Inclui análise completa de subdiretórios e contagem exata.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

def contar_arquivos_detalhado():
    """Conta todos os arquivos Python de forma detalhada"""
    
    print("🔢 CONTAGEM DETALHADA DE TODOS OS MÓDULOS")
    print("=" * 50)
    
    # Diretório base
    base_dir = Path(".")
    
    # Contadores
    total_arquivos_py = 0
    total_diretorios = 0
    total_arquivos_outros = 0
    
    # Estatísticas por pasta
    def criar_stats():
        return {
            'arquivos_py': 0,
            'subdirs': 0,
            'outros_arquivos': 0,
            'arquivos_lista': [],
            'subdirs_lista': []
        }
    
    stats_por_pasta = defaultdict(criar_stats)
    
    # Percorrer recursivamente
    for root, dirs, files in os.walk(base_dir):
        root_path = Path(root)
        
        # Pular diretórios especiais
        if any(part.startswith('.') or part == '__pycache__' for part in root_path.parts):
            continue
            
        # Se está na raiz, pular alguns arquivos
        if root_path == base_dir:
            continue
            
        # Determinar a pasta principal
        if root_path.parent == base_dir:
            pasta_principal = root_path.name
        else:
            # Para subdiretórios, usar a pasta principal
            partes = root_path.relative_to(base_dir).parts
            pasta_principal = partes[0] if partes else 'root'
        
        print(f"📁 Analisando: {root_path}")
        
        # Contar arquivos Python
        arquivos_py_local = []
        outros_arquivos_local = []
        
        for file in files:
            if file.endswith('.py'):
                arquivos_py_local.append(file)
                total_arquivos_py += 1
                stats_por_pasta[pasta_principal]['arquivos_py'] += 1
            elif not file.startswith('.') and file != 'pyrightconfig.json':
                outros_arquivos_local.append(file)
                total_arquivos_outros += 1
                stats_por_pasta[pasta_principal]['outros_arquivos'] += 1
        
        # Contar subdiretórios (apenas os válidos)
        subdirs_validos = []
        for dir_name in dirs:
            if not dir_name.startswith('.') and dir_name != '__pycache__':
                subdirs_validos.append(dir_name)
                total_diretorios += 1
                stats_por_pasta[pasta_principal]['subdirs'] += 1
        
        # Adicionar aos stats
        stats_por_pasta[pasta_principal]['arquivos_lista'].extend(arquivos_py_local)
        stats_por_pasta[pasta_principal]['subdirs_lista'].extend(subdirs_validos)
        
        # Mostrar arquivos encontrados
        if arquivos_py_local:
            for arquivo in arquivos_py_local:
                print(f"   🐍 {arquivo}")
        
        if subdirs_validos:
            for subdir in subdirs_validos:
                print(f"   📁 {subdir}/")
        
        if outros_arquivos_local:
            for arquivo in outros_arquivos_local[:3]:  # Mostrar apenas 3 primeiros
                print(f"   📄 {arquivo}")
            if len(outros_arquivos_local) > 3:
                print(f"   📄 ... e mais {len(outros_arquivos_local) - 3} arquivos")
        
        print()
    
    return {
        'total_arquivos_py': total_arquivos_py,
        'total_diretorios': total_diretorios,
        'total_arquivos_outros': total_arquivos_outros,
        'stats_por_pasta': dict(stats_por_pasta)
    }

def mostrar_estatisticas_detalhadas(stats):
    """Mostra estatísticas detalhadas"""
    
    print("📊 ESTATÍSTICAS DETALHADAS")
    print("=" * 30)
    
    print(f"🐍 Total de arquivos Python: {stats['total_arquivos_py']}")
    print(f"📁 Total de diretórios: {stats['total_diretorios']}")
    print(f"📄 Outros arquivos: {stats['total_arquivos_outros']}")
    print(f"📦 Total geral: {stats['total_arquivos_py'] + stats['total_arquivos_outros']}")
    print()
    
    print("📋 DETALHAMENTO POR PASTA:")
    print("=" * 30)
    
    for pasta, dados in sorted(stats['stats_por_pasta'].items()):
        print(f"📁 {pasta}/")
        print(f"   🐍 Arquivos Python: {dados['arquivos_py']}")
        print(f"   📁 Subdiretórios: {dados['subdirs']}")
        print(f"   📄 Outros arquivos: {dados['outros_arquivos']}")
        
        if dados['arquivos_lista']:
            print(f"   📝 Arquivos Python:")
            for arquivo in dados['arquivos_lista']:
                print(f"      • {arquivo}")
        
        if dados['subdirs_lista']:
            print(f"   📂 Subdiretórios:")
            for subdir in dados['subdirs_lista']:
                print(f"      • {subdir}/")
        
        print()

def contar_linhas_codigo():
    """Conta linhas de código Python"""
    
    print("📏 CONTAGEM DE LINHAS DE CÓDIGO")
    print("=" * 35)
    
    total_linhas = 0
    total_arquivos = 0
    
    for root, dirs, files in os.walk("."):
        # Pular diretórios especiais
        if any(part.startswith('.') or part == '__pycache__' for part in Path(root).parts):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        linhas = len(f.readlines())
                        total_linhas += linhas
                        total_arquivos += 1
                        
                        if linhas > 500:  # Mostrar arquivos grandes
                            print(f"📄 {file_path}: {linhas} linhas (GRANDE)")
                            
                except Exception as e:
                    print(f"❌ Erro ao ler {file_path}: {e}")
    
    print(f"\n📊 TOTAL:")
    print(f"   📄 Arquivos Python: {total_arquivos}")
    print(f"   📏 Linhas de código: {total_linhas:,}")
    print(f"   📈 Média por arquivo: {total_linhas / total_arquivos:.1f} linhas")
    print()

def verificar_modulos_especiais():
    """Verifica módulos especiais e importações"""
    
    print("🔍 VERIFICAÇÃO DE MÓDULOS ESPECIAIS")
    print("=" * 40)
    
    # Verificar arquivos grandes
    arquivos_grandes = []
    arquivos_importantes = []
    
    for root, dirs, files in os.walk("."):
        if any(part.startswith('.') or part == '__pycache__' for part in Path(root).parts):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        linhas = len(f.readlines())
                        
                        if linhas > 300:
                            arquivos_grandes.append((str(file_path), linhas))
                        
                        # Verificar arquivos importantes
                        if any(palavra in file.lower() for palavra in 
                               ['orchestrator', 'manager', 'processor', 'coordinator']):
                            arquivos_importantes.append((str(file_path), linhas))
                            
                except Exception:
                    pass
    
    print("📄 ARQUIVOS GRANDES (>300 linhas):")
    for arquivo, linhas in sorted(arquivos_grandes, key=lambda x: x[1], reverse=True):
        print(f"   • {arquivo}: {linhas} linhas")
    
    print(f"\n🎯 ARQUIVOS IMPORTANTES:")
    for arquivo, linhas in sorted(arquivos_importantes, key=lambda x: x[1], reverse=True):
        print(f"   • {arquivo}: {linhas} linhas")
    
    print()

def main():
    """Função principal"""
    
    print("🧮 CONTAGEM COMPLETA E DETALHADA DO SISTEMA CLAUDE_AI_NOVO")
    print("=" * 70)
    print()
    
    # Contagem detalhada
    stats = contar_arquivos_detalhado()
    
    # Mostrar estatísticas
    mostrar_estatisticas_detalhadas(stats)
    
    # Contar linhas de código
    contar_linhas_codigo()
    
    # Verificar módulos especiais
    verificar_modulos_especiais()
    
    # Conclusão
    print("🎯 CONCLUSÃO FINAL")
    print("=" * 20)
    
    total_py = stats['total_arquivos_py']
    total_outros = stats['total_arquivos_outros']
    total_geral = total_py + total_outros
    
    print(f"🐍 Arquivos Python (módulos): {total_py}")
    print(f"📄 Outros arquivos: {total_outros}")
    print(f"📦 TOTAL GERAL: {total_geral}")
    print()
    
    if total_py > 97:
        print(f"✅ CORREÇÃO: O sistema tem {total_py} módulos Python, não 97!")
        print(f"📈 Diferença: +{total_py - 97} módulos a mais do que relatado inicialmente")
    elif total_py == 97:
        print("✅ CONFIRMAÇÃO: O sistema tem exatamente 97 módulos Python")
    else:
        print(f"⚠️ DISCREPÂNCIA: O sistema tem {total_py} módulos, menos que os 97 relatados")
    
    print(f"\n🏗️ SISTEMA MUITO ROBUSTO:")
    print(f"   • {len(stats['stats_por_pasta'])} pastas principais")
    print(f"   • {stats['total_diretorios']} subdiretórios")
    print(f"   • {total_py} módulos Python")
    print(f"   • Sistema bem estruturado e organizado")

if __name__ == "__main__":
    main() 