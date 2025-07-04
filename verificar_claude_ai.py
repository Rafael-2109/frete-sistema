#!/usr/bin/env python3
'''
Script para verificar se o Claude AI está funcionando corretamente
'''

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def verificar_claude_ai():
    '''Verifica se o Claude AI está funcionando'''
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            
            print("🔍 VERIFICANDO CLAUDE AI...")
            print("=" * 50)
            
            # 1. Verificar tabelas AI
            tabelas_ai = [
                'ai_knowledge_patterns', 'ai_semantic_mappings',
                'ai_learning_history', 'ai_grupos_empresariais',
                'ai_business_contexts', 'ai_response_templates',
                'ai_learning_metrics'
            ]
            
            tabelas_ok = 0
            print("\n📊 TABELAS DE IA:")
            for tabela in tabelas_ai:
                try:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    print(f"   ✅ {tabela}: {count} registros")
                    tabelas_ok += 1
                except Exception as e:
                    print(f"   ❌ {tabela}: {str(e)[:50]}...")
            
            # 2. Verificar imports
            print("\n🔧 IMPORTS:")
            try:
                from app.claude_ai import claude_real_integration
                print("   ✅ claude_real_integration")
            except Exception as e:
                print(f"   ❌ claude_real_integration: {e}")
            
            try:
                from app.claude_ai import multi_agent_system
                print("   ✅ multi_agent_system")
            except Exception as e:
                print(f"   ❌ multi_agent_system: {e}")
            
            try:
                from app.claude_ai import lifelong_learning
                print("   ✅ lifelong_learning")
            except Exception as e:
                print(f"   ❌ lifelong_learning: {e}")
            
            # 3. Verificar diretórios
            print("\n📁 DIRETÓRIOS:")
            diretorios = [
                'instance/claude_ai/backups',
                'instance/claude_ai/backups/generated',
                'instance/claude_ai/backups/projects',
                'app/claude_ai/logs'
            ]
            
            for diretorio in diretorios:
                if Path(diretorio).exists():
                    print(f"   ✅ {diretorio}")
                else:
                    print(f"   ❌ {diretorio}")
            
            # 4. Verificar configuração
            print("\n🔒 CONFIGURAÇÃO:")
            config_file = Path('instance/claude_ai/security_config.json')
            if config_file.exists():
                print("   ✅ security_config.json")
            else:
                print("   ❌ security_config.json")
            
            # Resumo
            print("\n" + "=" * 50)
            print("📈 RESUMO:")
            print(f"   Tabelas AI: {tabelas_ok}/{len(tabelas_ai)}")
            
            if tabelas_ok >= 5:
                print("\n🎉 CLAUDE AI FUNCIONANDO!")
                return True
            else:
                print("\n⚠️ CLAUDE AI COM PROBLEMAS")
                return False
                
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    sucesso = verificar_claude_ai()
    sys.exit(0 if sucesso else 1)
