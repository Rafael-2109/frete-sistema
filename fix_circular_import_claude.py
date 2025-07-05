#!/usr/bin/env python3
"""
🔧 Script para resolver import circular entre claude_real_integration e enhanced_claude_integration
"""

import os
import re

def fix_circular_import():
    """Corrige o import circular tornando-o lazy"""
    
    print("🔧 Resolvendo Import Circular do Claude AI...")
    
    # 1. Corrigir claude_real_integration.py
    file_path = "app/claude_ai/claude_real_integration.py"
    
    if not os.path.exists(file_path):
        print(f"❌ Arquivo {file_path} não encontrado")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup original
    with open(file_path + '.backup_circular', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Remover import do topo do arquivo
    content = re.sub(
        r'from \.enhanced_claude_integration import get_enhanced_claude_system',
        '# from .enhanced_claude_integration import get_enhanced_claude_system  # Movido para evitar circular import',
        content
    )
    
    # Tornar o import lazy dentro do try/except existente
    # Procurar o bloco onde enhanced_claude é inicializado
    old_init = """            # 🚀 ENHANCED CLAUDE INTEGRATION - Claude Otimizado
            from .enhanced_claude_integration import get_enhanced_claude_system
            self.enhanced_claude = get_enhanced_claude_system(self.client)
            logger.info("🚀 Enhanced Claude Integration carregado!")"""
    
    new_init = """            # 🚀 ENHANCED CLAUDE INTEGRATION - Claude Otimizado
            try:
                # Import lazy para evitar circular import
                from .enhanced_claude_integration import get_enhanced_claude_system
                self.enhanced_claude = get_enhanced_claude_system(self.client)
                logger.info("🚀 Enhanced Claude Integration carregado!")
            except ImportError as e:
                logger.warning(f"⚠️ Enhanced Claude Integration não disponível: {e}")
                self.enhanced_claude = None"""
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✅ Import lazy aplicado no __init__")
    else:
        print("⚠️ Bloco de inicialização não encontrado no formato esperado")
    
    # Salvar arquivo corrigido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ claude_real_integration.py corrigido")
    
    # 2. Garantir que enhanced_claude_integration.py já tem import lazy
    enhanced_path = "app/claude_ai/enhanced_claude_integration.py"
    
    if os.path.exists(enhanced_path):
        with open(enhanced_path, 'r', encoding='utf-8') as f:
            enhanced_content = f.read()
        
        # Verificar se já tem import lazy
        if "# Import lazy para evitar circular import" in enhanced_content:
            print("✅ enhanced_claude_integration.py já tem import lazy")
        else:
            print("⚠️ enhanced_claude_integration.py pode precisar de ajuste no import")
    
    return True

def verify_fix():
    """Verifica se a correção funcionou"""
    
    print("\n🔍 Verificando correção...")
    
    try:
        # Tentar importar ambos os módulos
        import sys
        sys.path.insert(0, os.getcwd())
        
        # Primeiro importar claude_real_integration
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        print("✅ claude_real_integration importado com sucesso")
        
        # Depois importar enhanced_claude_integration
        from app.claude_ai.enhanced_claude_integration import get_enhanced_claude_system
        print("✅ enhanced_claude_integration importado com sucesso")
        
        # Tentar instanciar
        claude = ClaudeRealIntegration()
        print("✅ ClaudeRealIntegration instanciado com sucesso")
        
        if claude.enhanced_claude:
            print("✅ Enhanced Claude carregado com sucesso")
        else:
            print("⚠️ Enhanced Claude não foi carregado (pode ser falta de API key)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fix Circular Import - Claude AI")
    print("=" * 50)
    
    # Aplicar correção
    if fix_circular_import():
        print("\n✅ Correção aplicada!")
        
        # Verificar
        if verify_fix():
            print("\n🎉 SUCESSO! Import circular resolvido!")
            print("\n📝 Próximos passos:")
            print("1. Faça commit das mudanças")
            print("2. Execute: git push")
            print("3. O Render fará deploy automático")
        else:
            print("\n❌ Verificação falhou. Revise os logs acima.")
    else:
        print("\n❌ Falha ao aplicar correção") 