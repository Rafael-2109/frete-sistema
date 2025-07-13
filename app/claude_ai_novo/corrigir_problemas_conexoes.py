#!/usr/bin/env python3
"""
Script para corrigir os problemas identificados nas conexões
"""

import os
import sys
import logging
from pathlib import Path

# Adicionar o caminho do projeto ao PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def corrigir_mapper_manager():
    """Corrige o erro _mappers no MapperManager"""
    logger.info("🔧 Corrigindo erro _mappers no MapperManager...")
    
    mapper_file = project_root / "app/claude_ai_novo/mappers/mapper_manager.py"
    
    with open(mapper_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se _mappers está sendo inicializado no __init__
    if "self._mappers = {}" not in content:
        logger.info("📝 Adicionando inicialização de _mappers...")
        
        # Encontrar o __init__
        init_pos = content.find("def __init__(self")
        if init_pos != -1:
            # Encontrar o final do __init__
            end_init = content.find("\n\n    def", init_pos)
            if end_init == -1:
                end_init = content.find("\n\n    #", init_pos)
            
            # Adicionar _mappers se não existir
            if "self._mappers" not in content[init_pos:end_init]:
                # Inserir após a linha do logger
                logger_line = content.find("logger.info", init_pos)
                if logger_line != -1:
                    next_line = content.find("\n", logger_line) + 1
                    content = content[:next_line] + "        self._mappers = {}\n" + content[next_line:]
                    
                    with open(mapper_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                    logger.info("✅ _mappers inicializado no MapperManager")
    
    return True

def corrigir_memory_manager_orchestrator():
    """Corrige o erro memory_manager não definido no orchestrator"""
    logger.info("🔧 Corrigindo erro memory_manager no MainOrchestrator...")
    
    orchestrator_file = project_root / "app/claude_ai_novo/orchestrators/main_orchestrator.py"
    
    with open(orchestrator_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar o método _connect_modules
    start = content.find("def _connect_modules(self):")
    if start == -1:
        logger.error("❌ Método _connect_modules não encontrado!")
        return False
        
    end = content.find("\n    def", start + 1)
    if end == -1:
        end = len(content)
        
    method_content = content[start:end]
    
    # Verificar se memory_manager está sendo obtido
    if "memory_manager = self.components.get('memory_manager')" not in method_content:
        logger.info("📝 Adicionando obtenção de memory_manager...")
        
        # Inserir após os outros gets
        insert_after = "processor_manager = self.components.get('processor_manager')"
        insert_pos = method_content.find(insert_after)
        
        if insert_pos != -1:
            insert_pos += len(insert_after)
            new_line = "\n            memory_manager = self.components.get('memory_manager')"
            
            # Atualizar o conteúdo
            full_insert_pos = start + insert_pos
            content = content[:full_insert_pos] + new_line + content[full_insert_pos:]
            
            with open(orchestrator_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("✅ memory_manager adicionado ao _connect_modules")
    
    return True

def adicionar_loader_provider_connection():
    """Adiciona a conexão Loader → Provider no orchestrator"""
    logger.info("🔧 Adicionando conexão Loader → Provider...")
    
    orchestrator_file = project_root / "app/claude_ai_novo/orchestrators/main_orchestrator.py"
    
    with open(orchestrator_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se já existe a conexão
    if "data_provider.set_loader(loader_manager)" in content:
        logger.info("✅ Conexão Loader → Provider já existe")
        return True
        
    # Encontrar onde adicionar
    insert_after = "logger.info(\"✅ Mapper → Loader conectados\")"
    insert_pos = content.find(insert_after)
    
    if insert_pos != -1:
        insert_pos += len(insert_after)
        
        new_connection = '''
            
            # Conectar Loader → Provider
            if data_provider and loader_manager:
                data_provider.set_loader(loader_manager)
                logger.info("✅ Loader → Provider conectados")'''
        
        content = content[:insert_pos] + new_connection + content[insert_pos:]
        
        with open(orchestrator_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info("✅ Conexão Loader → Provider adicionada")
    
    return True

def verificar_processor_manager():
    """Verifica se ProcessorManager tem método set_memory"""
    logger.info("🔍 Verificando ProcessorManager...")
    
    processor_file = project_root / "app/claude_ai_novo/processors/processor_manager.py"
    
    # Verificar se o arquivo existe
    if not processor_file.exists():
        # Tentar em utils/base_classes.py
        processor_file = project_root / "app/claude_ai_novo/utils/base_classes.py"
    
    if processor_file.exists():
        with open(processor_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "class ProcessorManager" in content:
            logger.info("✅ ProcessorManager encontrado")
            
            # Verificar se tem set_memory
            if "def set_memory(" not in content:
                logger.warning("⚠️ ProcessorManager não tem método set_memory")
                # Vamos adicionar
                return adicionar_set_memory_processor(processor_file, content)
    
    return True

def adicionar_set_memory_processor(processor_file, content):
    """Adiciona método set_memory ao ProcessorManager"""
    logger.info("📝 Adicionando set_memory ao ProcessorManager...")
    
    # Encontrar a classe ProcessorManager
    class_start = content.find("class ProcessorManager")
    if class_start == -1:
        return False
        
    # Encontrar o final da classe
    next_class = content.find("\nclass ", class_start + 1)
    if next_class == -1:
        next_class = len(content)
    
    # Inserir antes do final da classe
    insert_pos = content.rfind("\n\n", class_start, next_class)
    
    new_method = '''
    
    def set_memory(self, memory_manager):
        """Configura o MemoryManager para processamento integrado"""
        try:
            self.memory_manager = memory_manager
            
            # Propagar para processadores que precisam
            for name, processor in self.processors.items():
                if hasattr(processor, 'set_memory'):
                    processor.set_memory(memory_manager)
                    
            logger.info("✅ MemoryManager configurado no ProcessorManager")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar memory: {e}")'''
    
    content = content[:insert_pos] + new_method + content[insert_pos:]
    
    with open(processor_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    logger.info("✅ Método set_memory adicionado ao ProcessorManager")
    return True

def main():
    """Executa as correções"""
    logger.info("🚀 Iniciando correções dos problemas de conexão...")
    
    # 1. Corrigir MapperManager
    corrigir_mapper_manager()
    
    # 2. Corrigir memory_manager no orchestrator
    corrigir_memory_manager_orchestrator()
    
    # 3. Adicionar conexão Loader → Provider
    adicionar_loader_provider_connection()
    
    # 4. Verificar ProcessorManager
    verificar_processor_manager()
    
    logger.info("\n✅ Correções aplicadas! Execute testar_conexoes_orchestrator.py para validar.")

if __name__ == "__main__":
    main() 