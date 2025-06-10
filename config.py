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
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0,
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
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


