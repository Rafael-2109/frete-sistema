#!/usr/bin/env python3
"""
Script executado ANTES de iniciar a aplicação
Garante que os tipos PostgreSQL sejam registrados e inicializa o estoque
"""
import os
import sys
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

print("🔥 PRE-START: Iniciando configurações pré-aplicação...")

# 1. Configurar encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
print("✅ PRE-START: Encoding UTF-8 configurado")

# 2. Verificar e corrigir DATABASE_URL
database_url = os.getenv('DATABASE_URL', '')
if database_url:
    # Corrigir URL do PostgreSQL se necessário
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        os.environ['DATABASE_URL'] = database_url
        print("✅ PRE-START: DATABASE_URL corrigida para postgresql://")
    
    # Adicionar encoding se não existir
    if 'client_encoding' not in database_url:
        if '?' in database_url:
            database_url += '&client_encoding=utf8'
        else:
            database_url += '?client_encoding=utf8'
        os.environ['DATABASE_URL'] = database_url
    
    print(f"✅ PRE-START: DATABASE_URL configurada: {database_url[:30]}...")
else:
    print("⚠️ PRE-START: DATABASE_URL não encontrada")

# 3. Registrar tipos PostgreSQL
if 'postgres' in database_url:
    try:
        import psycopg2
        from psycopg2 import extensions
        
        # Registrar tipos PostgreSQL globalmente
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
        extensions.register_type(DATE)
        
        TIME = extensions.new_type((1083,), "TIME", extensions.TIME)
        extensions.register_type(TIME)
        
        TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMP)
        
        TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
        extensions.register_type(TIMESTAMPTZ)
        
        DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
        extensions.register_type(DATEARRAY)
        
        print("✅ PRE-START: Tipos PostgreSQL registrados com sucesso!")
    except Exception as e:
        print(f"⚠️ PRE-START: Erro ao registrar tipos PostgreSQL: {e}")

# 4. Inicializar Sistema de Estoque em Tempo Real
if os.getenv('INIT_ESTOQUE_TEMPO_REAL', 'true').lower() == 'true':
    print("\n📦 PRE-START: Inicializando Sistema de Estoque em Tempo Real...")
    try:
        # Adicionar o diretório ao path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Importar e executar o script de inicialização
        from init_render_estoque import main as init_estoque
        
        resultado = init_estoque()
        
        if resultado == 0:
            print("✅ PRE-START: Sistema de estoque inicializado com sucesso!")
        else:
            print("⚠️ PRE-START: Sistema de estoque teve problemas na inicialização")
            
    except ImportError as e:
        print(f"⚠️ PRE-START: Script de inicialização do estoque não encontrado: {e}")
    except Exception as e:
        print(f"⚠️ PRE-START: Erro ao inicializar estoque: {e}")
        # Não falhar completamente - permitir que a aplicação inicie
else:
    print("ℹ️ PRE-START: Inicialização do estoque desabilitada (INIT_ESTOQUE_TEMPO_REAL=false)")

print("\n✅ PRE-START: Configurações pré-aplicação concluídas!")