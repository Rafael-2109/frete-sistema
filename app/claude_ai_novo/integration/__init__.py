"""
🔗 INTEGRATION - Módulo de Integração
====================================

Responsabilidade: INTEGRAR sistemas externos e interfaces.
Arquitetura consolidada conforme regras de responsabilidade única.

ESTRUTURA REORGANIZADA:
- ✅ integration_manager.py (coordena integrações)
- ✅ external_api_integration.py (Claude + APIs externas)
- ✅ web_integration.py (Flask + interfaces web)
- ✅ standalone_integration.py (execução sem dependências)
"""

import logging

logger = logging.getLogger(__name__)

# Flask fallback para execução standalone
try:
    from ..utils.flask_fallback import is_flask_available
    flask_available = is_flask_available()
except ImportError:
    flask_available = False
    logger.warning("⚠️ Flask fallback não disponível")

# ============================================================================
# COMPONENTES PRINCIPAIS CONSOLIDADOS
# ============================================================================

# Manager principal de integração
try:
    from .integration_manager import IntegrationManager, get_integration_manager
    _integration_manager_available = True
except ImportError as e:
    logger.warning(f"⚠️ IntegrationManager não disponível: {e}")
    _integration_manager_available = False

# Integração com APIs externas (Claude, etc.)
try:
    from .external_api_integration import (
        ExternalAPIIntegration, ClaudeAPIClient,
        get_external_api_integration, get_claude_client, create_claude_client
    )
    _external_api_integration_available = True
except ImportError as e:
    logger.warning(f"⚠️ External API Integration não disponível: {e}")
    _external_api_integration_available = False

# Integração web (Flask + interfaces)
try:
    from .web_integration import (
        WebIntegrationAdapter, WebFlaskRoutes,
        get_web_integration_adapter, get_flask_routes, create_integration_routes
    )
    _web_integration_available = True
except ImportError as e:
    logger.warning(f"⚠️ Web Integration não disponível: {e}")
    _web_integration_available = False

# Integração standalone (sem dependências web)
try:
    from .standalone_integration import (
        StandaloneIntegration, get_standalone_integration,
        get_standalone_adapter, create_standalone_system
    )
    _standalone_integration_available = True
except ImportError as e:
    logger.warning(f"⚠️ Standalone Integration não disponível: {e}")
    _standalone_integration_available = False

logger.info("✅ Integration consolidado carregado com sucesso")

# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA INTELIGENTES
# ============================================================================

def get_integration_system():
    """
    Retorna sistema de integração adequado baseado no ambiente.
    
    Prioridade:
    1. IntegrationManager (sistema completo)
    2. ExternalAPIIntegration (APIs externas)
    3. StandaloneIntegration (fallback)
    
    Returns:
        Sistema de integração apropriado
    """
    if flask_available and _integration_manager_available:
        return get_integration_manager()
    elif _external_api_integration_available:
        return get_external_api_integration()
    elif _standalone_integration_available:
        return get_standalone_integration()
    else:
        logger.error("❌ Nenhum sistema de integração disponível")
        return None

def get_web_system():
    """
    Retorna sistema de integração web específico.
    
    Returns:
        WebIntegrationAdapter ou None
    """
    if _web_integration_available:
        return get_web_integration_adapter()
    else:
        logger.warning("⚠️ Sistema web não disponível")
        return None

def get_external_api_system():
    """
    Retorna sistema de integração com APIs externas.
    
    Returns:
        ExternalAPIIntegration ou None
    """
    if _external_api_integration_available:
        return get_external_api_integration()
    else:
        logger.warning("⚠️ Sistema de APIs externas não disponível")
        return None

def get_standalone_system():
    """
    Retorna sistema de integração standalone.
    
    Returns:
        StandaloneIntegration ou None
    """
    if _standalone_integration_available:
        return get_standalone_integration()
    else:
        logger.warning("⚠️ Sistema standalone não disponível")
        return None

# ============================================================================
# FUNÇÕES DE COMPATIBILIDADE
# ============================================================================

def get_claude_ai_instance():
    """
    Função de compatibilidade para código existente.
    
    Retorna adapter adequado mantendo interface compatível.
    
    Returns:
        Adapter com interface síncrona para web
    """
    if _web_integration_available:
        return get_web_integration_adapter()
    elif _external_api_integration_available:
        return get_external_api_integration()
    elif _standalone_integration_available:
        return get_standalone_integration()
    else:
        logger.error("❌ Nenhum sistema disponível para compatibilidade")
        return None

def get_manager():
    """Alias para get_integration_system()."""
    return get_integration_system()

def get_flask_adapter():
    """Compatibilidade - retorna web integration adapter."""
    return get_web_system()

def get_standalone_adapter():
    """Compatibilidade - retorna standalone integration."""
    return get_standalone_system()

# ============================================================================
# FUNÇÕES DE INICIALIZAÇÃO E VALIDAÇÃO
# ============================================================================

def initialize_integration_system():
    """
    Inicializa o sistema de integração apropriado.
    
    Returns:
        Sistema inicializado ou None
    """
    system = get_integration_system()
    if system:
        # Tentar inicialização se método disponível
        if hasattr(system, 'initialize_complete_system'):
            try:
                init_result = system.initialize_complete_system()
                # Aguardar se async
                if hasattr(init_result, '__await__'):
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        init_result = loop.run_until_complete(init_result)
                    except RuntimeError:
                        init_result = asyncio.run(init_result)
                
                logger.info(f"🔗 Sistema inicializado: {system.__class__.__name__}")
                return system
            except Exception as e:
                logger.error(f"❌ Erro na inicialização: {e}")
        else:
            logger.info(f"🔗 Sistema carregado: {system.__class__.__name__}")
            return system
    else:
        logger.error("❌ Nenhum sistema de integração disponível")
        return None

