"""
🔒 CSRF Helper - Utilitários para validação e recuperação de tokens CSRF
"""

from flask import session, request, current_app, g
from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms import ValidationError
import logging

logger = logging.getLogger(__name__)

def validate_csrf_safe(token=None):
    """
    Valida token CSRF de forma segura, com fallback para regeneração
    
    Args:
        token (str, optional): Token CSRF para validar. Se None, pega do request.
        
    Returns:
        tuple: (is_valid, new_token_if_regenerated)
    """
    try:
        if token is None:
            # Tenta pegar o token do formulário
            token = request.form.get('csrf_token')
            
            # Se não encontrou no form, tenta nos headers
            if not token:
                for header_name in current_app.config.get('WTF_CSRF_HEADERS', ['X-CSRFToken', 'X-CSRF-Token']):
                    token = request.headers.get(header_name)
                    if token:
                        break
        
        if not token:
            logger.warning("🔒 CSRF: Token não encontrado na requisição")
            return False, generate_csrf()
        
        # Tenta validar o token
        validate_csrf(token)
        return True, None
        
    except ValidationError as e:
        error_msg = str(e)
        logger.warning(f"🔒 CSRF: Validação falhou - {error_msg}")
        
        # Se o erro for de sessão faltando, tenta regenerar
        if "session token is missing" in error_msg.lower():
            logger.info("🔒 CSRF: Regenerando token devido à sessão perdida")
            return False, generate_csrf()
        
        # Se o token expirou, regenera
        elif "expired" in error_msg.lower():
            logger.info("🔒 CSRF: Regenerando token devido à expiração")
            return False, generate_csrf()
        
        # Para outros erros, também regenera
        else:
            logger.info(f"🔒 CSRF: Regenerando token devido ao erro: {error_msg}")
            return False, generate_csrf()
    
    except Exception as e:
        logger.error(f"🔒 CSRF: Erro inesperado na validação: {str(e)}")
        return False, generate_csrf()

def ensure_csrf_token():
    """
    Garante que existe um token CSRF válido na sessão
    
    Returns:
        str: Token CSRF válido
    """
    try:
        return generate_csrf()
    except Exception as e:
        logger.error(f"🔒 CSRF: Erro ao gerar token: {str(e)}")
        # Em caso de erro crítico, tenta limpar e regenerar a sessão
        try:
            if 'csrf_token' in session:
                del session['csrf_token']
            return generate_csrf()
        except:
            # Se tudo falhar, retorna string vazia (será tratado no frontend)
            return ""

def is_csrf_error_recoverable(error):
    """
    Verifica se um erro CSRF pode ser recuperado automaticamente
    
    Args:
        error: Exceção ou string de erro
        
    Returns:
        bool: True se o erro pode ser recuperado
    """
    error_str = str(error).lower()
    
    recoverable_errors = [
        "csrf session token is missing",
        "csrf token has expired",
        "csrf token is missing",
        "csrf tokens do not match"
    ]
    
    return any(err in error_str for err in recoverable_errors)

def log_csrf_error(error, additional_info=""):
    """
    Loga erro CSRF com informações úteis para debug
    
    Args:
        error: Erro CSRF
        additional_info (str): Informações adicionais
    """
    try:
        user_agent = request.headers.get('User-Agent', 'Unknown')[:100]
        ip_address = request.remote_addr
        path = request.path
        method = request.method
        
        logger.warning(
            f"🔒 CSRF ERROR: {str(error)} | "
            f"Path: {path} | Method: {method} | "
            f"IP: {ip_address} | UA: {user_agent} | "
            f"Additional: {additional_info}"
        )
        
        # Log informações da sessão (sem dados sensíveis)
        session_info = {
            'has_csrf_token': 'csrf_token' in session,
            'session_keys': list(session.keys()) if session else [],
            'session_permanent': getattr(session, 'permanent', False)
        }
        
        logger.debug(f"🔒 CSRF Session Info: {session_info}")
        
    except Exception as e:
        logger.error(f"🔒 Erro ao logar erro CSRF: {str(e)}")

def validate_api_csrf(request, logger=None, graceful_mode=True):
    """
    Validação CSRF específica para APIs JSON com modo gracioso
    
    Args:
        request: Objeto request do Flask
        logger: Logger para registro de eventos
        graceful_mode: Se True, permite continuar mesmo com erro CSRF em produção
        
    Returns:
        bool: True se validação passou ou modo gracioso permitiu continuar
    """
    from flask import current_app
    from flask_wtf.csrf import validate_csrf, CSRFError
    
    try:
        # Buscar token CSRF de múltiplas fontes
        csrf_token = None
        
        # 1. Headers
        csrf_token = (request.headers.get('X-CSRFToken') or 
                     request.headers.get('X-CSRF-Token') or
                     request.headers.get('HTTP_X_CSRF_TOKEN'))
        
        # 2. JSON body
        if not csrf_token and request.json:
            csrf_token = request.json.get('csrf_token')
        
        # 3. Form data (fallback)
        if not csrf_token:
            csrf_token = request.form.get('csrf_token')
        
        if not csrf_token:
            if logger:
                logger.warning("🔒 API CSRF: Token não encontrado em nenhuma fonte")
            
            if graceful_mode and not current_app.config.get('DEBUG', False):
                if logger:
                    logger.info("🔄 Modo gracioso: Continuando sem token CSRF em produção")
                return True
            return False
        
        # Tentar validar o token
        validate_csrf(csrf_token)
        
        if logger:
            logger.debug("✅ API CSRF: Token validado com sucesso")
        return True
        
    except CSRFError as e:
        if logger:
            logger.warning(f"🔒 API CSRF Error: {e}")
        
        # Modo gracioso para produção
        if graceful_mode and not current_app.config.get('DEBUG', False):
            if logger:
                logger.info("🔄 Modo gracioso: Ignorando erro CSRF em produção")
            return True
        
        return False
        
    except Exception as e:
        if logger:
            logger.error(f"🔒 API CSRF: Erro inesperado: {e}")
        
        # Em caso de erro inesperado, modo gracioso permite continuar
        if graceful_mode:
            return True
        
        return False 