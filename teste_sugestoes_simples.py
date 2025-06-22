#!/usr/bin/env python3
"""
Teste simples do sistema de sugestões para verificar se o erro foi corrigido
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def testar_sugestoes_basico():
    """Teste básico das sugestões sem dependências externas"""
    print("🧠 TESTE BÁSICO DO SISTEMA DE SUGESTÕES")
    print("=" * 50)
    
    try:
        # Importar apenas o necessário
        from app.claude_ai.suggestion_engine import SuggestionEngine, Suggestion
        
        print("✅ Imports básicos: OK")
        
        # Criar engine sem Redis
        engine = SuggestionEngine(redis_cache=None)
        print("✅ Engine criado sem Redis: OK")
        
        # Teste 1: Sugestões para vendedor
        user_context_vendedor = {
            'user_id': 1,
            'username': 'Vendedor Teste',
            'perfil': 'vendedor',
            'vendedor_codigo': 'V001'
        }
        
        suggestions_vendedor = engine.get_intelligent_suggestions(user_context_vendedor)
        print(f"✅ Sugestões vendedor: {len(suggestions_vendedor)} geradas")
        
        if suggestions_vendedor:
            primeira = suggestions_vendedor[0]
            print(f"   → {primeira.get('icon', '')} {primeira.get('text', 'N/A')}")
        
        # Teste 2: Sugestões para admin
        user_context_admin = {
            'user_id': 2,
            'username': 'Admin Teste',
            'perfil': 'admin'
        }
        
        suggestions_admin = engine.get_intelligent_suggestions(user_context_admin)
        print(f"✅ Sugestões admin: {len(suggestions_admin)} geradas")
        
        # Teste 3: Entrada inválida (para testar correções)
        try:
            suggestions_invalida = engine.get_intelligent_suggestions("string_invalida")
            print(f"✅ Entrada inválida tratada: {len(suggestions_invalida)} sugestões fallback")
        except Exception as e:
            print(f"❌ Erro com entrada inválida: {e}")
            return False
        
        # Teste 4: Teste de validação interna
        test_suggestions = [
            Suggestion("Teste", "test", 3, "🔧", "Teste", ["admin"]),
            "string_invalida",  # Deve ser filtrada
            {"dict": "invalido"}  # Deve ser filtrada
        ]
        
        valid_suggestions = engine._validate_suggestions_list(test_suggestions, "test")
        if len(valid_suggestions) == 1:
            print("✅ Validação de lista funcionando: objetos inválidos filtrados")
        else:
            print(f"❌ Validação falhou: esperado 1, obtido {len(valid_suggestions)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa teste simples"""
    print("🚀 TESTE SIMPLES - VERIFICAÇÃO DE CORREÇÃO DO ERRO")
    print("=" * 60)
    
    sucesso = testar_sugestoes_basico()
    
    if sucesso:
        print("\n" + "=" * 60)
        print("✅ ERRO DE SUGESTÕES CORRIGIDO COM SUCESSO!")
        print("🧠 Sistema agora funciona sem erros de tipo")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ ERRO AINDA PRESENTE - REVISAR CORREÇÕES")
        print("=" * 60)
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 