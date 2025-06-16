#!/usr/bin/env python3
"""
🚨 ROLLBACK DE EMERGÊNCIA - CSRF
Script para reverter rapidamente as configurações CSRF em caso de problemas

Uso: python rollback_csrf_emergency.py
"""

import os
import shutil
from datetime import datetime

def backup_current_files():
    """Faz backup dos arquivos atuais antes do rollback"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backup_csrf_fix_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'config.py',
        'app/__init__.py',
        'app/templates/base.html',
        'app/utils/csrf_helper.py'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy2(file_path, os.path.join(backup_dir, os.path.basename(file_path)))
    
    print(f"✅ Backup criado em: {backup_dir}")
    return backup_dir

def rollback_config():
    """Reverte config.py para configurações mais rigorosas"""
    config_rollback = '''import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///sistema_fretes.db'
IS_POSTGRESQL = DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-super-secreta-aqui'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 🆕 CONFIGURAÇÕES DE MONITORAMENTO
    FILTRAR_FOB_MONITORAMENTO = os.environ.get('FILTRAR_FOB_MONITORAMENTO', 'True').lower() == 'true'
    
    # ⚠️ ROLLBACK: Configurações CSRF mais rigorosas
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora (padrão)
    WTF_CSRF_SSL_STRICT = True  # Mais rigoroso
    
    # ⚠️ ROLLBACK: Sessão mais curta
    PERMANENT_SESSION_LIFETIME = 14400  # 4 horas
    SESSION_COOKIE_SECURE = True  # Sempre secure
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'  # Mais rigoroso
    
    # Configurações condicionais baseadas no tipo de banco
    if IS_POSTGRESQL:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 200,
            'pool_timeout': 30,
            'max_overflow': 0,
            'pool_size': 5,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 15,
                'application_name': 'frete_sistema',
                'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=300000'
            }
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'connect_args': {
                'timeout': 20,
                'check_same_thread': False
            }
        }
    
    REMEMBER_COOKIE_DURATION = 86400
    SESSION_PROTECTION = 'strong'

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True
'''
    
    with open('config.py', 'w', encoding='utf-8') as f:
        f.write(config_rollback)
    
    print("✅ config.py revertido para configurações rigorosas")

def remove_csrf_helper():
    """Remove o arquivo csrf_helper.py se existir"""
    if os.path.exists('app/utils/csrf_helper.py'):
        os.remove('app/utils/csrf_helper.py')
        print("✅ csrf_helper.py removido")

def rollback_base_template():
    """Remove JavaScript adicional do base.html"""
    try:
        with open('app/templates/base.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove o JavaScript adicional que foi adicionado
        lines = content.split('\n')
        filtered_lines = []
        skip_block = False
        
        for line in lines:
            if '// ✅ NOVO: Tratamento aprimorado para erros CSRF' in line:
                skip_block = True
                continue
            elif skip_block and '</script>' in line:
                skip_block = False
                filtered_lines.append(line)
                continue
            elif not skip_block:
                filtered_lines.append(line)
        
        # Escreve o conteúdo filtrado
        with open('app/templates/base.html', 'w', encoding='utf-8') as f:
            f.write('\n'.join(filtered_lines))
        
        print("✅ JavaScript adicional removido do base.html")
        
    except Exception as e:
        print(f"⚠️ Erro ao reverter base.html: {e}")

def main():
    print("🚨 INICIANDO ROLLBACK DE EMERGÊNCIA - CSRF")
    print("=" * 50)
    
    # Confirm action
    confirm = input("⚠️ Tem certeza que quer reverter as configurações CSRF? (digite 'REVERTER'): ")
    if confirm != 'REVERTER':
        print("❌ Rollback cancelado")
        return
    
    try:
        # 1. Backup atual
        backup_dir = backup_current_files()
        
        # 2. Rollback config
        rollback_config()
        
        # 3. Remove csrf_helper
        remove_csrf_helper()
        
        # 4. Rollback template
        rollback_base_template()
        
        print("\n✅ ROLLBACK CONCLUÍDO!")
        print(f"📁 Backup dos arquivos alterados: {backup_dir}")
        print("\n🔄 PRÓXIMOS PASSOS:")
        print("1. Reinicie o servidor web")
        print("2. Monitore os logs de CSRF")
        print("3. Se tudo estiver funcionando, pode deletar o backup")
        
    except Exception as e:
        print(f"\n❌ ERRO NO ROLLBACK: {e}")
        print("🔧 Execute manualmente:")
        print("1. Restore o backup anterior via git")
        print("2. Ou reverta os arquivos manualmente")

if __name__ == '__main__':
    main() 