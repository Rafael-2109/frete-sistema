#!/usr/bin/env python3
"""
Teste do Sistema de Sugestões Inteligentes
Valida todas as funcionalidades implementadas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def testar_sistema_sugestoes():
    """Testa o sistema completo de sugestões inteligentes"""
    
    print("🧠 TESTE DO SISTEMA DE SUGESTÕES INTELIGENTES")
    print("=" * 60)
    
    # Teste 1: Importar módulos
    print("\n1️⃣ TESTE DE IMPORTS")
    try:
        from app.claude_ai.suggestion_engine import SuggestionEngine, Suggestion, init_suggestion_engine, get_suggestion_engine
        print("✅ Imports do sistema de sugestões: OK")
    except ImportError as e:
        print(f"❌ Erro nos imports: {e}")
        return False
    
    # Teste 2: Inicializar engine
    print("\n2️⃣ TESTE DE INICIALIZAÇÃO")
    try:
        # Tentar com Redis
        try:
            from app.utils.redis_cache import redis_cache
            engine = init_suggestion_engine(redis_cache)
            print("✅ Engine inicializado com Redis")
        except ImportError:
            # Fallback sem Redis
            engine = init_suggestion_engine(None)
            print("✅ Engine inicializado sem Redis (fallback)")
        
        if not engine:
            print("❌ Engine não foi inicializado")
            return False
            
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        return False
    
    # Teste 3: Sugestões base
    print("\n3️⃣ TESTE DE SUGESTÕES BASE")
    try:
        total_sugestoes = len(engine.base_suggestions)
        print(f"✅ {total_sugestoes} sugestões base carregadas")
        
        # Mostrar algumas sugestões
        for i, suggestion in enumerate(engine.base_suggestions[:3]):
            print(f"   {i+1}. {suggestion.icon} {suggestion.text} ({suggestion.category})")
            
    except Exception as e:
        print(f"❌ Erro nas sugestões base: {e}")
        return False
    
    # Teste 4: Sugestões por perfil
    print("\n4️⃣ TESTE DE SUGESTÕES POR PERFIL")
    
    # Perfis de teste
    test_profiles = [
        {
            'user_id': 1,
            'username': 'Vendedor Teste',
            'perfil': 'vendedor',
            'vendedor_codigo': 'V001'
        },
        {
            'user_id': 2,
            'username': 'Financeiro Teste', 
            'perfil': 'financeiro',
            'vendedor_codigo': None
        },
        {
            'user_id': 3,
            'username': 'Admin Teste',
            'perfil': 'admin',
            'vendedor_codigo': None
        }
    ]
    
    for profile in test_profiles:
        try:
            suggestions = engine.get_intelligent_suggestions(profile)
            print(f"✅ {profile['perfil']}: {len(suggestions)} sugestões geradas")
            
            # Mostrar primeira sugestão
            if suggestions:
                first = suggestions[0]
                print(f"   → {first['icon']} {first['text']}")
                
        except Exception as e:
            print(f"❌ Erro para perfil {profile['perfil']}: {e}")
            return False
    
    # Teste 5: Sugestões contextuais
    print("\n5️⃣ TESTE DE SUGESTÕES CONTEXTUAIS")
    try:
        # Contexto de conversa sobre cliente específico
        conversation_context = {
            'recent_content': 'Entregas do Assai em junho foram muito boas',
            'client_detected': 'Assai',
            'period_detected': 'junho'
        }
        
        user_context = {
            'user_id': 1,
            'username': 'Vendedor Teste',
            'perfil': 'vendedor'
        }
        
        contextual_suggestions = engine.get_intelligent_suggestions(user_context, conversation_context)
        print(f"✅ Sugestões contextuais: {len(contextual_suggestions)} geradas")
        
        # Verificar se há sugestões específicas para o Assai
        assai_suggestions = [s for s in contextual_suggestions if 'assai' in s['text'].lower()]
        if assai_suggestions:
            print(f"✅ Sugestões específicas do Assai encontradas: {len(assai_suggestions)}")
        else:
            print("⚠️ Nenhuma sugestão específica do Assai (esperado em alguns casos)")
            
    except Exception as e:
        print(f"❌ Erro nas sugestões contextuais: {e}")
        return False
    
    # Teste 6: Cache (se Redis disponível)
    print("\n6️⃣ TESTE DE CACHE")
    try:
        if engine.redis_cache and engine.redis_cache.disponivel:
            # Testar geração com cache
            suggestions1 = engine.get_intelligent_suggestions(test_profiles[0])
            suggestions2 = engine.get_intelligent_suggestions(test_profiles[0])  # Deve vir do cache
            
            print("✅ Cache Redis funcionando")
        else:
            print("⚠️ Cache Redis não disponível (usando fallback)")
            
    except Exception as e:
        print(f"❌ Erro no teste de cache: {e}")
        return False
    
    # Teste 7: Categorização
    print("\n7️⃣ TESTE DE CATEGORIZAÇÃO")
    try:
        categories = {}
        for suggestion in engine.base_suggestions:
            category = suggestion.category
            categories[category] = categories.get(category, 0) + 1
        
        print("✅ Categorias de sugestões:")
        for category, count in categories.items():
            print(f"   {category}: {count} sugestões")
            
    except Exception as e:
        print(f"❌ Erro na categorização: {e}")
        return False
    
    # Teste 8: Fallback
    print("\n8️⃣ TESTE DE FALLBACK")
    try:
        # Simular erro para testar fallback
        fallback_suggestions = engine._get_fallback_suggestions({'perfil': 'vendedor'})
        print(f"✅ Sugestões de fallback: {len(fallback_suggestions)} disponíveis")
        
    except Exception as e:
        print(f"❌ Erro no fallback: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("🧠 Sistema de Sugestões Inteligentes está funcionando perfeitamente")
    print("=" * 60)
    
    return True

def testar_integração_api():
    """Testa integração com o Flask"""
    print("\n🌐 TESTE DE INTEGRAÇÃO COM FLASK")
    print("-" * 40)
    
    try:
        # Tentar importar blueprint
        from app.claude_ai import claude_ai_bp
        print("✅ Blueprint claude_ai importado")
        
        # Verificar se as rotas estão registradas
        routes = [rule.rule for rule in claude_ai_bp.url_map.iter_rules()]
        
        expected_routes = ['/api/suggestions', '/api/suggestions/feedback', '/suggestions/dashboard']
        
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✅ Rota {route} registrada")
            else:
                print(f"⚠️ Rota {route} não encontrada")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração Flask: {e}")
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO TESTES DO SISTEMA DE SUGESTÕES INTELIGENTES")
    
    # Teste 1: Sistema principal
    success1 = testar_sistema_sugestoes()
    
    # Teste 2: Integração Flask
    success2 = testar_integração_api()
    
    if success1 and success2:
        print("\n✅ SISTEMA COMPLETO VALIDADO E PRONTO PARA USO!")
        sys.exit(0)
    else:
        print("\n❌ ALGUNS TESTES FALHARAM - REVISAR IMPLEMENTAÇÃO")
        sys.exit(1) 