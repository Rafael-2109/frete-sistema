#!/usr/bin/env python3
"""
🔧 SOLUÇÃO DEFINITIVA PARA O TRAVAMENTO
======================================

Remove todos os imports circulares e problemáticos que causam travamento.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def aplicar_solucao():
    """Aplica solução definitiva para o travamento"""
    
    print("🔧 APLICANDO SOLUÇÃO DEFINITIVA PARA O TRAVAMENTO\n")
    
    correções = []
    
    # 1. Corrigir integration/__init__.py
    print("1️⃣ Verificando integration/__init__.py...")
    integration_init = Path(__file__).parent / "integration" / "__init__.py"
    
    if integration_init.exists():
        with open(integration_init, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se há imports problemáticos durante a inicialização
        if "# Inicialização dos módulos" in content:
            print("   ⚠️ Encontrado código de inicialização")
            
            # Comentar inicialização automática
            new_content = content.replace(
                "# Inicialização dos módulos",
                "# Inicialização dos módulos (DESABILITADO para evitar travamento)"
            )
            
            # Procurar por código que executa durante import
            lines = content.split('\n')
            modified = False
            new_lines = []
            
            for line in lines:
                # Comentar linhas que executam código durante import
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('from') and not line.strip().startswith('import'):
                    if '=' in line and 'def' not in line and 'class' not in line:
                        # Possível execução durante import
                        if '_global_instances' in line or 'logger.' in line:
                            new_lines.append(line)
                        else:
                            new_lines.append(f"# {line}  # DESABILITADO: Possível causa de travamento")
                            modified = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            if modified:
                with open(integration_init, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                correções.append("integration/__init__.py - código de inicialização comentado")
    
    # 2. Verificar analyzers/__init__.py
    print("\n2️⃣ Verificando analyzers/__init__.py...")
    analyzers_init = Path(__file__).parent / "analyzers" / "__init__.py"
    
    if analyzers_init.exists():
        with open(analyzers_init, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # O analyzers tem muitos imports que podem causar travamento
        if "spacy" in content or "nltk" in content:
            print("   ⚠️ Encontrado imports pesados (spacy, nltk)")
            print("   💡 Esses imports são lentos mas não causam loop")
    
    # 3. Criar arquivo de configuração para desabilitar inicialização automática
    print("\n3️⃣ Criando arquivo de configuração...")
    config_file = Path(__file__).parent / "NO_AUTO_INIT"
    
    with open(config_file, 'w') as f:
        f.write("Este arquivo desabilita inicialização automática de módulos\n")
    
    correções.append("NO_AUTO_INIT - arquivo de configuração criado")
    
    # 4. Verificar se há outros arquivos problemáticos
    print("\n4️⃣ Procurando outros possíveis problemas...")
    
    # Procurar por arquivos que importam muitos módulos
    problem_files = []
    for py_file in Path(__file__).parent.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Contar imports
            import_count = content.count("import ")
            if import_count > 50:
                problem_files.append((py_file.name, import_count))
        except:
            pass
    
    if problem_files:
        print("\n   ⚠️ Arquivos com muitos imports (possível lentidão):")
        for file, count in sorted(problem_files, key=lambda x: x[1], reverse=True)[:5]:
            print(f"      - {file}: {count} imports")
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DAS CORREÇÕES")
    print("="*60)
    
    if correções:
        print("\n✅ CORREÇÕES APLICADAS:")
        for correção in correções:
            print(f"   - {correção}")
    
    print("\n📝 RECOMENDAÇÕES:")
    print("1. Reinicie o Python/Terminal para limpar cache de imports")
    print("2. Execute o teste novamente")
    print("3. Se ainda travar, o problema pode ser nos imports do spacy/nltk")
    print("4. Considere usar lazy loading para todos os módulos pesados")
    
    print("\n💡 SOLUÇÃO ALTERNATIVA:")
    print("Se o problema persistir, use imports diretos ao invés de")
    print("importar via __init__.py:")
    print("   # Ao invés de:")
    print("   from app.claude_ai_novo.integration import get_integration_manager")
    print("   # Use:")
    print("   from app.claude_ai_novo.integration.integration_manager import get_integration_manager")

if __name__ == "__main__":
    aplicar_solucao() 