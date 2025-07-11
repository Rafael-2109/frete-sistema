#!/usr/bin/env python3
"""
Commands Module - Sistema modular otimizado de comandos especializados
Versão 2.0 com auto-discovery, base unificada e arquitetura escalável

Autor: Claude AI System
Data: 2025-01-09
"""

import logging
import importlib
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Configurar logging específico do módulo
logger = logging.getLogger(__name__)

# ====================================
# CONFIGURAÇÃO E CONSTANTES
# ====================================

COMMANDS_VERSION = "2.0.0"
COMMANDS_DESCRIPTION = "Sistema modular de comandos especializados com base unificada"

# Configuração de auto-discovery
AUTO_DISCOVERY_CONFIG = {
    'enabled': True,
    'scan_subdirectories': True,
    'cache_imports': True,
    'fallback_graceful': True
}

# Prioridades de carregamento
LOAD_PRIORITIES = {
    'base_command': 1,
    'excel_command_manager': 2,
    'cursor_commands': 3,
    'dev_commands': 4,
    'file_commands': 5,
    'excel': 6  # Pasta excel/ será carregada por último
}

# ====================================
# AUTO-DISCOVERY E IMPORTS INTELIGENTES
# ====================================

class CommandsRegistry:
    """Registry inteligente para comandos disponíveis"""
    
    def __init__(self):
        self.commands = {}
        self.status = {}
        self.load_errors = {}
        self._discovery_complete = False
    
    def discover_commands(self):
        """Descobre e registra comandos disponíveis"""
        if self._discovery_complete:
            return
        
        logger.info("🔍 Iniciando auto-discovery de comandos...")
        
        # Descobrir comandos principais
        self._discover_main_commands()
        
        # Descobrir mini esqueletos Excel
        self._discover_excel_commands()
        
        self._discovery_complete = True
        logger.info(f"✅ Auto-discovery completo: {len(self.commands)} comandos registrados")
    
    def _discover_main_commands(self):
        """Descobre comandos principais"""
        main_commands = [
            ('base_command', 'BaseCommand', 'Classe base para todos os comandos'),
            ('excel_command_manager', 'ExcelOrchestrator', 'Orquestrador de Excel'),
            ('cursor_commands', 'CursorCommands', 'Comandos do Cursor Mode'),
            ('dev_commands', 'DevCommands', 'Comandos de desenvolvimento'),
            ('file_commands', 'FileCommands', 'Comandos de arquivos')
        ]
        
        for module_name, class_name, description in main_commands:
            self._try_import_command(module_name, class_name, description)
    
    def _discover_excel_commands(self):
        """Descobre mini esqueletos Excel"""
        excel_commands = [
            ('excel.fretes', 'ExcelFretes', 'Gerador Excel de fretes'),
            ('excel.pedidos', 'ExcelPedidos', 'Gerador Excel de pedidos'),
            ('excel.entregas', 'ExcelEntregas', 'Gerador Excel de entregas'),
            ('excel.faturamento', 'ExcelFaturamento', 'Gerador Excel de faturamento')
        ]
        
        for module_name, class_name, description in excel_commands:
            self._try_import_command(module_name, class_name, description)
    
    def _try_import_command(self, module_name: str, class_name: str, description: str):
        """Tenta importar um comando específico"""
        try:
            # Tentar import do módulo
            full_module_name = f".{module_name}" if not module_name.startswith('.') else module_name
            module = importlib.import_module(full_module_name, package=__name__)
            
            # Verificar se a classe existe
            if hasattr(module, class_name):
                command_class = getattr(module, class_name)
                self.commands[module_name] = {
                    'class': command_class,
                    'module': module,
                    'description': description,
                    'status': 'available'
                }
                self.status[module_name] = True
                logger.info(f"✅ {module_name} ({class_name}) carregado com sucesso")
            else:
                self._register_error(module_name, f"Classe {class_name} não encontrada")
                
        except ImportError as e:
            self._register_error(module_name, f"Import error: {e}")
        except Exception as e:
            self._register_error(module_name, f"Erro inesperado: {e}")
    
    def _register_error(self, module_name: str, error: str):
        """Registra erro de carregamento"""
        self.status[module_name] = False
        self.load_errors[module_name] = error
        
        if AUTO_DISCOVERY_CONFIG['fallback_graceful']:
            logger.warning(f"⚠️ {module_name}: {error}")
        else:
            logger.error(f"❌ {module_name}: {error}")
    
    def get_command(self, command_name: str):
        """Retorna comando específico"""
        if command_name in self.commands:
            return self.commands[command_name]['class']
        return None
    
    def get_available_commands(self) -> List[str]:
        """Retorna lista de comandos disponíveis"""
        return [name for name, status in self.status.items() if status]
    
    def get_status_report(self) -> Dict[str, Any]:
        """Retorna relatório de status completo"""
        return {
            'total_commands': len(self.commands),
            'available_commands': len(self.get_available_commands()),
            'failed_commands': len([name for name, status in self.status.items() if not status]),
            'commands': self.commands,
            'status': self.status,
            'errors': self.load_errors,
            'version': COMMANDS_VERSION
        }

