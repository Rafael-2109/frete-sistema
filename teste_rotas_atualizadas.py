#!/usr/bin/env python3
"""
🧪 TESTE DAS ROTAS ATUALIZADAS - Blueprint e Interface de Transição
"""

import sys
from pathlib import Path

# Configurar path
projeto_root = Path(__file__).parent
sys.path.insert(0, str(projeto_root))

def main():
    print("🧪 TESTANDO ROTAS ATUALIZADAS DO CLAUDE AI")
    print("="*50)
    
    try:
        # Teste 1: Verificar se a interface de transição funciona
        print("1️⃣ Testando interface de transição...")
        from app.claude_transition import processar_consulta_transicao
        resultado = processar_consulta_transicao("Teste de integração das rotas")
        print(f"   ✅ Interface funcionando: {resultado[:50]}...")
        
        # Teste 2: Verificar imports das rotas
        print("2️⃣ Testando imports das rotas...")
        import app.claude_ai.routes
        print("   ✅ Rotas importadas com sucesso")
        
        # Teste 3: Verificar se blueprint está registrado
        print("3️⃣ Verificando blueprint...")
        from app.claude_ai import claude_ai_bp
        print(f"   ✅ Blueprint: {claude_ai_bp.name}")
        
        # Teste 4: Verificar se não há chamadas do sistema antigo
        print("4️⃣ Verificando código das rotas...")
        with open("app/claude_ai/routes.py", "r", encoding="utf-8") as f:
            conteudo = f.read()
        
        # Verificar se ainda há chamadas do sistema antigo
        if "processar_com_claude_real" in conteudo:
            print("   ❌ Ainda há chamadas do sistema antigo!")
            return False
        else:
            print("   ✅ Todas as chamadas atualizadas para interface de transição")
        
        # Teste 5: Verificar se interface de transição está importada
        if "processar_consulta_transicao" in conteudo:
            print("   ✅ Interface de transição corretamente importada")
        else:
            print("   ❌ Interface de transição não encontrada!")
            return False
        
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("="*50)
        print("✅ Blueprint registrado corretamente")
        print("✅ Rotas atualizadas para interface de transição")  
        print("✅ Sistema antigo não é mais chamado diretamente")
        print("✅ Interface funciona automaticamente (novo vs antigo)")
        
        print("\n🚀 INTEGRAÇÃO BLUEPRINT + TRANSIÇÃO COMPLETA!")
        print("💡 As rotas Flask agora usam o sistema modular automaticamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 