"""
�� SEMANTIC MANAGER - Interface Unificada Atualizada
===================================================

Classe de compatibilidade que utiliza os módulos especializados.
Mantém interface original mas usa arquitetura modular.

NOVA ARQUITETURA:
- SemanticOrchestrator: Coordenação principal
- SemanticValidator: Validação e regras de negócio  
- SemanticEnricher: Enriquecimento com readers
- SemanticDiagnostics: Estatísticas e diagnósticos
"""

from typing import Dict, List, Any, Optional
import logging

# Imports dos módulos especializados
from .semantic_orchestrator import SemanticOrchestrator, get_semantic_orchestrator
from .semantic_validator import SemanticValidator, get_semantic_validator
from .semantic_enricher import SemanticEnricher, get_semantic_enricher
from .semantic_diagnostics import SemanticDiagnostics, get_semantic_diagnostics

logger = logging.getLogger(__name__)

class SemanticManager:
    """
    Interface unificada para o sistema semântico.
    
    ARQUITETURA MODULAR - Usa componentes especializados:
    - orchestrator: Coordenação e interface principal
    - validator: Validação de contexto e regras
    - enricher: Enriquecimento com readers
    - diagnostics: Estatísticas e diagnósticos
    """
    
    def __init__(self):
        """Inicializa o gerenciador semântico com arquitetura modular"""
        
        # Inicializar módulos especializados
        self.orchestrator = get_semantic_orchestrator()
        self.validator = get_semantic_validator(self.orchestrator)
        self.enricher = get_semantic_enricher(self.orchestrator)
        self.diagnostics = get_semantic_diagnostics(self.orchestrator)
        
        logger.info("🧠 SemanticManager inicializado com arquitetura modular")
    
    # ================================
    # INTERFACE DE COMPATIBILIDADE
    # Delega para módulos especializados
    # ================================
    
    # ORQUESTRAÇÃO PRINCIPAL
    @property
    def mappers(self):
        """Compatibilidade: acesso aos mappers"""
        return self.orchestrator.mappers
    
    @property
    def readme_reader(self):
        """Compatibilidade: acesso ao readme reader"""
        return self.orchestrator.readme_reader
    
    @property
    def database_reader(self):
        """Compatibilidade: acesso ao database reader"""
        return self.orchestrator.database_reader
    
    @property
    def readme_path(self):
        """Compatibilidade: acesso ao caminho do README"""
        return self.orchestrator.readme_path
    
    def mapear_termo_natural(self, termo: str, modelos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Delega para orchestrator"""
        return self.orchestrator.mapear_termo_natural(termo, modelos)
    
    def buscar_por_modelo(self, modelo: str) -> List[Dict[str, Any]]:
        """Delega para orchestrator"""
        return self.orchestrator.buscar_por_modelo(modelo)
    
    def buscar_no_readme(self, campo: str, modelo: Optional[str] = None) -> List[str]:
        """Delega para orchestrator"""
        return self.orchestrator.buscar_no_readme(campo, modelo)
    
    def listar_todos_modelos(self) -> List[str]:
        """Delega para orchestrator"""
        return self.orchestrator.listar_todos_modelos()
    
    def listar_todos_campos(self, modelo: Optional[str] = None) -> List[str]:
        """Delega para orchestrator"""
        return self.orchestrator.listar_todos_campos(modelo)
    
    # VALIDAÇÃO
    def validar_contexto_negocio(self, campo: str, modelo: str, valor: Optional[str] = None) -> Dict[str, Any]:
        """Delega para validator"""
        return self.validator.validar_contexto_negocio(campo, modelo, valor)
    
    def validar_consistencia_readme_banco(self) -> Dict[str, Any]:
        """Delega para validator"""
        return self.validator.validar_consistencia_readme_banco()
    
    # ENRIQUECIMENTO
    def enriquecer_mapeamento_com_readers(self, campo: str, modelo: Optional[str] = None) -> Dict[str, Any]:
        """Delega para enricher"""
        return self.enricher.enriquecer_mapeamento_com_readers(campo, modelo)
    
    # DIAGNÓSTICOS
    def gerar_estatisticas_completas(self) -> Dict[str, Any]:
        """Delega para diagnostics"""
        return self.diagnostics.gerar_estatisticas_completas()
    
    def diagnosticar_qualidade(self) -> Dict[str, Any]:
        """Delega para diagnostics"""
        return self.diagnostics.diagnosticar_qualidade()
    
    def gerar_relatorio_enriquecido(self) -> Dict[str, Any]:
        """Delega para diagnostics"""
        return self.diagnostics.gerar_relatorio_enriquecido()
    
    # ================================
    # NOVOS MÉTODOS AVANÇADOS
    # Aproveitam a arquitetura modular
    # ================================
    
    def validar_mapeamento_completo(self, termo_natural: str, campo: str, modelo: str) -> Dict[str, Any]:
        """Validação completa usando validator especializado"""
        return self.validator.validar_mapeamento_completo(termo_natural, campo, modelo)
    
    def enriquecer_batch_campos(self, campos: List[str], modelo: Optional[str] = None) -> Dict[str, Any]:
        """Enriquecimento em lote usando enricher especializado"""
        return self.enricher.enriquecer_batch_campos(campos, modelo)
    
    def gerar_relatorio_resumido(self) -> Dict[str, Any]:
        """Relatório resumido usando diagnostics especializado"""
        return self.diagnostics.gerar_relatorio_resumido()
    
    def verificar_saude_sistema(self) -> Dict[str, Any]:
        """Verificação de saúde usando orchestrator"""
        return self.orchestrator.verificar_saude_sistema()
    
    def obter_modulos_especializados(self) -> Dict[str, Any]:
        """
        Retorna referências aos módulos especializados.
        
        Returns:
            Dict com instâncias dos módulos
        """
        return {
            'orchestrator': self.orchestrator,
            'validator': self.validator,
            'enricher': self.enricher,
            'diagnostics': self.diagnostics
        }
    
    def executar_diagnostico_completo(self) -> Dict[str, Any]:
        """
        Executa diagnóstico completo usando todos os módulos.
        
        Returns:
            Dict com diagnóstico abrangente
        """
        return {
            'timestamp': self.orchestrator.verificar_saude_sistema(),
            'saude_sistema': self.orchestrator.verificar_saude_sistema(),
            'estatisticas': self.diagnostics.gerar_estatisticas_completas(),
            'qualidade': self.diagnostics.diagnosticar_qualidade(),
            'relatorio_enriquecido': self.diagnostics.gerar_relatorio_enriquecido(),
            'validacao_consistencia': self.validator.validar_consistencia_readme_banco(),
            'arquitetura': {
                'modular': True,
                'modulos_ativos': 4,
                'orquestrador': 'SemanticOrchestrator',
                'validador': 'SemanticValidator', 
                'enriquecedor': 'SemanticEnricher',
                'diagnosticos': 'SemanticDiagnostics'
            }
        }
    
    # ================================
    # MÉTODOS DE COMPATIBILIDADE
    # Mantém interface existente
    # ================================
    
    def __str__(self) -> str:
        """Representação string do manager"""
        return f"<SemanticManager[MODULAR] mappers={len(self.mappers)} campos={len(self.listar_todos_campos())} modulos=4>"
    
    def __repr__(self) -> str:
        """Representação detalhada do manager"""
        return self.__str__()


# ================================
# FUNÇÕES DE CONVENIÊNCIA GLOBAIS
# ================================

# Instância global para compatibilidade
_manager_instance = None

def get_semantic_manager() -> SemanticManager:
    """
    Obtém instância global do semantic manager.
    
    Returns:
        Instância do SemanticManager
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SemanticManager()
    return _manager_instance

# Aliases para compatibilidade com código existente
def get_manager() -> SemanticManager:
    """Alias para get_semantic_manager()"""
    return get_semantic_manager()

def create_semantic_manager() -> SemanticManager:
    """Alias para get_semantic_manager()"""
    return get_semantic_manager()

# ================================
# INICIALIZAÇÃO AUTOMÁTICA
# ================================

# Garantir que módulos estão disponíveis para import
__all__ = [
    'SemanticManager',
    'get_semantic_manager', 
    'get_manager',
    'create_semantic_manager',
    'SemanticOrchestrator',
    'SemanticValidator', 
    'SemanticEnricher',
    'SemanticDiagnostics'
]

logger.info("🎼 Sistema Semântico Modular carregado com sucesso")
logger.info("📊 Arquitetura: 4 módulos especializados (Orchestrator, Validator, Enricher, Diagnostics)")
logger.info("✅ Interface de compatibilidade mantida para código existente") 