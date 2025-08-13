#!/usr/bin/env python3
"""
Fix para erro SSL do PostgreSQL
================================

Corrige o erro: SSL error: decryption failed or bad record mac

Este erro ocorre quando há problemas na comunicação SSL entre a aplicação e o PostgreSQL.
Soluções implementadas:
1. Adiciona retry logic para operações de banco
2. Configura SSL adequadamente
3. Implementa pool de conexões mais robusto
"""

import os
import sys
import time
from functools import wraps
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_ssl_error(max_retries=3, delay=1):
    """
    Decorator para retry em caso de erro SSL
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if 'SSL' in str(e) or 'decryption failed' in str(e):
                        last_exception = e
                        logger.warning(f"Tentativa {attempt + 1}/{max_retries} falhou com erro SSL. Aguardando {delay}s...")
                        time.sleep(delay)
                        # Aumenta o delay exponencialmente
                        delay *= 2
                    else:
                        raise
            # Se todas as tentativas falharam
            logger.error(f"Todas as {max_retries} tentativas falharam")
            raise last_exception
        return wrapper
    return decorator

def fix_database_url():
    """
    Corrige a URL do banco para incluir parâmetros SSL adequados
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL não encontrada")
        return None
    
    # Se for PostgreSQL
    if database_url.startswith(('postgresql://', 'postgres://')):
        # Remove parâmetros existentes de SSL
        if '?' in database_url:
            base_url = database_url.split('?')[0]
            existing_params = database_url.split('?')[1] if '?' in database_url else ''
        else:
            base_url = database_url
            existing_params = ''
        
        # Novos parâmetros SSL
        ssl_params = [
            'sslmode=require',  # Ou 'prefer' para ser menos restritivo
            'sslcert=',  # Vazio para usar padrão
            'sslkey=',   # Vazio para usar padrão
            'sslrootcert=',  # Vazio para usar padrão
            'connect_timeout=30',
            'keepalives=1',
            'keepalives_idle=30',
            'keepalives_interval=10',
            'keepalives_count=5'
        ]
        
        # Combina parâmetros
        all_params = ssl_params
        if existing_params:
            # Filtra parâmetros SSL existentes
            for param in existing_params.split('&'):
                if not any(param.startswith(ssl) for ssl in ['ssl', 'keepalive']):
                    all_params.append(param)
        
        # Monta URL final
        fixed_url = f"{base_url}?{'&'.join(all_params)}"
        logger.info(f"URL corrigida com parâmetros SSL")
        return fixed_url
    
    return database_url

def test_connection():
    """
    Testa a conexão com o banco
    """
    fixed_url = fix_database_url()
    if not fixed_url:
        return False
    
    try:
        # Cria engine com configurações otimizadas
        engine = create_engine(
            fixed_url,
            pool_pre_ping=True,  # Testa conexão antes de usar
            pool_recycle=300,    # Recicla conexões a cada 5 minutos
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            echo=False
        )
        
        # Testa conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Conexão testada com sucesso!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexão: {e}")
        return False

def apply_fix_to_config():
    """
    Aplica correções ao arquivo config.py
    """
    config_file = 'config.py'
    
    # Lê o arquivo atual
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Adiciona configurações SSL se não existirem
    ssl_config = """
    # Configurações SSL para PostgreSQL (corrige erro de decryption)
    if IS_POSTGRESQL:
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["sslmode"] = "prefer"  # ou "require"
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["sslcontext"] = ssl_context
        
        # Configurações de keep-alive para evitar timeout
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["keepalives"] = 1
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["keepalives_idle"] = 30
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["keepalives_interval"] = 10
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"]["keepalives_count"] = 5
"""
    
    if "sslmode" not in content:
        logger.info("Adicionando configurações SSL ao config.py...")
        # Adiciona antes do final da classe Config
        # Procura por um bom lugar para inserir
        insertion_point = content.find("# Configurações condicionais baseadas no tipo de banco")
        if insertion_point == -1:
            insertion_point = content.find("class Config:")
            if insertion_point != -1:
                insertion_point = content.find("\n", insertion_point) + 1
        
        if insertion_point != -1:
            content = content[:insertion_point] + ssl_config + "\n" + content[insertion_point:]
            
            # Salva backup
            with open(config_file + '.backup', 'w') as f:
                f.write(content)
            
            logger.info("✅ Backup criado: config.py.backup")
            logger.info("📝 Para aplicar as correções, adicione as configurações SSL manualmente ao config.py")
            
            print("\n" + "="*60)
            print("ADICIONE ESTAS CONFIGURAÇÕES AO config.py:")
            print("="*60)
            print(ssl_config)
            print("="*60)
    else:
        logger.info("Configurações SSL já existem no config.py")

def create_retry_wrapper():
    """
    Cria um wrapper para operações de banco com retry automático
    """
    
    wrapper_code = '''
# Adicione este código ao arquivo onde ocorre o erro (carteira/routes.py ou similar)

from functools import wraps
import time
from sqlalchemy.exc import OperationalError
import logging

logger = logging.getLogger(__name__)

def retry_database_operation(max_retries=3, delay=1):
    """
    Decorator para retry automático em operações de banco
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    error_msg = str(e)
                    if 'SSL' in error_msg or 'decryption failed' in error_msg:
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(f"Erro SSL na tentativa {attempt + 1}/{max_retries}. Aguardando {current_delay}s...")
                            time.sleep(current_delay)
                            current_delay *= 2  # Backoff exponencial
                            
                            # Força reconexão
                            try:
                                from app import db
                                db.session.rollback()
                                db.session.close()
                                db.engine.dispose()
                            except:
                                pass
                    else:
                        raise
            
            # Se todas as tentativas falharam
            logger.error(f"Todas as {max_retries} tentativas falharam com erro SSL")
            raise last_exception
        return wrapper
    return decorator

# Exemplo de uso:
# @retry_database_operation(max_retries=3)
# def atualizar_carteira():
#     # seu código aqui
#     db.session.commit()
'''
    
    print("\n" + "="*60)
    print("WRAPPER PARA RETRY AUTOMÁTICO:")
    print("="*60)
    print(wrapper_code)
    print("="*60)

def main():
    """
    Executa as correções
    """
    print("🔧 CORREÇÃO DE ERRO SSL DO POSTGRESQL")
    print("="*60)
    
    # 1. Testa conexão atual
    print("\n1. Testando conexão atual...")
    test_connection()
    
    # 2. Sugere correções para config.py
    print("\n2. Verificando config.py...")
    apply_fix_to_config()
    
    # 3. Cria wrapper para retry
    print("\n3. Criando wrapper para retry automático...")
    create_retry_wrapper()
    
    print("\n" + "="*60)
    print("📋 RESUMO DAS SOLUÇÕES:")
    print("="*60)
    print("""
    1. SOLUÇÃO RÁPIDA (Temporária):
       - Reinicie o servidor/aplicação
       - O erro geralmente é temporário e causado por timeout
    
    2. SOLUÇÃO PERMANENTE:
       - Adicione as configurações SSL ao config.py
       - Use o decorator retry_database_operation nas operações críticas
       - Configure os parâmetros de keep-alive
    
    3. VARIÁVEIS DE AMBIENTE (adicione ao .env ou Render):
       PGSSLMODE=prefer
       PGCONNECT_TIMEOUT=30
       
    4. SE O ERRO PERSISTIR:
       - Verifique se o certificado SSL do servidor está válido
       - Considere usar sslmode=disable temporariamente (não recomendado para produção)
       - Verifique os logs do PostgreSQL para mais detalhes
    """)

if __name__ == "__main__":
    main()