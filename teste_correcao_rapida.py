#!/usr/bin/env python3
"""
🧪 TESTE RÁPIDO DAS CORREÇÕES
Verifica se os problemas de coroutine e suggestion engine foram resolvidos
"""

import asyncio

def teste_sistema_transicao():
    """Testa o sistema de transição corrigido"""
    print("🔄 Testando sistema de transição...")
    
    try:
        from app.claude_transition import processar_consulta_transicao
        
        # Teste básico
        resultado = processar_consulta_transicao("teste", {"user_id": "test"})
        
        print(f"✅ Sistema de transição funcional")
        print(f"📝 Resultado: {resultado[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no sistema de transição: {e}")
        return False

def teste_suggestion_engine():
    """Testa o Suggestion Engine corrigido"""
    print("\n🎯 Testando Suggestion Engine...")
    
    try:
        from claude_ai_novo.suggestions.sugestion_engine import SuggestionEngine
        
        # Criar instância
        engine = SuggestionEngine()
        
        # Teste básico
        user_context = {
            'perfil': 'vendedor',
            'username': 'Teste',
            'vendedor_codigo': '123'
        }
        
        suggestions = engine.generate_suggestions(user_context)
        
        print(f"✅ Suggestion Engine funcional")
        print(f"📝 Geradas {len(suggestions)} sugestões")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no Suggestion Engine: {e}")
        return False

async def teste_sistema_async():
    """Testa o sistema assíncrono"""
    print("\n⚡ Testando sistema assíncrono...")
    
    try:
        from app.claude_transition import processar_consulta_transicao_async
        
        resultado = await processar_consulta_transicao_async("teste async", {"user_id": "test"})
        
        print(f"✅ Sistema assíncrono funcional")
        print(f"📝 Resultado: {resultado[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no sistema assíncrono: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 TESTANDO CORREÇÕES APLICADAS")
    print("=" * 50)
    
    resultados = []
    
    # Teste 1: Sistema de transição
    resultados.append(teste_sistema_transicao())
    
    # Teste 2: Suggestion Engine
    resultados.append(teste_suggestion_engine())
    
    # Teste 3: Sistema assíncrono
    try:
        resultado_async = asyncio.run(teste_sistema_async())
        resultados.append(resultado_async)
    except Exception as e:
        print(f"❌ Erro no teste assíncrono: {e}")
        resultados.append(False)
    
    # Resultado final
    print("\n" + "="*50)
    print("📊 RESULTADO FINAL DAS CORREÇÕES")
    print("="*50)
    
    passou = sum(resultados)
    total = len(resultados)
    
    print(f"✅ Testes passaram: {passou}/{total}")
    print(f"📊 Taxa de sucesso: {passou/total*100:.1f}%")
    
    if passou == total:
        print("\n🎉 TODAS AS CORREÇÕES FUNCIONARAM!")
        print("🚀 Sistema pronto para produção!")
    else:
        print("\n⚠️ Algumas correções ainda precisam de ajustes")
    
    print("\n💡 PRÓXIMOS PASSOS:")
    print("1. Fazer commit das correções")
    print("2. Deploy para produção") 
    print("3. Testar erro 500 em /claude-ai/real")
    print("4. Implementar integração completa")

if __name__ == "__main__":
    main() 