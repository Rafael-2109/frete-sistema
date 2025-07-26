#!/usr/bin/env python3
"""
Testa sintaxe do context_loader.py
"""

import ast

print("🔍 Testando sintaxe de context_loader.py...")

try:
    with open('app/claude_ai_novo/loaders/context_loader.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Testar sintaxe
    ast.parse(content)
    print("✅ context_loader.py - Sintaxe OK!")
    
except SyntaxError as e:
    print(f"❌ Erro de sintaxe: {e}")
    print(f"   Linha {e.lineno}: {e.text}")
    print(f"   {' ' * (e.offset - 1)}^")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n💡 Se ainda houver erro, execute o servidor Flask para ver o erro completo.")