#!/usr/bin/env python3
"""
🚀 Script para garantir que todas as funcionalidades do Claude AI funcionem
"""

import os
import sys
import json
from datetime import datetime

def ensure_directories():
    """Garante que todos os diretórios necessários existam"""
    directories = [
        "instance/claude_ai",
        "instance/claude_ai/backups",
        "instance/claude_ai/backups/generated",
        "instance/claude_ai/backups/projects",
        "app/claude_ai/logs",
        "ml_models",
        "logs",
        "uploads"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Diretório garantido: {directory}")

def ensure_security_config():
    """Garante que security_config.json existe"""
    security_config_path = "instance/claude_ai/security_config.json"
    
    if not os.path.exists(security_config_path):
        security_config = {
            "allowed_commands": [
                "descobrir_projeto",
                "ler_arquivo",
                "criar_modulo",
                "inspecionar_banco",
                "listar_diretorio"
            ],
            "blocked_paths": [
                "/etc/",
                "/usr/",
                "/bin/",
                ".git/",
                "__pycache__/",
                "venv/",
                ".env"
            ],
            "max_file_size_mb": 10,
            "allowed_extensions": [
                ".py", ".html", ".css", ".js", ".json", 
                ".md", ".txt", ".yml", ".yaml", ".sql"
            ],
            "rate_limits": {
                "max_commands_per_minute": 30,
                "max_file_reads_per_minute": 50
            }
        }
        
        with open(security_config_path, 'w', encoding='utf-8') as f:
            json.dump(security_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ security_config.json criado em {security_config_path}")
    else:
        print(f"✅ security_config.json já existe")

def test_imports():
    """Testa se todos os imports funcionam sem circular import"""
    print("\n🔍 Testando imports do Claude AI...")
    
    try:
        # Teste 1: Importar claude_real_integration primeiro
        from app.claude_ai.claude_real_integration import ClaudeRealIntegration
        print("✅ claude_real_integration importado com sucesso")
        
        # Teste 2: Importar enhanced_claude_integration
        from app.claude_ai.enhanced_claude_integration import get_enhanced_claude_system
        print("✅ enhanced_claude_integration importado com sucesso")
        
        # Teste 3: Instanciar ClaudeRealIntegration
        claude = ClaudeRealIntegration()
        print("✅ ClaudeRealIntegration instanciado")
        
        # Teste 4: Verificar se enhanced_claude foi carregado
        if hasattr(claude, 'enhanced_claude') and claude.enhanced_claude:
            print("✅ Enhanced Claude carregado com sucesso!")
        else:
            print("⚠️ Enhanced Claude não carregado (pode ser falta de API key)")
        
        # Teste 5: Listar todos os sistemas carregados
        sistemas = [
            ('multi_agent_system', 'Sistema Multi-Agente'),
            ('advanced_ai_system', 'Sistema IA Avançado'),
            ('nlp_analyzer', 'NLP Avançado'),
            ('intelligent_analyzer', 'Analisador Inteligente'),
            ('enhanced_claude', 'Enhanced Claude'),
            ('suggestion_engine', 'Suggestion Engine'),
            ('ml_models', 'Modelos ML'),
            ('human_learning', 'Human-in-Loop Learning'),
            ('input_validator', 'Input Validator'),
            ('ai_config', 'AI Configuration'),
            ('alert_engine', 'Alert Engine'),
            ('mapeamento_semantico', 'Mapeamento Semântico')
        ]
        
        print("\n📊 Status dos Sistemas:")
        for attr, nome in sistemas:
            if hasattr(claude, attr) and getattr(claude, attr):
                print(f"✅ {nome}")
            else:
                print(f"❌ {nome}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def create_test_script():
    """Cria script de teste para verificar funcionalidades"""
    test_script = '''#!/usr/bin/env python3
"""
Script de teste para verificar Claude AI
"""

from app.claude_ai.claude_real_integration import ClaudeRealIntegration

# Testar processamento de consulta
claude = ClaudeRealIntegration()

# Teste 1: Consulta simples
print("\\n=== TESTE 1: Consulta Simples ===")
resposta = claude.processar_consulta_real("Quantas entregas temos hoje?")
print(f"Resposta: {resposta[:200]}...")

# Teste 2: Consulta sobre memória vitalícia
print("\\n=== TESTE 2: Memória Vitalícia ===")
resposta = claude.processar_consulta_real("O que você tem guardado na memória vitalícia?")
print(f"Resposta: {resposta[:200]}...")

# Teste 3: Comando automático
print("\\n=== TESTE 3: Comando Automático ===")
resposta = claude.processar_consulta_real("Quero descobrir o projeto atual")
print(f"Resposta: {resposta[:200]}...")

print("\\n✅ Testes concluídos!")
'''
    
    with open('test_claude_ai.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("✅ Script de teste criado: test_claude_ai.py")

def main():
    """Função principal"""
    print("🚀 Garantindo que Claude AI funcione corretamente")
    print("=" * 50)
    
    # 1. Garantir diretórios
    ensure_directories()
    
    # 2. Garantir security_config.json
    ensure_security_config()
    
    # 3. Testar imports
    if test_imports():
        print("\n✅ SUCESSO! Todos os imports funcionam!")
        
        # 4. Criar script de teste
        create_test_script()
        
        print("\n📝 Próximos passos:")
        print("1. Execute: python test_claude_ai.py")
        print("2. Faça commit das mudanças")
        print("3. Execute: git push")
        print("4. O Render fará deploy automático")
        
    else:
        print("\n❌ Problemas detectados. Revise os logs acima.")

if __name__ == "__main__":
    main() 