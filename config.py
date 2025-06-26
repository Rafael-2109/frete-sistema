import os
from dotenv import load_dotenv

load_dotenv()

# Detecta o tipo de banco uma vez
DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///sistema_fretes.db'
IS_POSTGRESQL = DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')

# Detecta se é ambiente de produção
IS_PRODUCTION = os.environ.get('ENVIRONMENT') == 'production' or 'render.com' in os.environ.get('RENDER_EXTERNAL_URL', '')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-super-secreta-aqui'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 🆕 CONFIGURAÇÕES DE MONITORAMENTO
    # Filtrar NFs FOB do monitoramento (True por padrão)
    FILTRAR_FOB_MONITORAMENTO = os.environ.get('FILTRAR_FOB_MONITORAMENTO', 'True').lower() == 'true'
    
    # ✅ CONFIGURAÇÕES DE CSRF OTIMIZADAS
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200  # 2 horas (era 1 hora por padrão)
    
    if IS_PRODUCTION:
        # Configurações de CSRF para produção - menos rigorosas para evitar erros
        WTF_CSRF_SSL_STRICT = False  # Desabilita verificação rigorosa de referrer
        WTF_CSRF_CHECK_DEFAULT = True
        # Headers alternativos para CSRF em produção
        WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token', 'HTTP_X_CSRFTOKEN', 'HTTP_X_CSRF_TOKEN']
    else:
        # Configurações de CSRF para desenvolvimento
        WTF_CSRF_SSL_STRICT = False  # Também desabilitado em dev
        WTF_CSRF_CHECK_DEFAULT = True
    
    # ✅ CONFIGURAÇÕES DE SESSÃO OTIMIZADAS
    # Sessão mais longa e estável
    PERMANENT_SESSION_LIFETIME = 28800  # 8 horas
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # Secure apenas em produção
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Mais permissivo que 'Strict'
    
    # Configurações condicionais baseadas no tipo de banco
    if IS_POSTGRESQL:
        # Configurações para PostgreSQL (Render) - OTIMIZADAS PARA EVITAR EOF
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,  # Testa conexão antes de usar
            'pool_recycle': 300,    # Recicla conexões a cada 5 minutos (era 200)
            'pool_timeout': 10,     # Timeout mais curto para falhar rápido (era 30)
            'max_overflow': 10,     # Permite mais conexões temporárias (era 0)
            'pool_size': 10,        # Mais conexões no pool (era 5)
            'echo_pool': False,     # Debug do pool (ativar se precisar)
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10,  # Timeout de conexão mais curto (era 15)
                'application_name': 'frete_sistema',
                'keepalives': 1,        # Ativa keepalive
                'keepalives_idle': 30,  # Envia keepalive a cada 30s
                'keepalives_interval': 10,  # Intervalo entre keepalives
                'keepalives_count': 5,  # Tentativas antes de desistir
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
    
    # ===========================
    # CONFIGURAÇÕES DE ARMAZENAMENTO DE ARQUIVOS
    # ===========================
    
    # AWS S3 (para produção)
    USE_S3 = os.environ.get('USE_S3', 'False').lower() == 'true'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    
    # Upload de arquivos
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB max upload
    UPLOAD_EXTENSIONS = ['jpg', 'jpeg', 'png', 'pdf', 'xlsx', 'docx', 'txt']

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True


