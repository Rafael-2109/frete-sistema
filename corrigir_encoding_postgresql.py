#!/usr/bin/env python3
"""
Script para corrigir problema de encoding UTF-8 no PostgreSQL
"""

import os
import sys
import logging
from urllib.parse import urlparse, urlunparse

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_url():
    """Corrige URL do banco de dados para UTF-8"""
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        logger.error("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        return False
    
    logger.info(f"🔍 URL atual: {database_url[:50]}...")
    
    # Parse da URL
    parsed = urlparse(database_url)
    
    # Verificar se já tem encoding
    if 'client_encoding=utf8' in parsed.query or 'client_encoding=utf-8' in parsed.query:
        logger.info("✅ Encoding UTF-8 já configurado")
        return True
    
    # Adicionar encoding UTF-8
    if parsed.query:
        new_query = parsed.query + '&client_encoding=utf-8'
    else:
        new_query = 'client_encoding=utf-8'
    
    # Reconstruir URL
    new_parsed = parsed._replace(query=new_query)
    new_url = urlunparse(new_parsed)
    
    logger.info(f"🔧 Nova URL: {new_url[:50]}...")
    
    return new_url

def fix_config_file():
    """Corrige arquivo de configuração"""
    
    config_file = 'config.py'
    
    if not os.path.exists(config_file):
        logger.error(f"❌ Arquivo {config_file} não encontrado")
        return False
    
    logger.info(f"🔍 Lendo {config_file}...")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se já tem correção
    if 'client_encoding=utf' in content:
        logger.info("✅ Correção de encoding já aplicada")
        return True
    
    # Adicionar correção
    fixes = [
        # Adicionar encoding na URL do banco
        ('DATABASE_URL = os.environ.get(\'DATABASE_URL\')', 
         'DATABASE_URL = os.environ.get(\'DATABASE_URL\')\n    # Correção UTF-8 para PostgreSQL\n    if DATABASE_URL and \'client_encoding=\' not in DATABASE_URL:\n        DATABASE_URL += \'&client_encoding=utf-8\' if \'?\' in DATABASE_URL else \'?client_encoding=utf-8\''),
        
        # Adicionar configuração de encoding
        ('class Config:', 
         'class Config:\n    # Configuração de encoding UTF-8\n    SQLALCHEMY_ENGINE_OPTIONS = {\n        "pool_pre_ping": True,\n        "pool_recycle": 300,\n        "connect_args": {"client_encoding": "utf8"}\n    }'),
    ]
    
    modified = False
    for old, new in fixes:
        if old in content and new not in content:
            content = content.replace(old, new)
            modified = True
            logger.info(f"✅ Aplicada correção: {old[:30]}...")
    
    if modified:
        # Fazer backup
        backup_file = f'{config_file}.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"💾 Backup salvo em: {backup_file}")
        
        # Salvar arquivo corrigido
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"✅ Arquivo {config_file} corrigido")
        
    return True

def set_environment_variables():
    """Define variáveis de ambiente para UTF-8"""
    
    env_vars = {
        'LANG': 'pt_BR.UTF-8',
        'LC_ALL': 'pt_BR.UTF-8',
        'PYTHONIOENCODING': 'utf-8',
        'PGCLIENTENCODING': 'UTF8'
    }
    
    logger.info("🔧 Configurando variáveis de ambiente...")
    
    for var, value in env_vars.items():
        os.environ[var] = value
        logger.info(f"✅ {var} = {value}")
    
    # Criar arquivo .env se não existir
    env_file = '.env'
    env_lines = []
    
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
    
    # Adicionar variáveis se não existirem
    for var, value in env_vars.items():
        var_line = f"{var}={value}\n"
        if not any(line.startswith(f"{var}=") for line in env_lines):
            env_lines.append(var_line)
            logger.info(f"✅ Adicionado ao .env: {var}")
    
    # Salvar .env
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(env_lines)
    
    return True

def create_test_script():
    """Cria script de teste para verificar encoding"""
    
    test_script = '''#!/usr/bin/env python3
"""
Script de teste para verificar encoding UTF-8
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def test_database_connection():
    """Testa conexão com banco de dados"""
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    try:
        # Parse da URL
        parsed = urlparse(database_url)
        
        # Configurar conexão com UTF-8 explícito
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove '/' do início
            user=parsed.username,
            password=parsed.password,
            options='-c client_encoding=utf8'
        )
        
        # Testar encoding
        cursor = conn.cursor()
        cursor.execute("SHOW client_encoding;")
        encoding = cursor.fetchone()[0]
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"✅ Encoding: {encoding}")
        
        # Testar caracteres especiais
        cursor.execute("SELECT 'Olá, teste com acentuação!' as teste;")
        result = cursor.fetchone()[0]
        print(f"✅ Teste de caracteres: {result}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def test_python_encoding():
    """Testa encoding do Python"""
    
    print(f"✅ Python encoding: {sys.getdefaultencoding()}")
    print(f"✅ Filesystem encoding: {sys.getfilesystemencoding()}")
    print(f"✅ Locale encoding: {locale.getpreferredencoding()}")
    
    # Testar caracteres especiais
    test_string = "Olá, mundo com acentuação! 🚀"
    print(f"✅ Teste string: {test_string}")
    
    return True

if __name__ == "__main__":
    import locale
    
    print("🚀 Testando encoding UTF-8...")
    print("="*50)
    
    test_python_encoding()
    print("="*50)
    test_database_connection()
    print("="*50)
    print("✅ Teste concluído!")
'''
    
    with open('teste_encoding.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    logger.info("✅ Script de teste criado: teste_encoding.py")
    return True

def main():
    """Função principal"""
    
    logger.info("🚀 Iniciando correção de encoding UTF-8...")
    
    try:
        # 1. Corrigir URL do banco
        logger.info("\n1. Corrigindo URL do banco de dados...")
        new_url = fix_database_url()
        
        # 2. Corrigir arquivo de config
        logger.info("\n2. Corrigindo arquivo de configuração...")
        fix_config_file()
        
        # 3. Configurar variáveis de ambiente
        logger.info("\n3. Configurando variáveis de ambiente...")
        set_environment_variables()
        
        # 4. Criar script de teste
        logger.info("\n4. Criando script de teste...")
        create_test_script()
        
        logger.info("\n✅ Todas as correções aplicadas com sucesso!")
        logger.info("🔥 Reinicie o sistema para aplicar as mudanças")
        logger.info("🧪 Execute 'python teste_encoding.py' para testar")
        
    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 