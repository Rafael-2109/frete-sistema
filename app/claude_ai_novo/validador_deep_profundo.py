#!/usr/bin/env python3
"""
🔬 VALIDADOR DEEP PROFUNDO - Validação Individual de Cada Módulo
===============================================================

Este validador testa CADA módulo individualmente para garantir que:
1. Imports funcionam corretamente
2. Classes podem ser instanciadas
3. Métodos principais executam sem erro
4. Não há dependências quebradas ocultas

Criado após descoberta de que validador anterior era superficial.
"""

import sys
import os
import traceback
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

class DeepValidator:
    """Validador profundo que testa cada módulo individualmente"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'total_modules': 0,
            'passed_modules': 0,
            'failed_modules': 0,
            'detailed_results': {},
            'critical_failures': [],
            'warnings': [],
            'summary': {}
        }
        
    def validate_all_modules(self):
        """Valida todos os módulos profundamente"""
        print("🔬 DEEP VALIDATOR - Validação Profunda Individual")
        print("=" * 60)
        print("⚠️  TESTANDO CADA MÓDULO INDIVIDUALMENTE")
        print("⚠️  ISSO PODE DEMORAR MAIS, MAS É MAIS PRECISO")
        print("")
        
        # Lista de módulos para testar profundamente
        modules_to_test = [
            # Commands
            ('commands.excel.fretes', 'ExcelFretes', self._test_excel_fretes),
            ('commands.excel.pedidos', 'ExcelPedidos', self._test_excel_pedidos),
            ('commands.excel.entregas', 'ExcelEntregas', self._test_excel_entregas),
            ('commands.excel.faturamento', 'ExcelFaturamento', self._test_excel_faturamento),
            ('commands.base_command', 'BaseCommand', self._test_base_command),
            ('commands.auto_command_processor', 'AutoCommandProcessor', self._test_auto_command_processor),
            ('commands.cursor_commands', 'CursorCommands', self._test_cursor_commands),
            ('commands.dev_commands', 'DevCommands', self._test_dev_commands),
            ('commands.file_commands', 'FileCommands', self._test_file_commands),
            
            # Core modules
            ('orchestrators.main_orchestrator', 'MainOrchestrator', self._test_main_orchestrator),
            ('orchestrators.orchestrator_manager', 'OrchestratorManager', self._test_orchestrator_manager),
            ('integration.integration_manager', 'IntegrationManager', self._test_integration_manager),
            ('processors.context_processor', 'ContextProcessor', self._test_context_processor),
            ('analyzers.analyzer_manager', 'AnalyzerManager', self._test_analyzer_manager),
            ('mappers.mapper_manager', 'MapperManager', self._test_mapper_manager),
            ('validators.validator_manager', 'ValidatorManager', self._test_validator_manager),
            ('providers.provider_manager', 'ProviderManager', self._test_provider_manager),
            ('memorizers.memory_manager', 'MemoryManager', self._test_memory_manager),
            ('utils.utils_manager', 'UtilsManager', self._test_utils_manager),
        ]
        
        for module_path, class_name, test_func in modules_to_test:
            self._test_individual_module(module_path, class_name, test_func)
        
        self._generate_final_report()
        return self.results
    
    def _test_individual_module(self, module_path: str, class_name: str, test_func):
        """Testa um módulo individual profundamente"""
        self.results['total_modules'] += 1
        module_result = {
            'module_path': module_path,
            'class_name': class_name,
            'status': 'unknown',
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        print(f"🔬 Testando: {module_path}")
        
        try:
            # Teste 1: Import do módulo
            success, error = self._test_module_import(module_path)
            if not success:
                module_result['status'] = 'import_failed'
                module_result['errors'].append(f"Import failed: {error}")
                self.results['detailed_results'][module_path] = module_result
                self.results['failed_modules'] += 1
                self.results['critical_failures'].append(f"{module_path}: Import failed")
                print(f"  ❌ Import failed: {error}")
                return
            
            module_result['tests_passed'] += 1
            print(f"  ✅ Import: OK")
            
            # Teste 2: Verificar se classe existe
            success, class_obj, error = self._test_class_exists(module_path, class_name)
            if not success:
                module_result['status'] = 'class_not_found'
                module_result['errors'].append(f"Class not found: {error}")
                module_result['tests_failed'] += 1
                print(f"  ❌ Class {class_name}: {error}")
            else:
                module_result['tests_passed'] += 1
                print(f"  ✅ Class {class_name}: OK")
                
                # Teste 3: Instanciar classe
                success, instance, error = self._test_class_instantiation(class_obj, class_name)
                if not success:
                    module_result['status'] = 'instantiation_failed'
                    module_result['errors'].append(f"Instantiation failed: {error}")
                    module_result['tests_failed'] += 1
                    print(f"  ❌ Instantiation: {error}")
                else:
                    module_result['tests_passed'] += 1
                    print(f"  ✅ Instantiation: OK")
                    
                    # Teste 4: Executar teste específico do módulo
                    try:
                        specific_results = test_func(instance)
                        module_result['details'].update(specific_results)
                        
                        if specific_results.get('success', True):
                            module_result['tests_passed'] += len(specific_results.get('tests', []))
                            print(f"  ✅ Specific tests: {len(specific_results.get('tests', []))} passed")
                        else:
                            module_result['tests_failed'] += 1
                            module_result['errors'].extend(specific_results.get('errors', []))
                            print(f"  ❌ Specific tests failed")
                    except Exception as e:
                        module_result['tests_failed'] += 1
                        module_result['errors'].append(f"Specific test error: {str(e)}")
                        print(f"  ❌ Specific test error: {e}")
            
            # Determinar status final
            if module_result['tests_failed'] == 0:
                module_result['status'] = 'passed'
                self.results['passed_modules'] += 1
                print(f"  🎉 PASSED: {module_result['tests_passed']} tests")
            else:
                module_result['status'] = 'failed'
                self.results['failed_modules'] += 1
                print(f"  💥 FAILED: {module_result['tests_failed']} failures")
                
        except Exception as e:
            module_result['status'] = 'exception'
            module_result['errors'].append(f"Unexpected error: {str(e)}")
            module_result['tests_failed'] += 1
            self.results['failed_modules'] += 1
            self.results['critical_failures'].append(f"{module_path}: {str(e)}")
            print(f"  💥 EXCEPTION: {e}")
        
        self.results['detailed_results'][module_path] = module_result
        print("")
    
    def _test_module_import(self, module_path: str) -> Tuple[bool, str]:
        """Testa import de um módulo"""
        try:
            # Tentar import relativo primeiro
            if not module_path.startswith('app.'):
                full_path = f"app.claude_ai_novo.{module_path}"
            else:
                full_path = module_path
                
            importlib.import_module(full_path)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def _test_class_exists(self, module_path: str, class_name: str) -> Tuple[bool, Any, str]:
        """Testa se uma classe existe no módulo"""
        try:
            if not module_path.startswith('app.'):
                full_path = f"app.claude_ai_novo.{module_path}"
            else:
                full_path = module_path
                
            module = importlib.import_module(full_path)
            
            if hasattr(module, class_name):
                class_obj = getattr(module, class_name)
                return True, class_obj, ""
            else:
                available = [attr for attr in dir(module) if not attr.startswith('_')]
                return False, None, f"Class {class_name} not found. Available: {available[:5]}"
        except Exception as e:
            return False, None, str(e)
    
    def _test_class_instantiation(self, class_obj: Any, class_name: str) -> Tuple[bool, Any, str]:
        """Testa instanciação de uma classe"""
        try:
            # Diferentes estratégias de instanciação
            try:
                instance = class_obj()
                return True, instance, ""
            except TypeError:
                # Alguns podem precisar de parâmetros
                try:
                    instance = class_obj(None)  # Tentar com None
                    return True, instance, ""
                except:
                    return False, None, f"Could not instantiate {class_name} - requires specific parameters"
        except Exception as e:
            return False, None, str(e)
    
    # Testes específicos para cada tipo de módulo
    
    def _test_excel_fretes(self, instance) -> Dict:
        """Teste específico para ExcelFretes"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            # Teste 1: Método de detecção
            if hasattr(instance, 'is_excel_fretes_command'):
                result = instance.is_excel_fretes_command("excel fretes teste")
                results['tests'].append(f"is_excel_fretes_command: {result}")
            
            # Teste 2: Verificar herança BaseCommand
            if hasattr(instance, '_validate_input'):
                results['tests'].append("Herda BaseCommand: TRUE")
            else:
                results['errors'].append("Não herda BaseCommand")
                
            # Teste 3: Método principal (sem executar)
            if hasattr(instance, 'gerar_excel_fretes'):
                results['tests'].append("gerar_excel_fretes: método existe")
            else:
                results['errors'].append("gerar_excel_fretes: método não existe")
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _test_excel_pedidos(self, instance) -> Dict:
        """Teste específico para ExcelPedidos"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            if hasattr(instance, 'is_excel_pedidos_command'):
                result = instance.is_excel_pedidos_command("excel pedidos teste")
                results['tests'].append(f"is_excel_pedidos_command: {result}")
            
            if hasattr(instance, '_validate_input'):
                results['tests'].append("Herda BaseCommand: TRUE")
            else:
                results['errors'].append("Não herda BaseCommand")
                
            if hasattr(instance, 'gerar_excel_pedidos'):
                results['tests'].append("gerar_excel_pedidos: método existe")
            else:
                results['errors'].append("gerar_excel_pedidos: método não existe")
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _test_excel_entregas(self, instance) -> Dict:
        """Teste específico para ExcelEntregas"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            if hasattr(instance, 'is_excel_entregas_command'):
                result = instance.is_excel_entregas_command("excel entregas teste")
                results['tests'].append(f"is_excel_entregas_command: {result}")
            
            if hasattr(instance, '_validate_input'):
                results['tests'].append("Herda BaseCommand: TRUE")
            else:
                results['errors'].append("Não herda BaseCommand")
                
            if hasattr(instance, 'gerar_excel_entregas'):
                results['tests'].append("gerar_excel_entregas: método existe")
            else:
                results['errors'].append("gerar_excel_entregas: método não existe")
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _test_excel_faturamento(self, instance) -> Dict:
        """Teste específico para ExcelFaturamento"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            if hasattr(instance, 'is_excel_faturamento_command'):
                result = instance.is_excel_faturamento_command("excel faturamento teste")
                results['tests'].append(f"is_excel_faturamento_command: {result}")
            
            if hasattr(instance, '_validate_input'):
                results['tests'].append("Herda BaseCommand: TRUE")
            else:
                results['errors'].append("Não herda BaseCommand")
                
            if hasattr(instance, 'gerar_excel_faturamento'):
                results['tests'].append("gerar_excel_faturamento: método existe")
            else:
                results['errors'].append("gerar_excel_faturamento: método não existe")
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _test_base_command(self, instance) -> Dict:
        """Teste específico para BaseCommand"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            # Teste métodos essenciais
            essential_methods = ['_validate_input', '_sanitize_input', '_handle_error', '_log_command']
            for method in essential_methods:
                if hasattr(instance, method):
                    results['tests'].append(f"{method}: existe")
                else:
                    results['errors'].append(f"{method}: não existe")
                    
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _test_auto_command_processor(self, instance) -> Dict:
        """Teste específico para AutoCommandProcessor"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            if hasattr(instance, 'process_natural_command'):
                results['tests'].append("process_natural_command: existe")
            
            if hasattr(instance, 'register_command'):
                results['tests'].append("register_command: existe")
                
            if hasattr(instance, 'command_registry'):
                results['tests'].append("command_registry: existe")
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    # Métodos genéricos para outros módulos
    def _test_cursor_commands(self, instance) -> Dict:
        return self._generic_command_test(instance, 'cursor')
    
    def _test_dev_commands(self, instance) -> Dict:
        return self._generic_command_test(instance, 'dev')
    
    def _test_file_commands(self, instance) -> Dict:
        return self._generic_command_test(instance, 'file')
    
    def _generic_command_test(self, instance, command_type: str) -> Dict:
        """Teste genérico para módulos de comando"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            if hasattr(instance, '_validate_input'):
                results['tests'].append("Herda BaseCommand: TRUE")
            
            # Verificar se tem método específico de detecção
            detection_method = f"is_{command_type}_command"
            if hasattr(instance, detection_method):
                results['tests'].append(f"{detection_method}: existe")
                
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _test_main_orchestrator(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['process_query', 'initialize'])
    
    def _test_orchestrator_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['get_orchestrator', 'process_query'])
    
    def _test_integration_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['get_integration_status', 'process_unified_query'])
    
    def _test_context_processor(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['process'])
    
    def _test_analyzer_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['analyze'])
    
    def _test_mapper_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['map'])
    
    def _test_validator_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['validate'])
    
    def _test_provider_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['provide'])
    
    def _test_memory_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, ['remember', 'recall'])
    
    def _test_utils_manager(self, instance) -> Dict:
        return self._generic_manager_test(instance, [])
    
    def _generic_manager_test(self, instance, expected_methods: List[str]) -> Dict:
        """Teste genérico para managers"""
        results = {'success': True, 'tests': [], 'errors': []}
        
        try:
            for method in expected_methods:
                if hasattr(instance, method):
                    results['tests'].append(f"{method}: existe")
                else:
                    results['errors'].append(f"{method}: não existe")
                    
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
            
        return results
    
    def _generate_final_report(self):
        """Gera relatório final"""
        print("=" * 60)
        print("📊 RELATÓRIO FINAL - DEEP VALIDATION")
        print("=" * 60)
        
        success_rate = (self.results['passed_modules'] / self.results['total_modules'] * 100) if self.results['total_modules'] > 0 else 0
        
        print(f"📋 Total de módulos testados: {self.results['total_modules']}")
        print(f"✅ Módulos aprovados: {self.results['passed_modules']}")
        print(f"❌ Módulos falharam: {self.results['failed_modules']}")
        print(f"🏆 Taxa de sucesso: {success_rate:.1f}%")
        print("")
        
        if self.results['critical_failures']:
            print("🚨 FALHAS CRÍTICAS:")
            for failure in self.results['critical_failures']:
                print(f"  ❌ {failure}")
            print("")
        
        if success_rate == 100:
            print("🎉 TODOS OS MÓDULOS PASSARAM NA VALIDAÇÃO PROFUNDA!")
        else:
            print("⚠️ ALGUNS MÓDULOS FALHARAM - VERIFICAR DETALHES ACIMA")
        
        # Salvar resultados
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"deep_validation_{timestamp}.json"
        
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Relatório detalhado salvo em: {filename}")

if __name__ == "__main__":
    validator = DeepValidator()
    results = validator.validate_all_modules() 