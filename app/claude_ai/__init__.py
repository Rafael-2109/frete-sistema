from flask import Blueprint

claude_ai_bp = Blueprint('claude_ai', __name__, url_prefix='/claude-ai')

# Import routes to register them with the blueprint
from . import routes 

# Import ClaudeRealIntegration
try:
    from .claude_real_integration import ClaudeRealIntegration
except ImportError:
    ClaudeRealIntegration = None

# 🚀 SISTEMA AVANÇADO DE IA v2.0 - ROTAS AVANÇADAS ATIVADAS
# Versão: 25/06/2025 - Sistema Multi-Agent + Human Learning + PostgreSQL JSONB

# 🤖 SISTEMA DE AUTONOMIA TOTAL v1.0 - ADICIONADO
# Sistema completo de autonomia com segurança absoluta

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
    
    # 🔒 NOVO: Inicializar Sistema de Segurança
    try:
        from .security_guard import init_security_guard
        
        security_guard = init_security_guard(app.instance_path)
        if security_guard:
            app.logger.info("🔒 Sistema de Segurança Claude AI inicializado")
        else:
            app.logger.warning("⚠️ Sistema de Segurança com problemas")
            success = False
                
    except ImportError as e:
        app.logger.warning(f"⚠️ Sistema de Segurança não disponível: {e}")
        success = False
    except Exception as e:
        app.logger.error(f"❌ Erro ao inicializar segurança: {e}")
        success = False
    
    # 🤖 NOVO: Inicializar Processador Automático de Comandos
    try:
        from .auto_command_processor import init_auto_processor
        
        auto_processor = init_auto_processor()
        if auto_processor:
            app.logger.info("🤖 Processador Automático de Comandos inicializado")
        else:
            app.logger.warning("⚠️ Processador Automático com problemas")
            success = False
                
    except ImportError as e:
        app.logger.warning(f"⚠️ Processador Automático não disponível: {e}")
        success = False
    except Exception as e:
        app.logger.error(f"❌ Erro ao inicializar processador automático: {e}")
        success = False
    
    # 🚀 NOVO: Inicializar Gerador de Código
    try:
        from .claude_code_generator import init_code_generator
        
        code_generator = init_code_generator(app.instance_path)
        if code_generator:
            app.logger.info("🚀 Gerador de Código Claude AI inicializado")
        else:
            app.logger.warning("⚠️ Gerador de Código com problemas")
            success = False
                
    except ImportError as e:
        app.logger.warning(f"⚠️ Gerador de Código não disponível: {e}")
        success = False
    except Exception as e:
        app.logger.error(f"❌ Erro ao inicializar gerador de código: {e}")
        success = False
    
    # 🧠 Inicializar Sistema de Sugestões Inteligentes
    try:
        from .suggestion_engine import init_suggestion_engine
        
        suggestion_engine = init_suggestion_engine(redis_cache)
        if suggestion_engine:
            app.logger.info("🧠 Sistema de Sugestões Inteligentes inicializado" + 
                          (" com Redis" if redis_cache else " (sem Redis)"))
        else:
            app.logger.warning("⚠️ Sistema de Sugestões sem Redis (fallback)")
                
    except ImportError as e:
        app.logger.warning(f"⚠️ Sistema de Sugestões Inteligentes não disponível: {e}")
    except Exception as e:
        app.logger.error(f"❌ Erro ao inicializar sugestões: {e}")
    
    # 📊 Configurar analisador de dados
    try:
        from .data_analyzer import init_data_analyzers
        app.logger.info("📊 Analisador de Dados configurado")
    except ImportError as e:
        app.logger.warning(f"⚠️ Analisador de dados não disponível: {e}")
        
    return success

# 🎯 FUNÇÕES DE ACESSO RÁPIDO PARA OS SISTEMAS DE AUTONOMIA
def get_security_guard():
    """Retorna instância do sistema de segurança"""
    try:
        from .security_guard import get_security_guard
        return get_security_guard()
    except ImportError:
        return None

def get_auto_processor():
    """Retorna instância do processador automático"""
    try:
        from .auto_command_processor import get_auto_processor
        return get_auto_processor()
    except ImportError:
        return None

def get_code_generator():
    """Retorna instância do gerador de código"""
    try:
        from .claude_code_generator import get_code_generator
        return get_code_generator()
    except ImportError:
        return None

# ❌ REMOVIDO: Inicialização automática que causava problemas
# init_intelligent_suggestions() 