#!/usr/bin/env python3
"""
🔧 ATUALIZAR IMPORTS DO SISTEMA
===============================

Atualiza todos os imports para usar caminhos diretos e evitar travamentos.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Mapeamento de imports antigos para novos
IMPORT_MAPPINGS = [
    # Integration Manager
    (
        r'from app\.claude_ai_novo\.integration import get_integration_manager',
        'from app.claude_ai_novo.integration.integration_manager import get_integration_manager'
    ),
    (
        r'from \.\.integration import get_integration_manager',
        'from ..integration.integration_manager import get_integration_manager'
    ),
    (
        r'from \.integration import get_integration_manager',
        'from .integration.integration_manager import get_integration_manager'
    ),
    
    # Orchestrator Manager
    (
        r'from app\.claude_ai_novo\.orchestrators import get_orchestrator_manager',
        'from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager'
    ),
    (
        r'from \.\.orchestrators import get_orchestrator_manager',
        'from ..orchestrators.orchestrator_manager import get_orchestrator_manager'
    ),
    
    # Session Orchestrator
    (
        r'from app\.claude_ai_novo\.orchestrators import get_session_orchestrator',
        'from app.claude_ai_novo.orchestrators.session_orchestrator import get_session_orchestrator'
    ),
    
    # Analyzers
    (
        r'from app\.claude_ai_novo\.analyzers import get_analyzer_manager',
        'from app.claude_ai_novo.analyzers.analyzer_manager import get_analyzer_manager'
    ),
    
    # Processors
    (
        r'from app\.claude_ai_novo\.processors import get_processor_manager',
        'from app.claude_ai_novo.processors.processor_manager import get_processor_manager'
    ),
]

def atualizar_arquivo(file_path: Path, dry_run: bool = False) -> List[Tuple[int, str, str]]:
    """
    Atualiza imports em um arquivo.
    
    Args:
        file_path: Caminho do arquivo
        dry_run: Se True, apenas mostra o que seria alterado
        
    Returns:
        Lista de (linha, antes, depois) das alterações
    """
    alteracoes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        modified = False
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Aplicar cada mapeamento
            for old_pattern, new_import in IMPORT_MAPPINGS:
                if re.search(old_pattern, line):
                    # Preservar indentação
                    indent = len(line) - len(line.lstrip())
                    new_line = ' ' * indent + new_import + '\n'
                    
                    if new_line != original_line:
                        alteracoes.append((i + 1, original_line.strip(), new_line.strip()))
                        line = new_line
                        modified = True
                        break
            
            new_lines.append(line)
        
        # Salvar arquivo se houve alterações e não é dry run
        if modified and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        
    except Exception as e:
        print(f"❌ Erro ao processar {file_path}: {e}")
    
    return alteracoes

def atualizar_sistema(dry_run: bool = False):
    """
    Atualiza todos os arquivos Python do sistema.
    
    Args:
        dry_run: Se True, apenas mostra o que seria alterado
    """
    print("🔧 ATUALIZANDO IMPORTS DO SISTEMA CLAUDE AI NOVO\n")
    
    if dry_run:
        print("🔍 MODO DRY RUN - Apenas mostrando o que seria alterado\n")
    
    # Diretórios a processar
    dirs_to_process = [
        Path(__file__).parent,  # claude_ai_novo
        Path(__file__).parent.parent / "claude_ai",  # claude_ai antigo
        Path(__file__).parent.parent,  # app
    ]
    
    total_files = 0
    total_changes = 0
    files_with_changes = []
    
    # Processar cada diretório
    for base_dir in dirs_to_process:
        if not base_dir.exists():
            continue
        
        # Buscar todos os arquivos Python
        py_files = list(base_dir.rglob("*.py"))
        
        for py_file in py_files:
            # Pular arquivos em __pycache__ e migrations
            if "__pycache__" in str(py_file) or "migrations" in str(py_file):
                continue
            
            # Pular este próprio script
            if py_file.name == "atualizar_imports_sistema.py":
                continue
            
            total_files += 1
            alteracoes = atualizar_arquivo(py_file, dry_run)
            
            if alteracoes:
                files_with_changes.append((py_file, alteracoes))
                total_changes += len(alteracoes)
    
    # Mostrar resultados
    print(f"\n📊 RESUMO DA ATUALIZAÇÃO:")
    print(f"   Arquivos analisados: {total_files}")
    print(f"   Arquivos com alterações: {len(files_with_changes)}")
    print(f"   Total de imports atualizados: {total_changes}")
    
    if files_with_changes:
        print(f"\n📝 ARQUIVOS {'QUE SERIAM ALTERADOS' if dry_run else 'ALTERADOS'}:\n")
        
        for file_path, alteracoes in files_with_changes:
            # Mostrar caminho relativo
            try:
                rel_path = file_path.relative_to(root_dir)
            except:
                rel_path = file_path
            
            print(f"   📄 {rel_path}")
            for linha, antes, depois in alteracoes:
                print(f"      Linha {linha}:")
                print(f"        ❌ {antes}")
                print(f"        ✅ {depois}")
            print()
    
    if not dry_run and total_changes > 0:
        print("✅ IMPORTS ATUALIZADOS COM SUCESSO!")
        print("\n💡 PRÓXIMOS PASSOS:")
        print("1. Reinicie o servidor Flask")
        print("2. Teste o sistema para garantir que tudo funciona")
        print("3. Os travamentos devem estar resolvidos")
    elif dry_run and total_changes > 0:
        print("\n💡 Para aplicar as alterações, execute:")
        print("   python atualizar_imports_sistema.py --apply")

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Atualiza imports do sistema Claude AI Novo')
    parser.add_argument('--apply', action='store_true', help='Aplica as alterações (sem isso, apenas mostra)')
    parser.add_argument('--check-only', action='store_true', help='Apenas verifica sem alterar')
    
    args = parser.parse_args()
    
    # Se não passou --apply, fazer dry run
    dry_run = not args.apply
    
    atualizar_sistema(dry_run)
    
    if dry_run and not args.check_only:
        print("\n⚠️ ATENÇÃO: Este foi um DRY RUN - nenhum arquivo foi alterado")
        print("Para aplicar as alterações, use: python atualizar_imports_sistema.py --apply")

if __name__ == "__main__":
    main() 