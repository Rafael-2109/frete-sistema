#!/usr/bin/env python3
"""
Script para implementar as conexões restantes entre módulos
Foco nas 3 conexões que ainda não funcionam:
- Loader → Provider
- Memorizer → Processor  
- Learner → Analyzer
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

def implementar_conexao_loader_provider():
    """Implementa conexão Loader → Provider"""
    logger.info("🔧 Implementando conexão Loader → Provider...")
    
    # O DataProvider já tem set_loader(), mas precisamos garantir que
    # o MainOrchestrator está chamando corretamente
    orchestrator_file = project_root / "app/claude_ai_novo/orchestrators/main_orchestrator.py"
    
    # Verificar se a conexão está sendo feita
    with open(orchestrator_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Procurar onde o DataProvider é configurado
    if "data_provider.set_loader(loader_manager)" not in content:
        logger.warning("⚠️ Conexão Loader → Provider não encontrada no _connect_modules")
        
        # Vamos verificar o método _connect_modules
        import_pos = content.find("def _connect_modules(self):")
        if import_pos != -1:
            # Encontrar o final do método
            method_end = content.find("\n    def", import_pos + 1)
            if method_end == -1:
                method_end = len(content)
                
            method_content = content[import_pos:method_end]
            
            # Verificar se já tem a linha mas com sintaxe diferente
            if "self.data_provider" in method_content and "set_loader" in method_content:
                logger.info("✅ Conexão já existe mas com sintaxe diferente")
            else:
                logger.error("❌ Conexão Loader → Provider não implementada no _connect_modules")
                return False
    
    return True

def implementar_set_processor_no_memorizer():
    """Implementa método set_processor no MemoryManager"""
    logger.info("🔧 Implementando set_processor no MemoryManager...")
    
    memory_file = project_root / "app/claude_ai_novo/memorizers/memory_manager.py"
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se já tem o método
    if "def set_processor(" in content:
        logger.info("✅ Método set_processor já existe no MemoryManager")
        return True
        
    # Adicionar o método
    logger.info("📝 Adicionando método set_processor ao MemoryManager...")
    
    # Encontrar o final da classe
    class_end = content.rfind("\n\n# ")
    if class_end == -1:
        class_end = content.rfind("\n\ndef ")
    if class_end == -1:
        class_end = len(content)
    
    new_method = '''
    def set_processor(self, processor_manager):
        """Configura o ProcessorManager para processamento integrado"""
        try:
            self.processor_manager = processor_manager
            
            # Propagar para componentes que precisam
            if hasattr(self, 'context_memory') and self.context_memory:
                if hasattr(self.context_memory, 'set_processor'):
                    self.context_memory.set_processor(processor_manager)
                    
            if hasattr(self, 'conversation_memory') and self.conversation_memory:
                if hasattr(self.conversation_memory, 'set_processor'):
                    self.conversation_memory.set_processor(processor_manager)
                    
            logger.info("✅ ProcessorManager configurado no MemoryManager")
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar processor: {e}")
'''
    
    # Inserir antes do final da classe
    content = content[:class_end] + new_method + content[class_end:]
    
    with open(memory_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    logger.info("✅ Método set_processor adicionado ao MemoryManager")
    return True

def verificar_metodo_set_learner():
    """Verifica e corrige o método set_learner no AnalyzerManager"""
    logger.info("🔧 Verificando método set_learner no AnalyzerManager...")
    
    analyzer_file = project_root / "app/claude_ai_novo/analyzers/analyzer_manager.py"
    
    # Já foi corrigido no script anterior
    with open(analyzer_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "def set_learner(" in content and "self.components['intention']" in content:
        logger.info("✅ Método set_learner já corrigido no AnalyzerManager")
        return True
        
    return False

def verificar_conexoes_orchestrator():
    """Verifica se todas as conexões estão no _connect_modules"""
    logger.info("🔍 Verificando conexões no MainOrchestrator...")
    
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
    
    # Verificar cada conexão
    conexoes = {
        "Scanner → Loader": ["scanner", "loader", "configure_with_scanner"],
        "Loader → Provider": ["loader", "provider", "set_loader"],
        "Memorizer → Processor": ["memory", "processor", "set_processor"],
        "Learner → Analyzer": ["learner", "analyzer", "set_learner"]
    }
    
    status = {}
    for nome, keywords in conexoes.items():
        # Verificar se todos os keywords estão presentes
        found = all(kw in method_content for kw in keywords)
        status[nome] = found
        
        if found:
            logger.info(f"✅ {nome}: Conexão encontrada")
        else:
            logger.warning(f"❌ {nome}: Conexão não encontrada")
            
    return status

def corrigir_conexoes_orchestrator():
    """Corrige as conexões faltantes no orchestrator"""
    logger.info("🔧 Corrigindo conexões no MainOrchestrator...")
    
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
        end = content.find("\n\n    #", start + 1)
    if end == -1:
        end = len(content)
        
    method_content = content[start:end]
    
    # Verificar e adicionar conexões faltantes
    new_connections = []
    
    # Loader → Provider
    if "data_provider" in method_content and "set_loader" not in method_content:
        new_connections.append("""
            # Conectar Loader → Provider
            if data_provider and loader_manager:
                data_provider.set_loader(loader_manager)
                logger.info("✅ Conectado: Loader → Provider")""")
    
    # Memorizer → Processor
    if "memory_manager" in method_content and "set_processor" not in method_content:
        new_connections.append("""
            # Conectar Memorizer → Processor  
            if memory_manager and processor_manager:
                memory_manager.set_processor(processor_manager)
                logger.info("✅ Conectado: Memorizer → Processor")""")
    
    if new_connections:
        # Inserir antes do except ou no final do try
        try_end = method_content.rfind("\n        except")
        if try_end == -1:
            try_end = method_content.rfind("\n            logger.info")
            
        insertion_point = start + try_end
        
        for conn in new_connections:
            content = content[:insertion_point] + conn + content[insertion_point:]
            insertion_point += len(conn)
            
        with open(orchestrator_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"✅ Adicionadas {len(new_connections)} conexões ao orchestrator")
        
    return True

def main():
    """Executa a implementação das conexões restantes"""
    logger.info("🚀 Iniciando implementação das conexões restantes...")
    
    # 1. Verificar conexão Loader → Provider
    implementar_conexao_loader_provider()
    
    # 2. Implementar set_processor no MemoryManager
    implementar_set_processor_no_memorizer()
    
    # 3. Verificar set_learner no AnalyzerManager
    verificar_metodo_set_learner()
    
    # 4. Verificar todas as conexões no orchestrator
    status = verificar_conexoes_orchestrator()
    
    # 5. Corrigir conexões faltantes
    if status and not all(status.values()):
        corrigir_conexoes_orchestrator()
        
    logger.info("\n✅ Implementação concluída! Execute testar_conexoes_orchestrator.py para validar.")

if __name__ == "__main__":
    main() 