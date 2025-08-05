#!/usr/bin/env python3
"""
Script executado ANTES de iniciar a aplicação
Garante que os tipos PostgreSQL sejam registrados
"""
import os
import sys

print("🔥 PRE-START: Iniciando configurações pré-aplicação...")

# 1. Registrar tipos PostgreSQL
try:
    import register_pg_types
    print("✅ PRE-START: Tipos PostgreSQL registrados com sucesso!")
except Exception as e:
    print(f"⚠️ PRE-START: Erro ao registrar tipos PostgreSQL: {e}")

# 2. Verificar variáveis de ambiente
if os.getenv('DATABASE_URL'):
    print(f"✅ PRE-START: DATABASE_URL detectada: {os.getenv('DATABASE_URL')[:30]}...")
else:
    print("⚠️ PRE-START: DATABASE_URL não encontrada")

# 3. Configurar encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
print("✅ PRE-START: Encoding UTF-8 configurado")

print("✅ PRE-START: Configurações concluídas!")