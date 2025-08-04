"""
Test script for Claude integration
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.mcp_logistica.query_processor import QueryProcessor
from app.mcp_logistica.claude_integration import ClaudeIntegration

def test_claude_integration():
    """Test Claude integration functionality"""
    
    app = create_app()
    
    with app.app_context():
        # Initialize components
        processor = QueryProcessor(db.session)
        
        # Test queries
        test_queries = [
            # Low confidence queries that should trigger Claude
            "explique como funciona o sistema de entregas",
            "analise os atrasos desta semana",
            "compare as entregas de SP com RJ",
            "o que você pode me dizer sobre os pedidos pendentes?",
            
            # Normal queries that might get enhanced
            "quantas entregas para São Paulo hoje",
            "liste pedidos do cliente ABC",
            "mostrar notas fiscais em atraso",
            
            # Complex queries requiring Claude insights
            "qual a tendência de entregas para o próximo mês?",
            "sugestões para melhorar o tempo de entrega",
            "análise de performance das transportadoras"
        ]
        
        print("=" * 60)
        print("TESTANDO INTEGRAÇÃO COM CLAUDE")
        print("=" * 60)
        print()
        
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            print("-" * 50)
            
            # Process query
            user_context = {
                'user_id': 'test_user',
                'user_name': 'Test User',
                'session_id': 'test_session',
                'enhance_with_claude': True  # Force Claude enhancement
            }
            
            result = processor.process(query, user_context)
            
            # Show results
            print(f"✅ Success: {result.success}")
            print(f"🎯 Intent: {result.intent.primary} (confidence: {result.intent.confidence:.2f})")
            
            if result.claude_response:
                print(f"🤖 Claude Used: {result.claude_response.response_type}")
                print(f"   Confidence: {result.claude_response.confidence}")
                
                if result.natural_response:
                    print(f"\n💬 Natural Response:")
                    print(f"   {result.natural_response[:200]}...")
                    
            if result.suggestions:
                print(f"\n💡 Suggestions:")
                for i, suggestion in enumerate(result.suggestions[:3], 1):
                    print(f"   {i}. {suggestion}")
                    
            if result.error:
                print(f"\n❌ Error: {result.error}")
                
            print()
            
        # Test session context
        print("\n" + "=" * 60)
        print("TESTANDO CONTEXTO DE SESSÃO")
        print("=" * 60)
        
        # Get session summary
        summary = processor.claude_integration.get_session_summary('test_user', 'test_session')
        print(f"\n📊 Session Summary:")
        print(f"   Queries: {summary['query_count']}")
        print(f"   Domains: {', '.join(summary['domains_accessed'])}")
        
        # Clear session
        processor.claude_integration.clear_session_context('test_user', 'test_session')
        print("\n✅ Session context cleared")

if __name__ == '__main__':
    test_claude_integration()