# ====================================
# INSTÂNCIA GLOBAL E INICIALIZAÇÃO
# ====================================

# Registry global
_commands_registry = CommandsRegistry()

# Executar auto-discovery na importação
if AUTO_DISCOVERY_CONFIG['enabled']:
    try:
        _commands_registry.discover_commands()
    except Exception as e:
        logger.error(f"Erro crítico no auto-discovery: {e}")

# ====================================
# IMPORTS CONDICIONAIS ORGANIZADOS
# ====================================

# Base (sempre tentado)
try:
    from app.claude_ai_novo.commands.base_command import (
        BaseCommand, format_response_advanced, create_excel_summary, 
        detect_command_type, logging, datetime, db, current_user
    )
    BASE_AVAILABLE = True
    logger.info("✅ Base commands carregados")
except ImportError as e:
    BASE_AVAILABLE = False
    logger.warning(f"⚠️ Base commands indisponíveis: {e}")

# Excel Orchestrator
try:
    from .excel_command_manager import ExcelOrchestrator, get_excel_orchestrator
    EXCEL_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    EXCEL_ORCHESTRATOR_AVAILABLE = False

# Cursor Commands
try:
    from .cursor_commands import CursorCommands, get_cursor_commands
    CURSOR_COMMANDS_AVAILABLE = True
except ImportError:
    CURSOR_COMMANDS_AVAILABLE = False

# Dev Commands
try:
    from .dev_commands import DevCommands, get_dev_commands
    DEV_COMMANDS_AVAILABLE = True
except ImportError:
    DEV_COMMANDS_AVAILABLE = False

# File Commands
try:
    from .file_commands import FileCommands, get_file_commands
    FILE_COMMANDS_AVAILABLE = True
except ImportError:
    FILE_COMMANDS_AVAILABLE = False

# Excel Mini Esqueletos
try:
    from .excel import (
        ExcelFretes, ExcelPedidos, ExcelEntregas, ExcelFaturamento,
        get_excel_fretes, get_excel_pedidos, get_excel_entregas, get_excel_faturamento
    )
    EXCEL_MINI_AVAILABLE = True
except ImportError:
    EXCEL_MINI_AVAILABLE = False

# ====================================
# FUNÇÕES DE CONVENIÊNCIA
# ====================================

def get_commands_status() -> Dict[str, bool]:
    """Retorna status de disponibilidade de todos os comandos"""
    return {
        'base_command': BASE_AVAILABLE,
        'excel_command_manager': EXCEL_ORCHESTRATOR_AVAILABLE,
        'cursor_commands': CURSOR_COMMANDS_AVAILABLE,
        'dev_commands': DEV_COMMANDS_AVAILABLE,
        'file_commands': FILE_COMMANDS_AVAILABLE,
        'excel_mini': EXCEL_MINI_AVAILABLE
    }

def get_available_commands() -> List[str]:
    """Retorna lista de comandos disponíveis"""
    _commands_registry.discover_commands()
    return _commands_registry.get_available_commands()

def get_command_registry() -> CommandsRegistry:
    """Retorna registry de comandos"""
    return _commands_registry

