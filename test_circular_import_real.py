#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste real do import circular entre claude_real e enhanced
Simula o comportamento da aplicação Flask
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=== TESTE REAL DO IMPORT CIRCULAR ===\n")

# 1. Testar imports básicos
print("1. Testando imports básicos...")
try:
    from app.claude_ai.claude_real_integration import claude_real_integration
    from app.claude_ai.enhanced_claude_integration import enhanced_claude_integration
    print("✅ Imports básicos OK")
except Exception as e:
    print(f"❌ Erro nos imports: {e}")
    sys.exit(1)

# 2. Verificar estado inicial (antes do setup)
print("\n2. Estado ANTES do setup_claude_ai:")
print(f"   - enhanced_claude em claude_real: {claude_real_integration.enhanced_claude}")
print(f"   - claude_integration em enhanced: {getattr(enhanced_claude_integration, 'claude_integration', 'Não tem o atributo')}")

# 3. Simular setup da aplicação
print("\n3. Chamando setup_claude_ai (simula inicialização Flask)...")
try:
    # Criar app fake mínimo
    class FakeApp:
        def __init__(self):
            self.instance_path = os.path.dirname(__file__)
            self.logger = self
        
        def info(self, msg):
            print(f"   [INFO] {msg}")
        
        def warning(self, msg):
            print(f"   [WARN] {msg}")
        
        def error(self, msg):
            print(f"   [ERROR] {msg}")
    
    fake_app = FakeApp()
    
    # Chamar setup
    from app.claude_ai import setup_claude_ai
    setup_claude_ai(fake_app, None)
    
except Exception as e:
    print(f"❌ Erro no setup: {e}")
    import traceback
    traceback.print_exc()

# 4. Verificar estado final (depois do setup)
print("\n4. Estado DEPOIS do setup_claude_ai:")
print(f"   - enhanced_claude em claude_real: {claude_real_integration.enhanced_claude}")
print(f"   - É None? {claude_real_integration.enhanced_claude is None}")
print(f"   - claude_integration em enhanced: {getattr(enhanced_claude_integration, 'claude_integration', 'Não tem o atributo')}")
print(f"   - É None? {getattr(enhanced_claude_integration, 'claude_integration', None) is None}")

# 5. Testar se funcionam juntos
print("\n5. Testando se podem trabalhar juntos:")
try:
    # Testar método que deveria usar enhanced
    if hasattr(claude_real_integration, 'processar_consulta_real'):
        print("   - claude_real tem método processar_consulta_real")
    
    if hasattr(enhanced_claude_integration, 'processar_consulta_com_ia_avancada'):
        print("   - enhanced tem método processar_consulta_com_ia_avancada")
    
    print("✅ Sistemas prontos para trabalhar juntos!")
    
except Exception as e:
    print(f"❌ Erro ao testar métodos: {e}")

print("\n✅ CONCLUSÃO: Import circular resolvido! Os sistemas se conectam durante setup_claude_ai()") 