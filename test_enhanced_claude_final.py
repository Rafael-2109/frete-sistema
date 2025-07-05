#!/usr/bin/env python3
"""
🧪 Teste final para verificar se o Enhanced Claude está funcionando
"""

import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_claude():
    """Testa se o Enhanced Claude está funcionando"""
    
    print("🧪 Testando Enhanced Claude...")
    
    # 1. Testar imports individuais
    print("\n1️⃣ Testando imports individuais...")
    try:
        from app.claude_ai.claude_real_integration import claude_real_integration
        print("✅ claude_real_integration importado")
    except Exception as e:
        print(f"❌ Erro ao importar claude_real_integration: {e}")
        return False
    
    try:
        from app.claude_ai.enhanced_claude_integration import enhanced_claude_integration
        print("✅ enhanced_claude_integration importado")
    except Exception as e:
        print(f"❌ Erro ao importar enhanced_claude_integration: {e}")
        return False
    
    # 2. Testar conexão manual
    print("\n2️⃣ Conectando Enhanced Claude com Claude Real...")
    try:
        # Injetar enhanced no real
        claude_real_integration.set_enhanced_claude(enhanced_claude_integration)
        print("✅ Enhanced injetado no Real")
        
        # Injetar real no enhanced
        enhanced_claude_integration.claude_integration = claude_real_integration
        print("✅ Real injetado no Enhanced")
        
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return False
    
    # 3. Verificar conexões
    print("\n3️⃣ Verificando conexões...")
    if claude_real_integration.enhanced_claude is not None:
        print("✅ claude_real_integration.enhanced_claude está conectado")
    else:
        print("❌ claude_real_integration.enhanced_claude é None")
    
    if enhanced_claude_integration.claude_integration is not None:
        print("✅ enhanced_claude_integration.claude_integration está conectado")
    else:
        print("❌ enhanced_claude_integration.claude_integration é None")
    
    # 4. Testar processamento básico
    print("\n4️⃣ Testando processamento de consulta...")
    try:
        resultado = enhanced_claude_integration.processar_consulta_inteligente(
            "quantas entregas do Assai estão pendentes?",
            {"user_id": "test"}
        )
        
        print(f"✅ Processamento realizado com sucesso")
        print(f"   - Resposta: {resultado.get('resposta', '')[:100]}...")
        print(f"   - Confiança: {resultado.get('interpretacao', {}).get('confianca', 0):.1%}")
        
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Testar setup_claude_ai
    print("\n5️⃣ Testando setup_claude_ai()...")
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.claude_ai import setup_claude_ai
            result = setup_claude_ai(app)
            
            if result:
                print("✅ setup_claude_ai() executado com sucesso")
            else:
                print("⚠️ setup_claude_ai() retornou False")
                
    except Exception as e:
        print(f"❌ Erro ao testar setup_claude_ai: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Teste concluído!")
    return True

if __name__ == "__main__":
    test_enhanced_claude() 