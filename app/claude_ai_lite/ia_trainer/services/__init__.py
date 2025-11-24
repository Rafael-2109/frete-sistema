"""
Servicos do IA Trainer.

- CodebaseReader: Acesso ao codigo-fonte do sistema
- CodeValidator: Validacao de seguranca do codigo gerado
- CodeExecutor: Execucao controlada com timeout
- CodeGenerator: Geracao de codigo via Claude
- TrainerService: Orquestracao do fluxo de ensino
- codigo_loader: Carrega e cacheia codigos ativos para uso pelo sistema
- LoaderExecutor: Executa loaders estruturados (JOINs, filtros complexos)
- AutoLoaderService: Auto-geracao de loaders em tempo real
- DiscussionService: Modo Discussao Avancada com autonomia ampliada
"""

from .codebase_reader import CodebaseReader
from .code_validator import CodeValidator
from .code_executor import CodeExecutor
from .code_generator import CodeGenerator
from .trainer_service import TrainerService
from .loader_executor import LoaderExecutor, get_executor, executar_loader, validar_definicao
from .auto_loader import AutoLoaderService, get_auto_loader_service, tentar_responder_automaticamente
from .discussion_service import DiscussionService
from . import codigo_loader

__all__ = [
    'CodebaseReader',
    'CodeValidator',
    'CodeExecutor',
    'CodeGenerator',
    'TrainerService',
    'LoaderExecutor',
    'get_executor',
    'executar_loader',
    'validar_definicao',
    'AutoLoaderService',
    'get_auto_loader_service',
    'tentar_responder_automaticamente',
    'DiscussionService',
    'codigo_loader'
]
