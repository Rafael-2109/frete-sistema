from flask import Blueprint

claude_ai_bp = Blueprint('claude_ai', __name__, url_prefix='/claude-ai')

# Import routes to register them with the blueprint
from . import routes 

# 🚀 SISTEMA AVANÇADO DE IA v2.0 - ROTAS AVANÇADAS ATIVADAS
# Versão: 25/06/2025 - Sistema Multi-Agent + Human Learning + PostgreSQL JSONB

# ✅ CORREÇÃO: Inicialização movida para função explícita
# Evita problemas de inicialização circular

def setup_claude_ai(app, redis_cache=None):
    """
    Configura o sistema Claude AI com a aplicação Flask
    
    Args:
        app: Aplicação Flask
        redis_cache: Instância do cache Redis (opcional)
        
    Returns:
        bool: True se inicializado com sucesso
    """
    success = True
    
    # 🧠 Inicializar Sistema de Sugestões Inteligentes
    try:
        from .suggestion_engine import init_suggestion_engine
        
        suggestion_engine = init_suggestion_engine(redis_cache)
        if suggestion_engine:
            app.logger.info("🧠 Sistema de Sugestões Inteligentes inicializado" + 
                          (" com Redis" if redis_cache else " (sem Redis)"))
        else:
            app.logger.warning("⚠️ Sistema de Sugestões sem Redis (fallback)")
            success = False
                
    except ImportError as e:
        app.logger.warning(f"⚠️ Sistema de Sugestões Inteligentes não disponível: {e}")
        success = False
    except Exception as e:
        app.logger.error(f"❌ Erro ao inicializar sugestões: {e}")
        success = False
    
    # 📊 Configurar analisador de dados
    try:
        from .data_analyzer import init_data_analyzers
        app.logger.info("📊 Analisador de Dados configurado")
    except ImportError as e:
        app.logger.warning(f"⚠️ Analisador de dados não disponível: {e}")
        success = False
        
    return success

# ❌ REMOVIDO: Inicialização automática que causava problemas
# init_intelligent_suggestions() 