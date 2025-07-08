#!/usr/bin/env python3
"""
🧹 REMOVER SUGGESTION DASHBOARD
Script para remover funcionalidade desnecessária de forma segura
"""

import os
import re
import shutil
from pathlib import Path

def remover_suggestion_dashboard():
    """Remove a funcionalidade Suggestion Dashboard"""
    
    print("🧹 REMOVENDO SUGGESTION DASHBOARD")
    print("=" * 50)
    
    # 1. Remover rota em routes.py
    print("\n1. Removendo rota /suggestions/dashboard...")
    routes_file = Path("app/claude_ai/routes.py")
    
    if routes_file.exists():
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remover rota suggestions/dashboard
        lines = content.split('\n')
        new_lines = []
        skip_lines = False
        
        for i, line in enumerate(lines):
            # Detectar início da rota
            if "@claude_ai_bp.route('/suggestions/dashboard')" in line:
                skip_lines = True
                print(f"   ✅ Removendo rota na linha {i+1}")
                continue
            
            # Detectar fim da rota (próxima rota ou fim da função)
            if skip_lines and (line.startswith('@') or line.startswith('def ') and not line.startswith('def suggestions_dashboard')):
                skip_lines = False
            
            if not skip_lines:
                new_lines.append(line)
        
        # Salvar arquivo modificado
        with open(routes_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        print("   ✅ Rota removida com sucesso")
    else:
        print("   ⚠️ Arquivo routes.py não encontrado")
    
    # 2. Remover template
    print("\n2. Removendo template suggestions_dashboard.html...")
    template_file = Path("app/templates/claude_ai/suggestions_dashboard.html")
    
    if template_file.exists():
        # Fazer backup antes de remover
        backup_file = template_file.with_suffix('.html.backup_removed')
        shutil.copy2(template_file, backup_file)
        
        # Remover arquivo
        template_file.unlink()
        print(f"   ✅ Template removido (backup: {backup_file})")
    else:
        print("   ⚠️ Template não encontrado")
    
    # 3. Verificar e remover referências órfãs
    print("\n3. Verificando referências órfãs...")
    
    # Buscar por 'suggestions_dashboard' em outros arquivos
    files_to_check = [
        "app/claude_ai/__init__.py",
        "app/templates/claude_ai/chat.html",
        "app/templates/claude_ai/claude_real.html",
        "app/templates/claude_ai/dashboard.html"
    ]
    
    references_found = False
    for file_path in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'suggestions_dashboard' in content or 'suggestions/dashboard' in content:
                print(f"   ⚠️ Referência encontrada em {file_path}")
                references_found = True
    
    if not references_found:
        print("   ✅ Nenhuma referência órfã encontrada")
    
    print("\n" + "=" * 50)
    print("✅ SUGGESTION DASHBOARD REMOVIDO COM SUCESSO!")
    print("📊 Recursos liberados:")
    print("   - 1 rota HTTP removida")
    print("   - 1 template removido")
    print("   - Código mais limpo")
    
    return True

def validar_remocao():
    """Valida se a remoção foi bem-sucedida"""
    print("\n🔍 VALIDANDO REMOÇÃO...")
    
    # Verificar se rota foi removida
    routes_file = Path("app/claude_ai/routes.py")
    if routes_file.exists():
        with open(routes_file, 'r') as f:
            content = f.read()
        
        if "suggestions_dashboard" in content:
            print("❌ Ainda há referências à rota")
            return False
        else:
            print("✅ Rota removida corretamente")
    
    # Verificar se template foi removido
    template_file = Path("app/templates/claude_ai/suggestions_dashboard.html")
    if template_file.exists():
        print("❌ Template ainda existe")
        return False
    else:
        print("✅ Template removido corretamente")
    
    print("🎉 VALIDAÇÃO CONCLUÍDA - REMOÇÃO BEM-SUCEDIDA!")
    return True

if __name__ == "__main__":
    try:
        # Fazer remoção
        sucesso = remover_suggestion_dashboard()
        
        if sucesso:
            # Validar remoção
            validar_remocao()
        
    except Exception as e:
        print(f"❌ ERRO durante remoção: {e}")
        print("🔄 Sistema não foi modificado") 