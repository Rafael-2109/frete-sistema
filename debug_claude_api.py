#!/usr/bin/env python3
"""
Debug para verificar o problema real do Claude AI Novo
"""

import sys
import os
import logging

# Configurar logging para ver TUDO
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_key_loading():
    """Testa carregamento da API key"""
    print("\n🔍 TESTANDO CARREGAMENTO DA API KEY")
    print("="*60)
    
    # Método 1: Direto do ambiente
    key = os.getenv('ANTHROPIC_API_KEY')
    print(f"1. os.getenv('ANTHROPIC_API_KEY'): {key[:10] if key else 'None'}...")
    
    # Método 2: Via app config
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            from flask import current_app
            key_from_config = current_app.config.get('ANTHROPIC_API_KEY')
            print(f"2. current_app.config: {key_from_config[:10] if key_from_config else 'None'}...")
    except Exception as e:
        print(f"2. Erro ao carregar via Flask: {e}")
    
    # Método 3: ClaudeAPIClient.from_environment()
    try:
        from app.claude_ai_novo.integration.external_api_integration import ClaudeAPIClient
        
        # Verificar método from_environment
        print("\n3. Testando ClaudeAPIClient.from_environment()...")
        client = ClaudeAPIClient.from_environment()
        
        if client:
            print(f"   ✅ Cliente criado")
            print(f"   - api_key: {'configurada' if client.api_key else 'não configurada'}")
            print(f"   - client anthropic: {'criado' if client.client else 'não criado'}")
            print(f"   - model: {client.model}")
            print(f"   - max_tokens: {client.max_tokens}")
        else:
            print("   ❌ Cliente não foi criado")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def test_orchestrator_response():
    """Testa o que o orchestrator está retornando"""
    print("\n\n🔍 TESTANDO RESPOSTA DO ORCHESTRATOR")
    print("="*60)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
            import asyncio
            
            orchestrator = OrchestratorManager()
            
            # Query de teste
            query = "Olá, teste simples"
            context = {"user_id": "test"}
            
            # Processar
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(orchestrator.process_query(query, context))
            
            print(f"\nResultado do orchestrator:")
            print(f"- Tipo: {type(result)}")
            print(f"- Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            
            if isinstance(result, dict):
                print(f"- success: {result.get('success')}")
                print(f"- error: {result.get('error')}")
                print(f"- response: {str(result.get('response'))[:100] if 'response' in result else 'N/A'}...")
                
                # Verificar estrutura mais profunda
                if 'data' in result:
                    print(f"- data keys: {list(result['data'].keys()) if isinstance(result['data'], dict) else 'N/A'}")
                if 'steps_results' in result:
                    print(f"- steps_results: {list(result['steps_results'].keys()) if isinstance(result['steps_results'], dict) else 'N/A'}")
                    
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def test_response_processor():
    """Testa o ResponseProcessor diretamente"""
    print("\n\n🔍 TESTANDO RESPONSE PROCESSOR")
    print("="*60)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.claude_ai_novo.processors.response_processor import get_responseprocessor
            
            processor = get_responseprocessor()
            if processor:
                print("✅ ResponseProcessor carregado")
                
                # Verificar se tem claude_client
                if hasattr(processor, '_claude_client'):
                    print(f"- _claude_client: {processor._claude_client}")
                if hasattr(processor, 'claude_client'):
                    print(f"- claude_client: {processor.claude_client}")
                    
                # Testar método de resposta
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    result = loop.run_until_complete(
                        processor.gerar_resposta_otimizada(
                            consulta="Teste simples",
                            analise={"domains": ["geral"], "filters": {}},
                            user_context={},
                            dados_reais=[]
                        )
                    )
                    print(f"\nResposta gerada: {str(result)[:200]}...")
                except Exception as e:
                    print(f"Erro ao gerar resposta: {e}")
                    
            else:
                print("❌ ResponseProcessor não carregado")
                
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🐛 DEBUG DO CLAUDE AI NOVO")
    print("="*60)
    
    # Verificar se estamos no diretório correto
    print(f"📁 Diretório: {os.getcwd()}")
    print(f"🐍 Python: {sys.version}")
    
    # Executar testes
    test_api_key_loading()
    test_orchestrator_response()
    test_response_processor()