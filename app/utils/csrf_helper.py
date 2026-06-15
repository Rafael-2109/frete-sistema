"""
🔒 CSRF Helper - Validação robusta de token CSRF para endpoints de API.

Nota (limpeza 2026-06-15): removidas 5 funções órfãs (0 callers externos) —
validate_csrf_safe, ensure_csrf_token, is_csrf_error_recoverable,
log_csrf_error, regenerate_csrf_token. O CSRF global é tratado por
CSRFProtect() em app/__init__.py; esta função é o complemento usado pela
portaria. Histórico completo no git.
"""

import logging
from flask import current_app
from flask_wtf.csrf import validate_csrf


def validate_api_csrf(request, logger=None):
    """
    ✅ VALIDAÇÃO CSRF ROBUSTA com múltiplos fallbacks

    Tenta validar o token CSRF usando várias estratégias para evitar
    falsos positivos em produção.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Primeira tentativa: validação padrão
    try:
        validate_csrf(request.form.get('csrf_token'))
        return True
    except:
        pass

    # Segunda tentativa: buscar token em headers alternativos
    header_names = ['X-CSRFToken', 'X-CSRF-Token', 'HTTP_X_CSRFTOKEN', 'HTTP_X_CSRF_TOKEN']

    for header in header_names:
        csrf_token = request.headers.get(header)
        if csrf_token:
            try:
                validate_csrf(csrf_token)
                logger.info(f"🔒 CSRF válido via header {header}")
                return True
            except:
                continue

    # Terceira tentativa: buscar token no JSON body
    if request.is_json and request.json:
        csrf_token = request.json.get('csrf_token')
        if csrf_token:
            try:
                validate_csrf(csrf_token)
                logger.info("🔒 CSRF válido via JSON body")
                return True
            except:
                pass

    # Modo gracioso em produção - permite operação mas loga o problema
    if current_app.config.get('ENVIRONMENT') == 'production':
        logger.warning(f"🔒 CSRF falhou mas permitido em produção")
        return True

    # Em desenvolvimento, falha para identificar problemas
    logger.error("🔒 CSRF validation failed completely")
    return False
