from flask import Blueprint

claude_ai_bp = Blueprint('claude_ai', __name__, url_prefix='/claude-ai')

# Import routes to register them with the blueprint
from . import routes 

# 🧠 Inicializar Sistema de Sugestões Inteligentes
def init_intelligent_suggestions():
    """Inicializa sistema de sugestões inteligentes"""
    try:
        from .suggestion_engine import init_suggestion_engine
        
        # Tentar importar Redis cache
        try:
            from app.utils.redis_cache import redis_cache
            suggestion_engine = init_suggestion_engine(redis_cache)
            if suggestion_engine:
                print("🧠 Sistema de Sugestões Inteligentes inicializado com Redis")
            else:
                print("⚠️ Sistema de Sugestões sem Redis (fallback)")
        except ImportError:
            # Fallback sem Redis
            suggestion_engine = init_suggestion_engine(None)
            if suggestion_engine:
                print("🧠 Sistema de Sugestões Inteligentes inicializado (sem Redis)")
            else:
                print("❌ Erro ao inicializar Sistema de Sugestões")
        
        # 📊 Configurar analisador de dados (será inicializado quando necessário)
        try:
            from .data_analyzer import init_data_analyzers
            print("📊 Analisador de Dados configurado")
        except ImportError as e:
            print(f"⚠️ Analisador de dados não disponível: {e}")
                
    except ImportError:
        print("⚠️ Sistema de Sugestões Inteligentes não disponível")
    except Exception as e:
        print(f"❌ Erro ao inicializar sugestões: {e}")

# Inicializar sistema ao importar módulo
init_intelligent_suggestions() 