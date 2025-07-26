#!/usr/bin/env python3
"""
Test script to identify specific integration issues between claude_ai_novo and the main Flask app
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_flask_app_integration():
    """Test integration with main Flask app"""
    print("\n🔍 Testing Flask App Integration...")
    
    try:
        # Try to import and create Flask app
        from app import create_app
        app = create_app()
        print("✅ Flask app created successfully")
        
        # Test within app context
        with app.app_context():
            # Test database connection
            from app import db
            from sqlalchemy import text
            try:
                db.session.execute(text('SELECT 1'))
                print("✅ Database connection working")
            except Exception as e:
                print(f"❌ Database error: {e}")
            
            # Test claude_ai_novo import
            try:
                from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
                orchestrator = OrchestratorManager()
                print("✅ OrchestratorManager loaded in Flask context")
                
                # Test orchestrator status
                status = orchestrator.get_orchestrator_status()
                print(f"✅ Orchestrator status: {status['total_orchestrators']} orchestrators available")
                
            except Exception as e:
                print(f"❌ OrchestratorManager error: {e}")
                import traceback
                traceback.print_exc()
            
            # Test security guard
            try:
                from app.claude_ai_novo.security.security_guard import get_security_guard
                sg = get_security_guard()
                print(f"✅ SecurityGuard loaded - Production: {sg.is_production}, New system: {sg.new_system_active}")
            except Exception as e:
                print(f"❌ SecurityGuard error: {e}")
            
            # Test transition manager
            try:
                from app.claude_transition import get_transition_manager
                tm = get_transition_manager()
                print(f"✅ TransitionManager loaded - Active system: {tm.sistema_ativo}")
            except Exception as e:
                print(f"❌ TransitionManager error: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ Flask app integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_fallbacks():
    """Test import fallback mechanisms"""
    print("\n🔍 Testing Import Fallbacks...")
    
    # Test system_dependencies
    try:
        from app.claude_ai_novo.system_dependencies import DEPENDENCIES_STATUS
        print("\n📊 Dependencies Status:")
        for dep, status in DEPENDENCIES_STATUS.items():
            symbol = "✅" if status else "❌"
            print(f"  {symbol} {dep}: {'Available' if status else 'Using Mock'}")
    except Exception as e:
        print(f"❌ system_dependencies error: {e}")
    
    # Test specific fallbacks
    test_modules = [
        'app.claude_ai_novo.utils.flask_fallback',
        'app.claude_ai_novo.utils.flask_context_wrapper',
        'app.claude_ai_novo.utils.base_classes',
    ]
    
    for module in test_modules:
        try:
            __import__(module)
            print(f"✅ {module}: Loaded")
        except Exception as e:
            print(f"❌ {module}: {e}")

def test_async_integration():
    """Test async integration patterns"""
    print("\n🔍 Testing Async Integration...")
    
    import asyncio
    
    async def test_orchestrator_async():
        try:
            from app import create_app
            app = create_app()
            
            with app.app_context():
                from app.claude_ai_novo.orchestrators.orchestrator_manager import OrchestratorManager
                orchestrator = OrchestratorManager()
                
                # Test async query processing
                result = await orchestrator.process_query("test query", {"user_id": "test"})
                print(f"✅ Async query processed: {result.get('success', False)}")
                
                if 'error' in result:
                    print(f"   Error: {result['error']}")
                    
                return result
                
        except Exception as e:
            print(f"❌ Async integration error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # Run async test
    try:
        result = asyncio.run(test_orchestrator_async())
        return result is not None
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False

def test_response_extraction():
    """Test response extraction from orchestrator results"""
    print("\n🔍 Testing Response Extraction...")
    
    try:
        from app.claude_transition import ClaudeTransitionManager
        tm = ClaudeTransitionManager()
        
        # Test various response structures
        test_cases = [
            {"success": True, "response": "Simple response"},
            {"success": True, "result": {"response": "Nested response"}},
            {"success": True, "steps_results": {"step1": {"response": "Step response"}}},
            {"success": True, "agent_response": "Agent response"},
            {"success": True, "workflow_result": {"output": "Workflow output"}},
        ]
        
        for i, test_data in enumerate(test_cases):
            extracted = tm._extract_response_from_nested(test_data)
            if extracted:
                print(f"✅ Test case {i+1}: Extracted '{extracted[:50]}...'")
            else:
                print(f"❌ Test case {i+1}: Failed to extract response")
                
        return True
        
    except Exception as e:
        print(f"❌ Response extraction test error: {e}")
        return False

def main():
    """Run all integration tests"""
    print("="*60)
    print("🧪 CLAUDE AI NOVO - INTEGRATION ISSUES TEST")
    print("="*60)
    
    results = {
        'flask_app': test_flask_app_integration(),
        'import_fallbacks': test_import_fallbacks(),
        'async_integration': test_async_integration(),
        'response_extraction': test_response_extraction(),
    }
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())