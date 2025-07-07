#!/usr/bin/env python3
"""
🧪 TESTE RÁPIDO - Execute este arquivo para testar a nova interface
"""

import sys
from pathlib import Path

# Adicionar path do projeto
projeto_root = Path(__file__).parent
sys.path.insert(0, str(projeto_root))

def main():
    print("🧪 TESTANDO A NOVA INTERFACE DE TRANSIÇÃO")
    print("="*50)
    
    try:
        # Importar e testar
        from app.claude_transition import processar_consulta_transicao
        
        print("✅ Interface importada com sucesso!")
        
        # Teste básico
        resultado = processar_consulta_transicao("Como você está funcionando?")
        
        print("✅ Teste realizado com sucesso!")
        print(f"📄 Resultado: {resultado[:100]}...")
        
        print("\n🎉 PRONTO PARA USO!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. ✅ Substitua suas chamadas do Claude AI pela interface de transição")
        print("2. ✅ Configure USE_NEW_CLAUDE_SYSTEM=true quando quiser usar o sistema novo")
        print("3. ✅ Continue usando normalmente - o sistema escolhe automaticamente!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("🔧 Verifique se todos os arquivos estão no lugar correto")

if __name__ == "__main__":
    main() 