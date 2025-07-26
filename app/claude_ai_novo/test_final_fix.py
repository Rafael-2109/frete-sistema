#!/usr/bin/env python3
"""
Teste final após correção do flask_fallback.py
"""

import sys
import os
from datetime import datetime

# Adicionar diretórios ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

print("🧪 TESTE FINAL - CORREÇÃO flask_fallback.py")
print("="*60)
print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("="*60)

# Testar import do flask_fallback
print("\n✓ Testando import de flask_fallback.py...")
try:
    from app.claude_ai_novo.utils.flask_fallback import FlaskFallback
    print("  ✅ Import bem-sucedido!")
    
    # Testar instanciação
    fallback = FlaskFallback()
    print("  ✅ FlaskFallback instanciado!")
    
    # Testar método get_current_user
    user = fallback.get_current_user()
    print(f"  ✅ get_current_user() retornou: {user}")
    
except Exception as e:
    print(f"  ❌ Erro: {e}")

# Testar sistema de transição
print("\n✓ Testando sistema de transição...")
try:
    from app.claude_transition import ClaudeAITransition
    transition = ClaudeAITransition()
    
    # Testar inicialização
    init_result = transition.inicializar_sistema()
    
    print(f"  📊 Sistema novo OK: {init_result['sistema_novo_ok']}")
    print(f"  📊 Sistema antigo OK: {init_result['sistema_antigo_ok']}")
    print(f"  📊 Sistema ativo: {init_result['sistema_ativo']}")
    
    if not init_result['sistema_novo_ok']:
        print(f"  ⚠️ Erro no sistema novo: {init_result.get('erro_novo', 'N/A')}")
    
except Exception as e:
    print(f"  ❌ Erro ao testar transição: {e}")

print("\n" + "="*60)
print("✅ CORREÇÃO APLICADA:")
print("  - flask_fallback.py linha 283: removido try duplicado")
print("  - flask_fallback.py linha 285-290: removido código duplicado")
print("="*60)
print("\n💡 Reinicie o servidor Flask para aplicar a correção!")