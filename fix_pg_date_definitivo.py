#!/usr/bin/env python3
"""
Solução definitiva para erro PG 1082 - Tipo DATE PostgreSQL

Este script diagnostica e corrige o problema na raiz, removendo soluções paliativas.
"""

import os
import sys
import psycopg2
from psycopg2 import extensions

def diagnosticar_problema():
    """Diagnostica a causa raiz do problema PG 1082"""
    print("=== DIAGNÓSTICO DO PROBLEMA PG 1082 ===\n")
    
    # 1. Verificar versão do psycopg2
    print(f"1. Versão do psycopg2: {psycopg2.__version__}")
    versao_parts = psycopg2.__version__.split()[0].split('.')
    versao_major = int(versao_parts[0])
    versao_minor = int(versao_parts[1]) if len(versao_parts) > 1 else 0
    
    if versao_major < 2 or (versao_major == 2 and versao_minor < 8):
        print("   ⚠️ PROBLEMA: Versão antiga do psycopg2!")
        print("   ✅ SOLUÇÃO: Atualizar para psycopg2>=2.8")
        return False
    
    # 2. Verificar se tipos estão registrados
    print("\n2. Verificando tipos registrados...")
    tipos_necessarios = {
        1082: "DATE",
        1083: "TIME", 
        1114: "TIMESTAMP",
        1184: "TIMESTAMPTZ"
    }
    
    tipos_faltando = []
    for oid, nome in tipos_necessarios.items():
        if oid not in extensions.string_types:
            tipos_faltando.append((oid, nome))
            print(f"   ❌ Tipo {nome} (OID {oid}) NÃO registrado")
        else:
            print(f"   ✅ Tipo {nome} (OID {oid}) registrado")
    
    if tipos_faltando:
        print("\n   ⚠️ PROBLEMA: Tipos não registrados no psycopg2")
        print("   ✅ SOLUÇÃO: Registrar tipos antes de criar conexões")
        return False
    
    # 3. Testar conexão real
    print("\n3. Testando conexão com banco...")
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("   ❌ DATABASE_URL não encontrada")
            return False
            
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Teste simples
        cur.execute("SELECT CURRENT_DATE::date")
        result = cur.fetchone()
        print(f"   ✅ Query executada: {result[0]} (tipo: {type(result[0])})")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
        return False

def aplicar_solucao_definitiva():
    """Aplica a solução definitiva e limpa do problema"""
    print("\n=== APLICANDO SOLUÇÃO DEFINITIVA ===\n")
    
    # 1. Registrar tipos corretamente (sem conversões desnecessárias)
    print("1. Registrando tipos PostgreSQL...")
    
    # Para DATE - usar DATEOID do psycopg2 se disponível
    try:
        from psycopg2.extensions import DATEOID
        DATE = extensions.new_type((DATEOID,), "DATE", extensions.DATE)
    except:
        # Fallback para versões antigas
        DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
    
    extensions.register_type(DATE)
    print("   ✅ Tipo DATE registrado corretamente")
    
    # Registrar outros tipos
    TIME = extensions.new_type((1083,), "TIME", extensions.TIME)
    extensions.register_type(TIME)
    
    TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
    extensions.register_type(TIMESTAMP)
    
    TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
    extensions.register_type(TIMESTAMPTZ)
    
    print("   ✅ Todos os tipos registrados")
    
    # 2. Criar arquivo de configuração limpo
    print("\n2. Criando configuração limpa...")
    
    config_content = '''"""
Configuração limpa para tipos PostgreSQL
"""

import psycopg2
from psycopg2 import extensions

def registrar_tipos_postgresql():
    """Registra tipos PostgreSQL de forma limpa e eficiente"""
    # Registrar adaptadores de tipos Python -> PostgreSQL
    from psycopg2.extensions import register_adapter, adapt, AsIs
    from datetime import date, time, datetime
    
    # Registrar tipos PostgreSQL -> Python
    DATE = extensions.new_type((1082,), "DATE", extensions.DATE)
    TIME = extensions.new_type((1083,), "TIME", extensions.TIME) 
    TIMESTAMP = extensions.new_type((1114,), "TIMESTAMP", extensions.PYDATETIME)
    TIMESTAMPTZ = extensions.new_type((1184,), "TIMESTAMPTZ", extensions.PYDATETIME)
    
    # Arrays
    DATEARRAY = extensions.new_array_type((1182,), "DATEARRAY", DATE)
    TIMEARRAY = extensions.new_array_type((1183,), "TIMEARRAY", TIME)
    
    # Registrar globalmente
    for tipo in [DATE, TIME, TIMESTAMP, TIMESTAMPTZ, DATEARRAY, TIMEARRAY]:
        extensions.register_type(tipo)
    
    return True

# Executar ao importar
registrar_tipos_postgresql()
'''
    
    with open('app/utils/pg_types_config.py', 'w') as f:
        f.write(config_content)
    
    print("   ✅ Arquivo de configuração criado")
    
    # 3. Instruções para limpeza
    print("\n3. INSTRUÇÕES PARA LIMPEZA:")
    print("   a) Remover do app/__init__.py:")
    print("      - Funções cast_date e cast_timestamp")
    print("      - Event listener register_pg_types")
    print("      - Registro manual de tipos")
    print("   ")
    print("   b) Simplificar filtros Jinja2:")
    print("      - Remover safe_date_format")
    print("      - Usar apenas formatar_data_brasil")
    print("   ")
    print("   c) No início do app/__init__.py adicionar:")
    print("      from app.utils.pg_types_config import registrar_tipos_postgresql")
    print("   ")
    print("   d) requirements.txt deve ter:")
    print("      psycopg2-binary>=2.9.0")

def main():
    """Executa diagnóstico e solução"""
    print("SOLUÇÃO DEFINITIVA PARA ERRO PG 1082\n")
    
    # Diagnóstico
    if diagnosticar_problema():
        print("\n✅ Sistema está funcionando corretamente!")
        print("   Considere remover soluções paliativas para simplificar o código.")
    else:
        print("\n⚠️ Problemas detectados!")
        
    # Aplicar solução
    aplicar_solucao_definitiva()
    
    print("\n=== CONCLUSÃO ===")
    print("A solução definitiva foi preparada.")
    print("Siga as instruções acima para limpar o código.")

if __name__ == "__main__":
    main()