import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-super-secreta-aqui'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///sistema_fretes.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações para melhorar estabilidade PostgreSQL no Render
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 200,  # Recicla conexões mais frequentemente
        'pool_timeout': 30,   # Timeout maior para operações pesadas
        'max_overflow': 0,
        'pool_size': 5,       # Pool menor mas mais estável
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 15,
            'application_name': 'frete_sistema',
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=300000'
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


