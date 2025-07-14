#!/usr/bin/env python3
"""
Script para analisar problemas específicos do ambiente Render
"""

import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verificar_variaveis_ambiente():
    """Verifica variáveis de ambiente necessárias"""
    print("\n🔍 1. Verificando variáveis de ambiente...")
    
    variaveis_criticas = [
        'DATABASE_URL',
        'ANTHROPIC_API_KEY',
        'SECRET_KEY',
        'FLASK_APP',
        'REDIS_URL'
    ]
    
    variaveis_faltando = []
    variaveis_presentes = []
    
    for var in variaveis_criticas:
        valor = os.getenv(var)
        if valor:
            # Mascarar valores sensíveis
            if 'KEY' in var or 'PASSWORD' in var or 'URL' in var:
                valor_mascarado = valor[:10] + '...' if len(valor) > 10 else '***'
                print(f"   ✅ {var}: {valor_mascarado}")
            else:
                print(f"   ✅ {var}: {valor}")
            variaveis_presentes.append(var)
        else:
            print(f"   ❌ {var}: NÃO CONFIGURADA")
            variaveis_faltando.append(var)
    
    return variaveis_faltando

def verificar_conexao_banco():
    """Testa conexão com o banco de dados"""
    print("\n🔍 2. Testando conexão com banco de dados...")
    
    try:
        from app.claude_ai_novo.scanning.database.database_connection import DatabaseConnection
        
        db_conn = DatabaseConnection()
        
        if db_conn.is_connected():
            print("   ✅ Conexão estabelecida com sucesso")
            info = db_conn.get_connection_info()
            print(f"   📊 Método: {info.get('method', 'N/A')}")
            print(f"   📊 Testada: {info.get('tested', False)}")
            
            # Tentar listar tabelas
            if db_conn.is_inspector_available():
                print("   ✅ Inspector disponível")
            else:
                print("   ⚠️ Inspector não disponível (pode ser problema de encoding UTF-8)")
        else:
            print("   ❌ Não foi possível conectar ao banco")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar conexão: {e}")
        
def verificar_contexto_flask():
    """Verifica se o contexto Flask está disponível"""
    print("\n🔍 3. Verificando contexto Flask...")
    
    try:
        from flask import current_app
        
        if current_app:
            print("   ✅ Contexto Flask disponível")
        else:
            print("   ❌ Contexto Flask não disponível")
    except:
        print("   ⚠️ Flask não está em contexto de aplicação")
        print("   💡 Isso é normal fora do servidor web")

def verificar_loaders():
    """Testa os loaders de dados"""
    print("\n🔍 4. Testando loaders de dados...")
    
    try:
        from app.claude_ai_novo.loaders.loader_manager import LoaderManager
        
        loader_manager = LoaderManager()
        
        # Testar loader de entregas
        resultado = loader_manager.load_data_by_domain('entregas', {
            'cliente': 'Atacadão',
            'periodo': 30
        })
        
        if resultado.get('success'):
            total = len(resultado.get('data', []))
            is_mock = resultado.get('is_mock', False)
            print(f"   ✅ Loader de entregas funcionando")
            print(f"   📊 Total de registros: {total}")
            print(f"   📊 Dados mock: {'Sim' if is_mock else 'Não'}")
        else:
            print("   ❌ Loader de entregas falhou")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar loaders: {e}")

def verificar_claude_api():
    """Verifica se a API do Claude está configurada"""
    print("\n🔍 5. Verificando API do Claude...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if api_key:
        print("   ✅ ANTHROPIC_API_KEY configurada")
        print(f"   📊 Tamanho da chave: {len(api_key)} caracteres")
        
        # Verificar formato básico
        if api_key.startswith('sk-'):
            print("   ✅ Formato da chave parece correto")
        else:
            print("   ⚠️ Formato da chave pode estar incorreto")
    else:
        print("   ❌ ANTHROPIC_API_KEY não configurada")
        print("   💡 Sistema usará modo fallback")

def analisar_encodings():
    """Analisa problemas de encoding UTF-8"""
    print("\n🔍 6. Analisando problemas de encoding...")
    
    # Verificar encoding do sistema
    print(f"   📊 Encoding padrão: {sys.getdefaultencoding()}")
    print(f"   📊 Encoding do filesystem: {sys.getfilesystemencoding()}")
    
    # Verificar DATABASE_URL
    db_url = os.getenv('DATABASE_URL', '')
    if db_url:
        if 'client_encoding=utf8' in db_url:
            print("   ✅ DATABASE_URL já tem client_encoding=utf8")
        else:
            print("   ⚠️ DATABASE_URL sem client_encoding=utf8")
            print("   💡 Adicione ?client_encoding=utf8 à URL")
    
    # Testar caracteres problemáticos
    teste_chars = ['ã', 'ç', 'é', 'ô', 'ú']
    try:
        for char in teste_chars:
            char.encode('utf-8')
        print("   ✅ Encoding UTF-8 funcionando corretamente")
    except:
        print("   ❌ Problemas com encoding UTF-8")

def gerar_recomendacoes(variaveis_faltando):
    """Gera recomendações baseadas nos problemas encontrados"""
    print("\n" + "="*80)
    print("💡 RECOMENDAÇÕES PARA O RENDER")
    print("="*80)
    
    if variaveis_faltando:
        print("\n⚠️ Variáveis de ambiente faltando:")
        for var in variaveis_faltando:
            print(f"   - Configure {var} no painel do Render")
    
    print("\n📋 Checklist para deploy no Render:")
    print("   1. ✅ Verificar todas as variáveis de ambiente")
    print("   2. ✅ DATABASE_URL deve incluir ?client_encoding=utf8")
    print("   3. ✅ ANTHROPIC_API_KEY deve estar configurada")
    print("   4. ✅ Usar Python 3.11+ no Render")
    print("   5. ✅ requirements.txt deve incluir psycopg2-binary")
    
    print("\n🚀 Comandos úteis no Render:")
    print("   - Build Command: pip install -r requirements.txt")
    print("   - Start Command: gunicorn app:app")
    
    print("\n📊 Monitoramento:")
    print("   - Verificar logs no painel do Render")
    print("   - Procurar por 'ERROR' ou 'CRITICAL'")
    print("   - Monitorar uso de memória")

def main():
    print("🚀 Análise de Problemas Específicos do Render")
    print("="*80)
    
    # Executar verificações
    variaveis_faltando = verificar_variaveis_ambiente()
    verificar_conexao_banco()
    verificar_contexto_flask()
    verificar_loaders()
    verificar_claude_api()
    analisar_encodings()
    
    # Gerar recomendações
    gerar_recomendacoes(variaveis_faltando)
    
    print("\n" + "="*80)
    if not variaveis_faltando:
        print("✅ Sistema está pronto para o Render!")
    else:
        print("⚠️ Configure as variáveis faltantes antes do deploy!")
    print("="*80)

if __name__ == "__main__":
    main() 