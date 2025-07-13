#!/usr/bin/env python3
"""
Script para implementar os métodos faltantes nos componentes
para estabelecer as conexões entre módulos
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

def implementar_metodos_faltantes():
    """Implementa os métodos faltantes nos componentes"""
    
    # 1. Adicionar get_database_info ao ScanningManager
    logger.info("📝 Implementando get_database_info no ScanningManager...")
    
    scanner_file = project_root / "app/claude_ai_novo/scanning/scanning_manager.py"
    with open(scanner_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "def get_database_info" not in content:
        # Adicionar método antes do último método
        insert_pos = content.rfind("def __str__")
        if insert_pos == -1:
            insert_pos = content.rfind("class ScanningManager")
            # Encontrar o fim da classe
            lines = content[insert_pos:].split('\n')
            for i, line in enumerate(lines):
                if line and not line.startswith(' ') and i > 0:
                    insert_pos = insert_pos + sum(len(l) + 1 for l in lines[:i])
                    break
        
        new_method = '''
    def get_database_info(self) -> Dict[str, Any]:
        """Obtém informações completas do banco de dados"""
        try:
            if not self.database_manager:
                self.database_manager = DatabaseManager()
                
            # Escanear estrutura do banco
            db_info = self.database_manager.scan_database_structure()
            
            # Adicionar metadados úteis
            if db_info and 'tables' in db_info:
                for table_name, table_info in db_info['tables'].items():
                    # Adicionar informações de índices
                    if 'indexes' not in table_info:
                        table_info['indexes'] = []
                    
                    # Adicionar informações de relacionamentos
                    if 'relationships' not in table_info:
                        table_info['relationships'] = []
                        
            logger.info(f"✅ Informações do banco obtidas: {len(db_info.get('tables', {}))} tabelas")
            return db_info
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter informações do banco: {e}")
            return {}
    
'''
        
        content = content[:insert_pos] + new_method + content[insert_pos:]
        
        with open(scanner_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ get_database_info adicionado ao ScanningManager")
    
    # 2. Adicionar initialize_with_schema ao MapperManager
    logger.info("📝 Implementando initialize_with_schema no MapperManager...")
    
    mapper_file = project_root / "app/claude_ai_novo/mappers/mapper_manager.py"
    with open(mapper_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "def initialize_with_schema" not in content:
        # Adicionar após __init__
        init_end = content.find("logger.info(f'🧠 SemanticMapper (orquestrador) inicializado")
        if init_end != -1:
            # Encontrar o fim do método __init__
            lines_after = content[init_end:].split('\n')
            for i, line in enumerate(lines_after):
                if line and not line.startswith(' ') and i > 0:
                    insert_pos = init_end + sum(len(l) + 1 for l in lines_after[:i])
                    break
            else:
                insert_pos = init_end + len(lines_after[0]) + 1
        
        new_method = '''
    def initialize_with_schema(self, db_info: Dict[str, Any]):
        """Inicializa mappers com informações do schema do banco"""
        try:
            if not db_info or 'tables' not in db_info:
                logger.warning("⚠️ Schema vazio ou inválido")
                return
                
            # Atualizar informações de schema em todos os mappers
            self.db_schema = db_info
            
            # Propagar para mappers específicos
            for domain, mapper in self._mappers.items():
                if hasattr(mapper, 'set_schema_info'):
                    mapper.set_schema_info(db_info)
                    
            # Otimizar mapeamentos com base nos índices
            if 'tables' in db_info:
                self._optimize_mappings_with_indexes(db_info['tables'])
                
            logger.info(f"✅ Schema inicializado com {len(db_info.get('tables', {}))} tabelas")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar schema: {e}")
    
    def _optimize_mappings_with_indexes(self, tables_info: Dict[str, Any]):
        """Otimiza mapeamentos usando informações de índices"""
        # Identificar campos indexados para queries mais eficientes
        self.indexed_fields = {}
        
        for table_name, table_info in tables_info.items():
            if 'indexes' in table_info:
                self.indexed_fields[table_name] = [
                    idx.get('column') for idx in table_info['indexes']
                    if idx.get('column')
                ]
        
        logger.debug(f"📊 Campos indexados identificados: {len(self.indexed_fields)} tabelas")
    
'''
        
        content = content[:insert_pos] + new_method + content[insert_pos:]
        
        with open(mapper_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ initialize_with_schema adicionado ao MapperManager")
    
    # 3. Adicionar set_memory_manager ao ProcessorManager
    logger.info("📝 Implementando set_memory_manager no ProcessorManager...")
    
    processor_file = project_root / "app/claude_ai_novo/utils/base_classes.py"
    
    # Verificar se ProcessorManager existe no arquivo
    with open(processor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "class ProcessorManager" in content and "def set_memory_manager" not in content:
        # Encontrar a classe ProcessorManager
        class_pos = content.find("class ProcessorManager")
        if class_pos != -1:
            # Encontrar o __init__ da classe
            init_pos = content.find("def __init__", class_pos)
            if init_pos != -1:
                # Encontrar o fim do __init__
                lines_after = content[init_pos:].split('\n')
                indent = ""
                for i, line in enumerate(lines_after):
                    if i == 0:
                        # Pegar indentação
                        indent = line[:line.find("def")]
                    elif line and not line.startswith(indent + " ") and not line.startswith(indent + "def"):
                        insert_pos = init_pos + sum(len(l) + 1 for l in lines_after[:i])
                        break
                
                new_method = f'''
{indent}def set_memory_manager(self, memory_manager):
{indent}    """Configura o gerenciador de memória para os processadores"""
{indent}    self.memory_manager = memory_manager
{indent}    
{indent}    # Propagar para processadores que precisam de memória
{indent}    for processor in self.registry.processors.values():
{indent}        if hasattr(processor, 'set_memory'):
{indent}            processor.set_memory(memory_manager)
{indent}            
{indent}    logger.info("✅ MemoryManager configurado no ProcessorManager")
    
'''
                
                content = content[:insert_pos] + new_method + content[insert_pos:]
                
                with open(processor_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ set_memory_manager adicionado ao ProcessorManager")
    
    # 4. Adicionar set_learner ao AnalyzerManager
    logger.info("📝 Implementando set_learner no AnalyzerManager...")
    
    analyzer_file = project_root / "app/claude_ai_novo/analyzers/analyzer_manager.py"
    with open(analyzer_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "def set_learner" not in content:
        # Adicionar após __init__
        init_end = content.find("logger.info(f'AnalyzerManager inicializado")
        if init_end != -1:
            # Encontrar o fim do método __init__
            lines_after = content[init_end:].split('\n')
            for i, line in enumerate(lines_after):
                if line and not line.startswith(' ') and i > 0:
                    insert_pos = init_end + sum(len(l) + 1 for l in lines_after[:i])
                    break
        
        new_method = '''
    def set_learner(self, learner):
        """Configura o sistema de aprendizado para os analisadores"""
        self.learner = learner
        
        # Propagar para analisadores que usam aprendizado
        if self.intention_analyzer and hasattr(self.intention_analyzer, 'set_learner'):
            self.intention_analyzer.set_learner(learner)
            
        if self.semantic_analyzer and hasattr(self.semantic_analyzer, 'set_learner'):
            self.semantic_analyzer.set_learner(learner)
            
        logger.info("✅ Learner configurado no AnalyzerManager")
    
'''
        
        content = content[:insert_pos] + new_method + content[insert_pos:]
        
        with open(analyzer_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("✅ set_learner adicionado ao AnalyzerManager")
    
    logger.info("\n✅ Todos os métodos implementados com sucesso!")
    logger.info("\n🔄 Agora execute novamente o teste de conexões para verificar")

if __name__ == "__main__":
    implementar_metodos_faltantes() 