#!/usr/bin/env python3
"""
Teste simplificado do Claude AI Novo
"""

import os
import sys
import logging

# Configurar path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_flask_app():
    """Testa se consegue executar dentro do contexto Flask"""
    logger.info("🔍 Testando com contexto Flask...")
    
    try:
        # Configurar ambiente
        os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db')
        os.environ['SECRET_KEY'] = 'test-key'
        
        # Importar e criar app
        from app import create_app, db
        app = create_app()
        
        logger.info("✅ App Flask criado com sucesso")
        
        # Executar no contexto do app
        with app.app_context():
            logger.info("✅ Contexto Flask ativo")
            
            # Tentar importar e usar o claude_ai_novo
            from app.claude_ai_novo import get_claude_ai_instance
            
            claude_instance = get_claude_ai_instance()
            logger.info(f"✅ Instância criada: {type(claude_instance)}")
            
            # Testar processamento
            result = claude_instance.processar_consulta_sync("teste de integração")
            logger.info(f"✅ Resultado: {result[:100]}...")
            
            # Verificar status
            status = claude_instance.get_system_status()
            logger.info(f"📊 Status do sistema:")
            logger.info(f"  - Sistema pronto: {status.get('system_ready')}")
            logger.info(f"  - Módulos disponíveis: {claude_instance.get_available_modules()}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes():
    """Testa se as rotas funcionam"""
    logger.info("\n🔍 Testando rotas...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.test_client() as client:
            # Testar rota de chat
            response = client.post('/claude-ai/chat', 
                                 json={'message': 'teste'},
                                 follow_redirects=False)
            
            logger.info(f"  - Rota /chat: {response.status_code}")
            if response.status_code == 302:  # Redirecionamento para login
                logger.info("    ⚠️ Requer autenticação")
            elif response.status_code == 200:
                logger.info(f"    ✅ Resposta: {response.json}")
            
            # Testar rota de status
            response = client.get('/claude-ai/api/claude-ai-novo-metrics')
            logger.info(f"  - Rota /api/claude-ai-novo-metrics: {response.status_code}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro nas rotas: {e}")
        return False

def test_transition_manager():
    """Testa o transition manager diretamente"""
    logger.info("\n🔍 Testando transition manager...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.claude_transition import processar_consulta_transicao
            
            # Forçar uso do sistema novo
            os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'
            
            result = processar_consulta_transicao("Como estão as entregas?")
            logger.info(f"✅ Resultado transition: {result[:100]}...")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro no transition: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    logger.info("🚀 TESTE SIMPLIFICADO DO CLAUDE AI NOVO")
    logger.info("=" * 60)
    
    tests = [
        test_flask_app,
        test_routes,
        test_transition_manager
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append((test.__name__, result))
    
    logger.info("\n📊 RESUMO:")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{len(results)} testes passaram")
    
    if passed < len(results):
        logger.info("\n💡 DIAGNÓSTICO:")
        logger.info("O problema principal parece estar nos erros de sintaxe nos arquivos:")
        logger.info("1. app/claude_ai_novo/utils/flask_fallback.py")
        logger.info("2. app/claude_ai_novo/memorizers/context_memory.py")
        logger.info("\nEstes erros impedem a importação correta dos módulos.")

if __name__ == "__main__":
    main()