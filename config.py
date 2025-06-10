import os
from dotenv import load_dotenv

load_dotenv()

# Detecta o tipo de banco uma vez
DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///sistema_fretes.db'
IS_POSTGRESQL = DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-super-secreta-aqui'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações condicionais baseadas no tipo de banco
    if IS_POSTGRESQL:
        # Configurações para PostgreSQL (Render)
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
        # Configurações para SQLite (Local)
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'connect_args': {
                'timeout': 20,
                'check_same_thread': False
            }
        }
    
    # Flask-Login
    REMEMBER_COOKIE_DURATION = 86400  # 24 horas
    SESSION_PROTECTION = 'strong'

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True


