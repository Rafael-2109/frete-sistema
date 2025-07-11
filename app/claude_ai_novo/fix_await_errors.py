"""
🔧 FIX AWAIT ERRORS - Correção de Erros de Await
================================================

Script para detectar e corrigir erros críticos de await:
1. await sendo usado em objetos dict
2. await sendo usado em funções não async
3. await sendo usado incorretamente no sistema

Problema típico:
- await some_dict  # ERRO: dict não é awaitable
- await sync_function()  # ERRO: função não é async
"""

import os
import re
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class AwaitErrorFixer:
    """
    Detector e corretor de erros de await no sistema.
    """
    
    def __init__(self, base_path: str = "app/claude_ai_novo"):
        self.base_path = Path(base_path)
        self.errors_found = []
        self.fixes_applied = []
        
    def scan_await_errors(self) -> List[Dict[str, Any]]:
        """
        Escaneia todos os arquivos Python procurando por erros de await.
        
        Returns:
            Lista de erros encontrados
        """
        errors = []
        
        # Padrões problemáticos comuns
        patterns = [
            (r'await\s+\w+\s*\{', "await sendo usado em dict literal"),
            (r'await\s+\w+\s*\[', "await sendo usado em list/dict access"),
            (r'await\s+\w+\.\w+\s*\(.*\)', "await em método que pode não ser async"),
            (r'await\s+\w+\s*=', "await em atribuição incorreta"),
            (r'await\s+\{', "await direto em dict"),
            (r'await\s+\[', "await direto em list"),
        ]
        
        for py_file in self.base_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern, description in patterns:
                            if re.search(pattern, line):
                                errors.append({
                                    'file': str(py_file),
                                    'line': line_num,
                                    'content': line.strip(),
                                    'pattern': pattern,
                                    'description': description,
                                    'type': 'await_error'
                                })
                                
            except Exception as e:
                logger.warning(f"Erro ao processar {py_file}: {e}")
                
        return errors
    
    def detect_specific_await_dict_errors(self) -> List[Dict[str, Any]]:
        """
        Detecta especificamente erros de await em dict.
        
        Returns:
            Lista de erros específicos
        """
        errors = []
        
        # Arquivos críticos para verificar
        critical_files = [
            "integration/integration_manager.py",
            "orchestrators/orchestrator_manager.py",
            "orchestrators/main_orchestrator.py",
            "orchestrators/session_orchestrator.py",
            "orchestrators/workflow_orchestrator.py",
            "processors/query_processor.py",
            "processors/response_processor.py"
        ]
        
        for file_path in critical_files:
            full_path = self.base_path / file_path
            if full_path.exists():
                errors.extend(self._check_file_for_await_dict_errors(full_path))
        
        return errors
    
    def _check_file_for_await_dict_errors(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Verifica um arquivo específico para erros de await.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Lista de erros encontrados
        """
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    # Detectar await em dict
                    if re.search(r'await\s+\w+\s*\{', stripped):
                        errors.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': stripped,
                            'type': 'await_dict_literal',
                            'severity': 'critical'
                        })
                    
                    # Detectar await em resultado que pode ser dict
                    if re.search(r'await\s+\w+\.\w+\(.*\)', stripped):
                        # Verificar se a função chamada retorna dict
                        function_match = re.search(r'await\s+\w+\.(\w+)\(', stripped)
                        if function_match:
                            function_name = function_match.group(1)
                            if function_name in ['process_query', 'get_status', 'get_result']:
                                errors.append({
                                    'file': str(file_path),
                                    'line': line_num,
                                    'content': stripped,
                                    'type': 'await_dict_returning_function',
                                    'function': function_name,
                                    'severity': 'high'
                                })
                    
                    # Detectar await em funções não async conhecidas
                    non_async_functions = [
                        'process_unified_query', 'get_system_status', 'get_integration_status',
                        'process_query', 'orchestrate_operation', 'validate_operation_security'
                    ]
                    
                    for func_name in non_async_functions:
                        if f'await {func_name}' in stripped or f'await self.{func_name}' in stripped:
                            errors.append({
                                'file': str(file_path),
                                'line': line_num,
                                'content': stripped,
                                'type': 'await_non_async_function',
                                'function': func_name,
                                'severity': 'critical'
                            })
                            
        except Exception as e:
            logger.error(f"Erro ao verificar {file_path}: {e}")
            
        return errors
    
    def fix_await_errors(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Corrige erros de await encontrados.
        
        Args:
            errors: Lista de erros a corrigir
            
        Returns:
            Lista de correções aplicadas
        """
        fixes = []
        
        # Agrupar erros por arquivo
        files_to_fix = {}
        for error in errors:
            file_path = error['file']
            if file_path not in files_to_fix:
                files_to_fix[file_path] = []
            files_to_fix[file_path].append(error)
        
        # Aplicar correções por arquivo
        for file_path, file_errors in files_to_fix.items():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                original_content = content
                
                # Aplicar correções específicas
                for error in file_errors:
                    if error['type'] == 'await_non_async_function':
                        # Remover await de funções não async
                        old_line = error['content']
                        new_line = re.sub(r'await\s+', '', old_line)
                        content = content.replace(old_line, new_line)
                        
                        fixes.append({
                            'file': file_path,
                            'line': error['line'],
                            'old': old_line,
                            'new': new_line,
                            'type': 'removed_await_from_non_async'
                        })
                    
                    elif error['type'] == 'await_dict_returning_function':
                        # Para funções que retornam dict, remover await
                        old_line = error['content']
                        new_line = re.sub(r'await\s+', '', old_line)
                        content = content.replace(old_line, new_line)
                        
                        fixes.append({
                            'file': file_path,
                            'line': error['line'],
                            'old': old_line,
                            'new': new_line,
                            'type': 'removed_await_from_dict_function'
                        })
                
                # Salvar arquivo se houve alterações
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.info(f"✅ Correções aplicadas em {file_path}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao corrigir {file_path}: {e}")
                
        return fixes
    
    def run_full_fix(self) -> Dict[str, Any]:
        """
        Executa correção completa de erros de await.
        
        Returns:
            Relatório da correção
        """
        logger.info("🔧 Iniciando correção de erros de await...")
        
        # Detectar erros
        general_errors = self.scan_await_errors()
        specific_errors = self.detect_specific_await_dict_errors()
        
        all_errors = general_errors + specific_errors
        
        # Remover duplicatas
        unique_errors = []
        seen = set()
        for error in all_errors:
            key = (error['file'], error['line'], error['content'])
            if key not in seen:
                unique_errors.append(error)
                seen.add(key)
        
        logger.info(f"🔍 Encontrados {len(unique_errors)} erros de await")
        
        # Aplicar correções
        fixes = self.fix_await_errors(unique_errors)
        
        # Relatório
        report = {
            'success': True,
            'errors_found': len(unique_errors),
            'fixes_applied': len(fixes),
            'errors': unique_errors,
            'fixes': fixes,
            'critical_errors': [e for e in unique_errors if e.get('severity') == 'critical'],
            'high_errors': [e for e in unique_errors if e.get('severity') == 'high']
        }
        
        logger.info(f"✅ Correção concluída: {len(fixes)} fixes aplicados")
        
        return report


def main():
    """Função principal para executar as correções."""
    logging.basicConfig(level=logging.INFO)
    
    fixer = AwaitErrorFixer()
    report = fixer.run_full_fix()
    
    print("\n" + "="*50)
    print("🔧 RELATÓRIO DE CORREÇÃO DE ERROS DE AWAIT")
    print("="*50)
    print(f"Erros encontrados: {report['errors_found']}")
    print(f"Correções aplicadas: {report['fixes_applied']}")
    print(f"Erros críticos: {len(report['critical_errors'])}")
    print(f"Erros de alta prioridade: {len(report['high_errors'])}")
    
    if report['critical_errors']:
        print("\n🚨 ERROS CRÍTICOS:")
        for error in report['critical_errors']:
            print(f"  - {error['file']}:{error['line']} - {error['content']}")
    
    if report['fixes']:
        print("\n✅ CORREÇÕES APLICADAS:")
        for fix in report['fixes']:
            print(f"  - {fix['file']}:{fix['line']} - {fix['type']}")
    
    print("\n" + "="*50)
    
    return report


if __name__ == "__main__":
    main() 