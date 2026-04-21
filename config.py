import os

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - allow running without optional dependency

    def load_dotenv(*_args, **_kwargs):
        """Fallback when python-dotenv is not installed."""
        return None


load_dotenv()

# Detecta o tipo de banco uma vez
DATABASE_URL = os.environ.get("DATABASE_URL")
# Correção UTF-8 para PostgreSQL - versão RENDER-READY
if DATABASE_URL and DATABASE_URL.startswith(("postgresql://", "postgres://")):
    # Remove client_encoding existente primeiro
    if "client_encoding=" in DATABASE_URL:
        import re

        DATABASE_URL = re.sub(r"[?&]client_encoding=[^&]*", "", DATABASE_URL)

    # Render.com requer parâmetros específicos
    encoding_params = ["client_encoding=utf8", "connect_timeout=10", "application_name=sistema_fretes"]

    # Adiciona parâmetros de forma robusta
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL += separator + "&".join(encoding_params)

DATABASE_URL = DATABASE_URL or "sqlite:///sistema_fretes.db"
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

# Detecta se é ambiente de produção
IS_PRODUCTION = os.environ.get("ENVIRONMENT") == "production" or "render.com" in os.environ.get(
    "RENDER_EXTERNAL_URL", ""
)


class Config:
    # Configuração de encoding UTF-8 - mais robusta
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300, "echo": False}

    # Configurações específicas por tipo de banco
    if IS_POSTGRESQL:
        # Configurações otimizadas para Render.com
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {
            "client_encoding": "utf8",
            "options": "-c client_encoding=utf8 -c timezone=America/Sao_Paulo",
            "connect_timeout": 10,
            "command_timeout": 30,
            "application_name": "sistema_fretes",
        }
        # Pool settings para Render
        SQLALCHEMY_ENGINE_OPTIONS["pool_size"] = 5
        SQLALCHEMY_ENGINE_OPTIONS["max_overflow"] = 10
        SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] = 30
    else:
        SQLALCHEMY_ENGINE_OPTIONS["connect_args"] = {}
    # SECRET_KEY: obrigatório em produção, permite fallback apenas em desenvolvimento local
    _secret_key = os.environ.get("SECRET_KEY")
    if not _secret_key and IS_PRODUCTION:
        raise ValueError(
            "SECRET_KEY must be set in production environment! "
            "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    SECRET_KEY = _secret_key or "dev-key-local-only-insecure"  # Apenas para desenvolvimento local
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 🆕 CONFIGURAÇÕES DE MONITORAMENTO
    # Filtrar NFs FOB do monitoramento (True por padrão)
    FILTRAR_FOB_MONITORAMENTO = os.environ.get("FILTRAR_FOB_MONITORAMENTO", "True").lower() == "true"

    # Query Profiler — conta queries por request e detecta N+1
    # Ativar via ENABLE_QUERY_PROFILING=true no Render (reinicia servico)
    ENABLE_QUERY_PROFILING = os.environ.get("ENABLE_QUERY_PROFILING", "False").lower() == "true"

    # ✅ CONFIGURAÇÕES DE CSRF OTIMIZADAS
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200  # 2 horas (era 1 hora por padrão)

    if IS_PRODUCTION:
        # Configurações de CSRF para produção - menos rigorosas para evitar erros
        WTF_CSRF_SSL_STRICT = False  # Desabilita verificação rigorosa de referrer
        WTF_CSRF_CHECK_DEFAULT = True
        # Headers alternativos para CSRF em produção
        WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token", "HTTP_X_CSRFTOKEN", "HTTP_X_CSRF_TOKEN"]
    else:
        # Configurações de CSRF para desenvolvimento
        WTF_CSRF_SSL_STRICT = False  # Também desabilitado em dev
        WTF_CSRF_CHECK_DEFAULT = True

    # ✅ CONFIGURAÇÕES DE SESSÃO OTIMIZADAS
    # Sessão mais longa e estável
    PERMANENT_SESSION_LIFETIME = 28800  # 8 horas
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # Secure apenas em produção
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"  # Mais permissivo que 'Strict'

    # Configurações condicionais baseadas no tipo de banco
    if IS_POSTGRESQL:
        # Configurações para PostgreSQL (Render) - OTIMIZADAS PARA EVITAR EOF E SSL ERRORS
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,  # Testa conexão antes de usar
            "pool_recycle": 180,  # Recicla conexões a cada 3 minutos (reduzido para evitar SSL timeout)
            "pool_timeout": 10,  # Timeout mais curto para falhar rápido (era 30)
            "max_overflow": 15,  # Permite mais conexões temporárias (aumentado)
            "pool_size": 5,  # Menos conexões no pool mas com recycle mais frequente
            "echo_pool": False,  # Debug do pool (ativar se precisar)
            "connect_args": {
                "sslmode": "prefer",  # Mudado de 'require' para 'prefer' (mais flexível)
                "connect_timeout": 10,  # Timeout de conexão mais curto
                "application_name": "sistema_fretes",
                "keepalives": 1,  # Ativa keepalive
                "keepalives_idle": 30,  # Envia keepalive a cada 30s
                "keepalives_interval": 10,  # Intervalo entre keepalives
                "keepalives_count": 5,  # Tentativas antes de desistir
                "client_encoding": "utf8",  # Encoding UTF-8 explícito
                # Combina todas as opções em uma única string
                # idle_in_transaction_session_timeout=120s: operacoes Odoo podem levar 60-180s
                "options": "-c client_encoding=UTF8 -c timezone=America/Sao_Paulo -c statement_timeout=60000 -c idle_in_transaction_session_timeout=120000",
            },
        }
    else:
        # Configurações para SQLite (Local)
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "connect_args": {"timeout": 20, "check_same_thread": False}}

    # Flask-Login
    REMEMBER_COOKIE_DURATION = 86400  # 24 horas
    SESSION_PROTECTION = "strong"

    # ===========================
    # CONFIGURAÇÕES DE ARMAZENAMENTO DE ARQUIVOS
    # ===========================

    # AWS S3 (para produção)
    USE_S3 = os.environ.get("USE_S3", "False").lower() == "true"
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

    # Upload de arquivos
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB max upload
    UPLOAD_EXTENSIONS = ["jpg", "jpeg", "png", "pdf", "xlsx", "docx", "txt"]

    # ===========================
    # STATIC FILES & COMPRESSION
    # ===========================
    COMPRESS_MIMETYPES = [
        'text/html', 'text/css', 'text/xml', 'text/javascript',
        'application/json', 'application/javascript',
        'application/xml', 'application/xhtml+xml',
    ]
    COMPRESS_ALGORITHM = ['gzip']
    COMPRESS_MIN_SIZE = 512  # Comprime acima de 512 bytes

    # ==========================================
    # REDIS QUEUE - CONFIGURAÇÃO PARA WORKERS
    # ==========================================
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Configurações do RQ (Redis Queue)
    RQ_REDIS_URL = REDIS_URL
    RQ_DEFAULT_TIMEOUT = '30m'  # 30 minutos para jobs longos (Playwright)
    RQ_RESULT_TTL = 86400  # Mantém resultados por 24 horas
    RQ_FAILURE_TTL = 86400  # Mantém falhas por 24 horas
    RQ_QUEUES = ['high', 'default', 'low', 'atacadao']  # Fila dedicada para Atacadão
    
    # Dashboard do RQ (opcional)
    RQ_DASHBOARD_REDIS_URL = REDIS_URL
    RQ_DASHBOARD_WEB_BACKGROUND = True  # Executa em background

    # ==========================================
    # PLUGGY OPEN FINANCE — modulo pessoal (Bradesco via Meu Pluggy)
    # ==========================================
    PLUGGY_CLIENT_ID = os.environ.get('PLUGGY_CLIENT_ID')
    PLUGGY_CLIENT_SECRET = os.environ.get('PLUGGY_CLIENT_SECRET')
    PLUGGY_API_KEY = os.environ.get('PLUGGY_API_KEY')  # opcional; fallback do cache Redis
    PLUGGY_WEBHOOK_SECRET = os.environ.get('PLUGGY_WEBHOOK_SECRET')
    PLUGGY_INCLUDE_SANDBOX = os.environ.get('PLUGGY_INCLUDE_SANDBOX', 'false').lower() == 'true'
    PLUGGY_API_HOST = os.environ.get('PLUGGY_API_HOST', 'https://api.pluggy.ai')
    # URL publica do webhook — sobrescrever no Render se precisar dominio custom
    PLUGGY_WEBHOOK_URL = os.environ.get(
        'PLUGGY_WEBHOOK_URL',
        'https://sistema-fretes.onrender.com/pessoal/pluggy/webhook',
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True
    # Engine options seguros para SQLite em memória (sem pool sizing)
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": False, "connect_args": {"timeout": 20, "check_same_thread": False}}