def initialize_all_commands():
    """Inicializa todas as instâncias de comandos disponíveis"""
    instances = {}
    
    if EXCEL_ORCHESTRATOR_AVAILABLE:
        try:
            instances['excel_orchestrator'] = get_excel_orchestrator()
        except Exception as e:
            logger.warning(f"Erro ao inicializar excel_orchestrator: {e}")
    
    if CURSOR_COMMANDS_AVAILABLE:
        try:
            instances['cursor_commands'] = get_cursor_commands()
        except Exception as e:
            logger.warning(f"Erro ao inicializar cursor_commands: {e}")
    
    if DEV_COMMANDS_AVAILABLE:
        try:
            instances['dev_commands'] = get_dev_commands()
        except Exception as e:
            logger.warning(f"Erro ao inicializar dev_commands: {e}")
    
    if FILE_COMMANDS_AVAILABLE:
        try:
            instances['file_commands'] = get_file_commands()
        except Exception as e:
            logger.warning(f"Erro ao inicializar file_commands: {e}")
    
    logger.info(f"✅ {len(instances)} instâncias de comandos inicializadas")
    return instances

def get_commands_info() -> Dict[str, Any]:
    """Retorna informações completas do módulo commands"""
    status = get_commands_status()
    available_count = sum(1 for available in status.values() if available)
    
    return {
        'version': COMMANDS_VERSION,
        'description': COMMANDS_DESCRIPTION,
        'total_modules': len(status),
        'available_modules': available_count,
        'availability_rate': (available_count / len(status)) * 100 if status else 0,
        'status': status,
        'registry': _commands_registry.get_status_report(),
        'auto_discovery': AUTO_DISCOVERY_CONFIG['enabled']
    }

def get_command_manager():
    """
    Retorna manager de comandos (AutoCommandProcessor).
    
    Este é o verdadeiro gerenciador de comandos do sistema, responsável por:
    - Processamento automático de comandos naturais
    - Detecção inteligente de comandos
    - Validação de segurança
    - Execução de comandos
    - Histórico e sugestões
    
    Returns:
        AutoCommandProcessor: Manager real de comandos
    """
    from .auto_command_processor import get_auto_command_processor
    return get_auto_command_processor()

def reset_commands_cache():
    """Limpa cache e força re-discovery"""
    global _commands_registry
    _commands_registry = CommandsRegistry()
    if AUTO_DISCOVERY_CONFIG['enabled']:
        _commands_registry.discover_commands()
    logger.info("🔄 Cache de comandos resetado")

# ====================================
# EXPORTS ORGANIZADOS
# ====================================

# Classes principais (se disponíveis)
__all__ = ['COMMANDS_VERSION', 'COMMANDS_DESCRIPTION']

# Base
if BASE_AVAILABLE:
    __all__.extend([
        'BaseCommand', 'format_response_advanced', 'create_excel_summary', 
        'detect_command_type'
    ])

# Commands principais
if EXCEL_ORCHESTRATOR_AVAILABLE:
    __all__.extend(['ExcelOrchestrator', 'get_excel_orchestrator'])

if CURSOR_COMMANDS_AVAILABLE:
    __all__.extend(['CursorCommands', 'get_cursor_commands'])

if DEV_COMMANDS_AVAILABLE:
    __all__.extend(['DevCommands', 'get_dev_commands'])

if FILE_COMMANDS_AVAILABLE:
    __all__.extend(['FileCommands', 'get_file_commands'])

# Excel mini esqueletos
if EXCEL_MINI_AVAILABLE:
    __all__.extend([
        'ExcelFretes', 'ExcelPedidos', 'ExcelEntregas', 'ExcelFaturamento',
        'get_excel_fretes', 'get_excel_pedidos', 'get_excel_entregas', 'get_excel_faturamento'
    ])

# Funções utilitárias
__all__.extend([
    'get_commands_status', 'get_available_commands', 'get_command_registry',
    'initialize_all_commands', 'get_commands_info', 'get_command_manager', 'reset_commands_cache'
])

# ====================================
# LOG DE INICIALIZAÇÃO
# ====================================

logger.info(f"""
🎯 Commands Module v{COMMANDS_VERSION} Inicializado
📊 Status: {sum(1 for status in get_commands_status().values() if status)}/{len(get_commands_status())} módulos disponíveis
🔧 Auto-discovery: {'✅ Ativo' if AUTO_DISCOVERY_CONFIG['enabled'] else '❌ Inativo'}
""")

# Relatório de status na inicialização
if logger.isEnabledFor(logging.INFO):
    status = get_commands_status()
    for module, available in status.items():
        status_icon = "✅" if available else "❌"
        logger.info(f"{status_icon} {module}")
