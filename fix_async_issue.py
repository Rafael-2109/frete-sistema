#!/usr/bin/env python3
"""
Script para adicionar nest_asyncio ao projeto
Resolve conflito de Playwright Sync em loop asyncio
"""

# Adicionar ao início de app/__init__.py ou app/portal/routes_sessao.py
codigo_correcao = '''
# Fix para Playwright Sync em loop asyncio
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    # Se nest_asyncio não estiver instalado
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nest_asyncio"])
    import nest_asyncio
    nest_asyncio.apply()
'''

print("=" * 60)
print("CORREÇÃO PARA PLAYWRIGHT ASYNC")
print("=" * 60)
print()
print("1. Instale nest_asyncio:")
print("   pip install nest_asyncio")
print()
print("2. Adicione este código no início de app/__init__.py:")
print()
print(codigo_correcao)
print()
print("3. Ou execute este comando para instalar automaticamente:")
print("   pip install nest_asyncio && echo 'import nest_asyncio; nest_asyncio.apply()' >> app/__init__.py")
print()
print("=" * 60)