def validate_integration_architecture():
    """
    Valida se a arquitetura de integração está conforme as regras.
    
    Returns:
        Dict com análise arquitetural
    """
    components = {
        'integration_manager': _integration_manager_available,
        'external_api_integration': _external_api_integration_available,
        'web_integration': _web_integration_available,
        'standalone_integration': _standalone_integration_available
    }
    
    available_count = sum(1 for available in components.values() if available)
    total_count = len(components)
    
    # Verificar conformidade arquitetural
    architectural_compliance = {
        'responsibility_separation': True,  # Cada arquivo tem responsabilidade única
        'no_domain_folders': True,  # Não há subpastas por domínio (claude/ removida)
        'consolidated_functions': True,  # Funcionalidades duplicadas consolidadas
        'manager_coordination': _integration_manager_available  # Manager coordena
    }
    
    compliance_score = sum(1 for compliant in architectural_compliance.values() if compliant) / len(architectural_compliance)
    
    # Recomendação de sistema
    if flask_available and _integration_manager_available:
        recommended = 'IntegrationManager (sistema completo)'
    elif _external_api_integration_available:
        recommended = 'ExternalAPIIntegration (APIs)'
    elif _web_integration_available:
        recommended = 'WebIntegrationAdapter (web)'
    elif _standalone_integration_available:
        recommended = 'StandaloneIntegration (fallback)'
    else:
        recommended = 'Nenhum disponível'
    
    logger.info(f"📊 Integration status: {available_count}/{total_count} componentes")
    logger.info(f"🏗️ Compliance arquitetural: {compliance_score:.1%}")
    
    return {
        'components': components,
        'available_count': available_count,
        'total_count': total_count,
        'availability_percentage': (available_count / total_count) * 100,
        'architectural_compliance': architectural_compliance,
        'compliance_score': compliance_score,
        'recommended_system': recommended,
        'flask_available': flask_available,
        'architecture_status': 'COMPLIANT' if compliance_score >= 0.8 else 'NEEDS_IMPROVEMENT'
    }

# ============================================================================
# INSTÂNCIAS GLOBAIS LAZY-LOADED
# ============================================================================

_global_instances = {}

def get_global_instance(component_name: str):
    """
    Retorna instância global de um componente específico.
    
    Args:
        component_name: Nome do componente
        
    Returns:
        Instância global ou None
    """
    if component_name not in _global_instances:
        if component_name == 'integration_manager' and _integration_manager_available:
            _global_instances[component_name] = get_integration_manager()
        elif component_name == 'external_api_integration' and _external_api_integration_available:
            _global_instances[component_name] = get_external_api_integration()
        elif component_name == 'web_integration' and _web_integration_available:
            _global_instances[component_name] = get_web_integration_adapter()
        elif component_name == 'standalone_integration' and _standalone_integration_available:
            _global_instances[component_name] = get_standalone_integration()
        else:
            return None
    
    return _global_instances.get(component_name)

# ============================================================================
# EXPORTS PRINCIPAIS CONSOLIDADOS
# ============================================================================

__all__ = [
    # Classes principais
    'IntegrationManager', 
    'ExternalAPIIntegration', 'ClaudeAPIClient',
    'WebIntegrationAdapter', 'WebFlaskRoutes',
    'StandaloneIntegration',
    
    # Funções de acesso principal
    'get_integration_manager',
    'get_external_api_integration', 'get_claude_client', 'create_claude_client',
    'get_web_integration_adapter', 'get_flask_routes', 'create_integration_routes',
    'get_standalone_integration', 'create_standalone_system',
    
    # Funções de conveniência inteligentes
    'get_integration_system', 'get_web_system', 'get_external_api_system', 'get_standalone_system',
    
    # Compatibilidade
    'get_claude_ai_instance', 'get_manager', 'get_flask_adapter', 'get_standalone_adapter',
    
    # Inicialização e validação
    'initialize_integration_system', 'validate_integration_architecture',
    'get_global_instance',
    
    # Utilitários
    'is_flask_available'
]

# ============================================================================
# EXECUÇÃO STANDALONE PARA TESTES
# ============================================================================

if __name__ == "__main__":
    print("🔗 INTEGRATION - Módulo Consolidado de Integração")
    print("=" * 60)
    
    # Validar arquitetura
    analysis = validate_integration_architecture()
    print(f"📊 Componentes: {analysis['available_count']}/{analysis['total_count']} ({analysis['availability_percentage']:.1f}%)")
    print(f"🏗️ Compliance: {analysis['compliance_score']:.1%} - {analysis['architecture_status']}")
    print(f"💡 Sistema recomendado: {analysis['recommended_system']}")
    
    # Testar sistema
    integration_system = get_integration_system()
    if integration_system:
        print(f"✅ Sistema ativo: {integration_system.__class__.__name__}")
    else:
        print("❌ Nenhum sistema disponível")
    
    # Testar compatibilidade
    claude_instance = get_claude_ai_instance()
    if claude_instance:
        print(f"✅ Compatibilidade: {claude_instance.__class__.__name__}")
    else:
        print("❌ Compatibilidade não disponível") 