"""
🔧 FIX TYPE ERRORS - Correção de Erros de Tipo
==============================================

Script para corrigir todos os erros de tipo identificados pelo Pylance:
1. coordinators/__init__.py linha 73: agent_type faltando
2. orchestrators/orchestrator_manager.py: conflitos SessionPriority
3. orchestrators/session_orchestrator.py: conflitos type annotations
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TypeErrorFixer:
    """
    Corretor de erros de tipo no sistema.
    """
    
    def __init__(self):
        self.base_path = Path(".")
        self.fixes_applied = []
        
    def fix_coordinator_init_agent_type(self) -> bool:
        """
        Corrige o erro de agent_type faltando no coordinators/__init__.py
        """
        file_path = self.base_path / "coordinators" / "__init__.py"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Procurar pela linha problemática
            old_pattern = r'agent = SpecialistAgent\(\)'
            new_replacement = 'agent = SpecialistAgent(AgentType.FRETES)  # Usando FRETES como padrão'
            
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_replacement, content)
                
                # Também garantir que o import está presente
                if 'from app.claude_ai_novo.utils.agent_types import AgentType' not in content:
                    # Adicionar import após a linha do SpecialistAgent
                    specialist_import = 'from .specialist_agents import SpecialistAgent'
                    agent_type_import = 'from app.claude_ai_novo.utils.agent_types import AgentType'
                    
                    content = content.replace(
                        specialist_import,
                        f'{specialist_import}\n        {agent_type_import}'
                    )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append("coordinators/__init__.py - agent_type parameter added")
                logger.info("✅ Corrigido: coordinators/__init__.py - agent_type parameter")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao corrigir coordinators/__init__.py: {e}")
            return False
        
        return False
    
    def fix_orchestrator_manager_session_priority(self) -> bool:
        """
        Corrige conflitos SessionPriority no orchestrator_manager.py
        """
        file_path = self.base_path / "orchestrators" / "orchestrator_manager.py"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simplificar a lógica de SessionPriority para evitar conflitos de tipo
            old_pattern = r'# Importar enum necessário do session_orchestrator.*?priority = "normal"'
            
            new_replacement = '''# Usar valores diretos para evitar conflitos de tipo
            priority_value = params.get('priority', 'normal')
            
            # Tentar import e uso direto
            try:
                from app.claude_ai_novo.orchestrators.session_orchestrator import SessionPriority
                if priority_value.upper() == 'HIGH':
                    session_priority = SessionPriority.HIGH
                elif priority_value.upper() == 'LOW':
                    session_priority = SessionPriority.LOW
                elif priority_value.upper() == 'CRITICAL':
                    session_priority = SessionPriority.CRITICAL
                else:
                    session_priority = SessionPriority.NORMAL
            except ImportError:
                # Fallback para string simples
                session_priority = priority_value'''
            
            if re.search(old_pattern, content, re.DOTALL):
                content = re.sub(old_pattern, new_replacement, content, flags=re.DOTALL)
                
                # Também corrigir o uso da variável priority para session_priority
                content = content.replace(
                    'priority=priority,',
                    'priority=session_priority,'
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append("orchestrators/orchestrator_manager.py - SessionPriority conflicts")
                logger.info("✅ Corrigido: orchestrators/orchestrator_manager.py - SessionPriority")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao corrigir orchestrator_manager.py: {e}")
            return False
        
        return False
    
    def fix_session_orchestrator_type_annotations(self) -> bool:
        """
        Corrige conflitos de type annotations no session_orchestrator.py
        """
        file_path = self.base_path / "orchestrators" / "session_orchestrator.py"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remover type annotations problemáticas
            corrections = [
                # Linha 19: MockSessionMemory annotation
                (r'get_session_memory: Callable\[\[\], MockSessionMemory\] = get_session_memory', 
                 'get_session_memory = get_session_memory'),
                
                # Linha 20: MockPerformanceAnalyzer annotation
                (r'get_performance_analyzer: Callable\[\[\], type\[MockPerformanceAnalyzer\]\] = get_performance_analyzer',
                 'get_performance_analyzer = get_performance_analyzer'),
                
                # Linha 25: MockSessionMemory annotation (duplicata)
                (r'get_session_memory: Callable\[\[\], MockSessionMemory\] = get_session_memory',
                 'get_session_memory = get_session_memory'),
                
                # Linha 26: MockPerformanceAnalyzer annotation (duplicata)
                (r'get_performance_analyzer: Callable\[\[\], type\[MockPerformanceAnalyzer\]\] = get_performance_analyzer',
                 'get_performance_analyzer = get_performance_analyzer'),
            ]
            
            changes_made = False
            for old_pattern, new_replacement in corrections:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_replacement, content)
                    changes_made = True
            
            if changes_made:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append("orchestrators/session_orchestrator.py - type annotations")
                logger.info("✅ Corrigido: orchestrators/session_orchestrator.py - type annotations")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao corrigir session_orchestrator.py: {e}")
            return False
        
        return False
    
    def run_all_fixes(self) -> dict:
        """
        Executa todas as correções de tipo.
        
        Returns:
            Relatório das correções
        """
        logger.info("🔧 Iniciando correção de erros de tipo...")
        
        fixes = [
            ("coordinators agent_type", self.fix_coordinator_init_agent_type),
            ("orchestrator_manager SessionPriority", self.fix_orchestrator_manager_session_priority),
            ("session_orchestrator type annotations", self.fix_session_orchestrator_type_annotations),
        ]
        
        results = []
        successful_fixes = 0
        
        for fix_name, fix_function in fixes:
            try:
                success = fix_function()
                results.append({
                    'fix': fix_name,
                    'success': success,
                    'error': None
                })
                if success:
                    successful_fixes += 1
            except Exception as e:
                results.append({
                    'fix': fix_name,
                    'success': False,
                    'error': str(e)
                })
        
        report = {
            'total_fixes': len(fixes),
            'successful_fixes': successful_fixes,
            'failed_fixes': len(fixes) - successful_fixes,
            'fixes_applied': self.fixes_applied,
            'results': results
        }
        
        logger.info(f"✅ Correção concluída: {successful_fixes}/{len(fixes)} fixes bem-sucedidos")
        
        return report


def main():
    """Função principal para executar as correções."""
    logging.basicConfig(level=logging.INFO)
    
    fixer = TypeErrorFixer()
    report = fixer.run_all_fixes()
    
    print("\n" + "="*50)
    print("🔧 RELATÓRIO DE CORREÇÃO DE ERROS DE TIPO")
    print("="*50)
    print(f"Total de correções: {report['total_fixes']}")
    print(f"Correções bem-sucedidas: {report['successful_fixes']}")
    print(f"Correções falharam: {report['failed_fixes']}")
    
    print("\n✅ CORREÇÕES APLICADAS:")
    for fix in report['fixes_applied']:
        print(f"  - {fix}")
    
    print("\n📋 DETALHES:")
    for result in report['results']:
        status = "✅ SUCESSO" if result['success'] else "❌ FALHOU"
        print(f"  {status} - {result['fix']}")
        if result['error']:
            print(f"    Erro: {result['error']}")
    
    print("="*50)
    
    return report


if __name__ == "__main__":
    main() 