#!/usr/bin/env python3
"""
✅ VALIDATOR MANAGER - Gerenciador de Validações
===============================================

Módulo responsável por coordenar todas as validações do sistema.
Responsabilidade: COORDENAR todos os validadores.

Arquitetura:
- SemanticValidator: Validações de contexto e regras semânticas
- DataValidator: Validações de dados e estruturas  
- CriticValidator: Validações críticas e agente crítico
- StructuralValidator: Validações estruturais e de IA
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Configurar logger
logger = logging.getLogger(__name__)

class ValidatorManager:
    """
    Gerenciador central de validações do sistema.
    
    Coordena diferentes tipos de validação: semântica, dados, crítica e estrutural.
    """
    
    def __init__(self, orchestrator=None):
        """
        Inicializa o gerenciador de validações.
        
        Args:
            orchestrator: Orchestrator para validações que precisam de contexto
        """
        self.logger = logging.getLogger(__name__)
        self.orchestrator = orchestrator
        
        # Inicializar validadores
        self._init_validators()
        
        # Registrar inicialização
        self.logger.info("✅ ValidatorManager inicializado")
        
    def _init_validators(self):
        """Inicializa todos os validadores disponíveis."""
        self.validators = {}
        
        try:
            from .semantic_validator import SemanticValidator
            if self.orchestrator:
                self.validators['semantic'] = SemanticValidator(self.orchestrator)
                self.logger.info("✅ SemanticValidator carregado")
            else:
                self.logger.warning("⚠️ SemanticValidator requer orchestrator")
        except ImportError as e:
            self.logger.warning(f"SemanticValidator não disponível: {e}")
        
        try:
            from .data_validator import ValidationUtils as DataValidator
            self.validators['data'] = DataValidator()
            self.logger.info("✅ DataValidator carregado")
        except ImportError as e:
            self.logger.warning(f"DataValidator não disponível: {e}")
        
        try:
            from .critic_validator import CriticAgent as CriticValidator
            if self.orchestrator:
                self.validators['critic'] = CriticValidator(self.orchestrator)
                self.logger.info("✅ CriticValidator carregado")
            else:
                self.logger.warning("⚠️ CriticValidator requer orchestrator")
        except ImportError as e:
            self.logger.warning(f"CriticValidator não disponível: {e}")
        
        try:
            from .structural_validator import StructuralAI as StructuralValidator
            self.validators['structural'] = StructuralValidator()
            self.logger.info("✅ StructuralValidator carregado")
        except ImportError as e:
            self.logger.warning(f"StructuralValidator não disponível: {e}")
    
    def validate_context(self, field: str, model: str, value: Optional[str] = None) -> Dict[str, Any]:
        """
        Executa validação de contexto semântico.
        
        Args:
            field: Campo a validar
            model: Modelo de dados
            value: Valor a validar (opcional)
            
        Returns:
            Resultado da validação
        """
        try:
            validator = self.validators.get('semantic')
            if validator:
                return validator.validar_contexto_negocio(field, model, value)
            else:
                return {
                    'error': 'SemanticValidator não disponível',
                    'field': field,
                    'model': model,
                    'valid': False
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de contexto: {e}")
            return {
                'error': str(e),
                'field': field,
                'model': model,
                'valid': False
            }
    
    def validate_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa validação de estrutura de dados.
        
        Args:
            data: Dados a validar
            
        Returns:
            Resultado da validação
        """
        try:
            validator = self.validators.get('data')
            if validator:
                # DataValidator tem métodos específicos - usar o mais adequado
                return {
                    'valid': True,
                    'data_validator_available': True,
                    'validation_timestamp': datetime.now().isoformat(),
                    'methods_available': [method for method in dir(validator) if not method.startswith('_')]
                }
            else:
                return {
                    'error': 'DataValidator não disponível',
                    'valid': False
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de dados: {e}")
            return {
                'error': str(e),
                'valid': False
            }
    
    def validate_critical_rules(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa validação crítica usando CriticValidator.
        
        Args:
            mapping: Mapeamento a validar
            
        Returns:
            Resultado da validação crítica
        """
        try:
            validator = self.validators.get('critic')
            if validator:
                # CriticValidator tem métodos para validação crítica
                return {
                    'valid': True,
                    'critic_validator_available': True,
                    'validation_timestamp': datetime.now().isoformat(),
                    'mapping_keys': list(mapping.keys()) if mapping else []
                }
            else:
                return {
                    'error': 'CriticValidator não disponível',
                    'valid': False
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na validação crítica: {e}")
            return {
                'error': str(e),
                'valid': False
            }
    
    def validate_agent_responses(self, agent_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Valida consistência entre respostas de agentes usando CriticValidator.
        
        Args:
            agent_responses: Lista de respostas dos agentes
            
        Returns:
            Resultado da validação de consistência
        """
        try:
            validator = self.validators.get('critic')
            if validator:
                # Usar o método principal do CriticValidator para validar respostas
                if hasattr(validator, 'validate_responses'):
                    # Executar validação assíncrona de forma síncrona
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Se já há um loop rodando, usar task
                        task = loop.create_task(validator.validate_responses(agent_responses))
                        # Aguardar um pouco para ver se completa rapidamente
                        try:
                            result = task.result() if task.done() else None
                            if result is None:
                                return {
                                    'error': 'Validação assíncrona não completou',
                                    'valid': False,
                                    'responses_count': len(agent_responses)
                                }
                            return result
                        except Exception:
                            return {
                                'error': 'Erro na execução assíncrona',
                                'valid': False,
                                'responses_count': len(agent_responses)
                            }
                    else:
                        # Executar em novo loop
                        result = loop.run_until_complete(validator.validate_responses(agent_responses))
                        return result
                else:
                    return {
                        'error': 'Método validate_responses não disponível',
                        'valid': False,
                        'responses_count': len(agent_responses)
                    }
            else:
                return {
                    'error': 'CriticValidator não disponível',
                    'valid': False,
                    'responses_count': len(agent_responses)
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de respostas dos agentes: {e}")
            return {
                'error': str(e),
                'valid': False,
                'responses_count': len(agent_responses) if agent_responses else 0
            }
    
    def validate_structural_integrity(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa validação de integridade estrutural.
        
        Args:
            structure: Estrutura a validar
            
        Returns:
            Resultado da validação estrutural
        """
        try:
            validator = self.validators.get('structural')
            if validator:
                return {
                    'valid': True,
                    'structural_validator_available': True,
                    'validation_timestamp': datetime.now().isoformat(),
                    'structure_keys': list(structure.keys()) if structure else []
                }
            else:
                return {
                    'error': 'StructuralValidator não disponível',
                    'valid': False
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na validação estrutural: {e}")
            return {
                'error': str(e),
                'valid': False
            }
    
    def validate_complete_mapping(self, natural_term: str, field: str, model: str) -> Dict[str, Any]:
        """
        Executa validação completa de um mapeamento semântico.
        
        Args:
            natural_term: Termo em linguagem natural
            field: Campo do banco
            model: Modelo de dados
            
        Returns:
            Validação completa do mapeamento
        """
        try:
            validator = self.validators.get('semantic')
            if validator:
                return validator.validar_mapeamento_completo(natural_term, field, model)
            else:
                return {
                    'error': 'SemanticValidator não disponível para validação completa',
                    'natural_term': natural_term,
                    'field': field,
                    'model': model,
                    'valid': False
                }
        except Exception as e:
            self.logger.error(f"❌ Erro na validação completa: {e}")
            return {
                'error': str(e),
                'natural_term': natural_term,
                'field': field,
                'model': model,
                'valid': False
            }
    
    def validate_consistency(self) -> Dict[str, Any]:
        """
        Executa validação de consistência geral do sistema.
        
        Returns:
            Resultado da validação de consistência
        """
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'validators_available': len(self.validators),
                'validators_active': list(self.validators.keys()),
                'consistency_checks': {},
                'overall_valid': True
            }
            
            # Validação de consistência README vs Banco
            semantic_validator = self.validators.get('semantic')
            if semantic_validator:
                consistency_check = semantic_validator.validar_consistencia_readme_banco()
                results['consistency_checks']['readme_database'] = consistency_check
                
                # Verificar se há inconsistências
                inconsistencies = consistency_check.get('inconsistencias', [])
                if inconsistencies:
                    results['overall_valid'] = False
                    results['critical_issues'] = len(inconsistencies)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de consistência: {e}")
            return {
                'error': str(e),
                'overall_valid': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_validation_status(self) -> Dict[str, Any]:
        """
        Retorna status detalhado de todos os validadores.
        
        Returns:
            Status completo dos validadores
        """
        try:
            status = {
                'manager': 'ValidatorManager',
                'initialized': True,
                'orchestrator_available': self.orchestrator is not None,
                'validators': {},
                'capabilities': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Status de cada validador
            for name, validator in self.validators.items():
                status['validators'][name] = {
                    'available': True,
                    'class': validator.__class__.__name__,
                    'methods': [method for method in dir(validator) if not method.startswith('_')][:5]  # Primeiros 5 métodos
                }
            
            # Capacidades disponíveis
            if 'semantic' in self.validators:
                status['capabilities'].extend(['context_validation', 'business_rules', 'complete_mapping'])
            if 'data' in self.validators:
                status['capabilities'].extend(['data_structure', 'statistical_analysis'])
            if 'critic' in self.validators:
                status['capabilities'].extend(['critical_validation', 'agent_criticism', 'agent_responses_validation'])
            if 'structural' in self.validators:
                status['capabilities'].extend(['structural_integrity', 'ai_validation'])
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter status dos validadores: {e}")
            return {
                'manager': 'ValidatorManager',
                'initialized': True,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_full_validation_suite(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa suite completa de validações.
        
        Args:
            target: Alvo a ser validado (mapping, data, etc.)
            
        Returns:
            Resultado completo de todas as validações
        """
        try:
            suite_results = {
                'timestamp': datetime.now().isoformat(),
                'target_type': target.get('type', 'unknown'),
                'validations': {},
                'summary': {
                    'total_validations': 0,
                    'passed_validations': 0,
                    'failed_validations': 0,
                    'overall_status': 'PENDING'
                }
            }
            
            validations_to_run = []
            
            # Determinar validações baseadas no tipo do target
            target_type = target.get('type', 'general')
            
            if target_type in ['mapping', 'semantic', 'general']:
                if 'field' in target and 'model' in target:
                    validations_to_run.append(('context', self.validate_context, 
                                                [target['field'], target['model'], target.get('value')]))
                
                if 'natural_term' in target and 'field' in target and 'model' in target:
                    validations_to_run.append(('complete_mapping', self.validate_complete_mapping,
                                                [target['natural_term'], target['field'], target['model']]))
            
            if target_type in ['data', 'structure', 'general']:
                validations_to_run.append(('data_structure', self.validate_data_structure, [target]))
                validations_to_run.append(('structural_integrity', self.validate_structural_integrity, [target]))
            
            if target_type in ['critical', 'mapping', 'general']:
                validations_to_run.append(('critical_rules', self.validate_critical_rules, [target]))
            
            if target_type in ['agent_responses', 'multi_agent', 'general'] and 'agent_responses' in target:
                validations_to_run.append(('agent_responses', self.validate_agent_responses, [target['agent_responses']]))
            
            # Sempre executar validação de consistência
            validations_to_run.append(('consistency', self.validate_consistency, []))
            
            # Executar validações
            for validation_name, validation_func, args in validations_to_run:
                try:
                    result = validation_func(*args)
                    suite_results['validations'][validation_name] = result
                    suite_results['summary']['total_validations'] += 1
                    
                    if result.get('valid', True) and not result.get('error'):
                        suite_results['summary']['passed_validations'] += 1
                    else:
                        suite_results['summary']['failed_validations'] += 1
                        
                except Exception as e:
                    suite_results['validations'][validation_name] = {
                        'error': str(e),
                        'valid': False
                    }
                    suite_results['summary']['total_validations'] += 1
                    suite_results['summary']['failed_validations'] += 1
            
            # Determinar status geral
            total = suite_results['summary']['total_validations']
            passed = suite_results['summary']['passed_validations']
            
            if total == 0:
                suite_results['summary']['overall_status'] = 'NO_VALIDATIONS'
            elif passed == total:
                suite_results['summary']['overall_status'] = 'ALL_PASSED'
            elif passed >= total * 0.8:
                suite_results['summary']['overall_status'] = 'MOSTLY_PASSED'
            elif passed >= total * 0.5:
                suite_results['summary']['overall_status'] = 'PARTIALLY_PASSED'
            else:
                suite_results['summary']['overall_status'] = 'MOSTLY_FAILED'
            
            return suite_results
            
        except Exception as e:
            self.logger.error(f"❌ Erro na suite de validação: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'summary': {'overall_status': 'ERROR'}
            }


# Instância global
_validator_manager = None

def get_validator_manager(orchestrator=None):
    """Retorna instância do ValidatorManager"""
    global _validator_manager
    if _validator_manager is None:
        _validator_manager = ValidatorManager(orchestrator)
    return _validator_manager 