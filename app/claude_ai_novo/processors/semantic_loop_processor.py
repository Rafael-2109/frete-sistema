#!/usr/bin/env python3
"""
🔄 PROCESSADOR DE LOOP SEMÂNTICO-LÓGICO
Sistema de refinamento semântico iterativo para melhorar interpretação de consultas
"""

# Imports da base comum
from .base import ProcessorBase, logging, datetime
from typing import Dict, List, Any

class SemanticLoopProcessor(ProcessorBase):
    """Processador de Loop Semântico-Lógico"""
    
    def __init__(self):
        super().__init__()
        self.loop_history = []
        self.refinement_patterns = {}
        
    async def process_semantic_loop(self, initial_query: str, 
                                  max_iterations: int = 3) -> Dict[str, Any]:
        """Processa consulta através de loop semântico-lógico"""
        
        # Validar entrada
        if not self._validate_input(initial_query):
            return self._get_error_response("Consulta inválida")
        
        # Sanitizar entrada
        query = self._sanitize_input(initial_query)
        
        # Log da operação
        self._log_operation(f"process_semantic_loop", f"query: {query[:50]}...")
        
        # Verificar cache
        cache_key = self._generate_cache_key("semantic_loop", query, max_iterations)
        cached_result = self._get_cached_result(cache_key)
        
        if cached_result:
            self._log_operation("Cache hit para loop semântico")
            return cached_result
        
        start_time = datetime.now()
        
        try:
            loop_result = {
                'initial_query': initial_query,
                'iterations': [],
                'final_interpretation': None,
                'confidence_evolution': [],
                'semantic_refinements': []
            }
            
            current_query = query
            
            for iteration in range(max_iterations):
                self.logger.info(f"🔄 Loop Semântico - Iteração {iteration + 1}")
                
                # Análise semântica
                semantic_analysis = await self._analyze_semantics(current_query)
                
                # Validação lógica
                logic_validation = await self._validate_logic(semantic_analysis)
                
                # Decisão de refinamento
                needs_refinement = logic_validation['confidence'] < 0.8 or \
                                 len(logic_validation['inconsistencies']) > 0
                
                iteration_result = {
                    'iteration': iteration + 1,
                    'query': current_query,
                    'semantic_analysis': semantic_analysis,
                    'logic_validation': logic_validation,
                    'needs_refinement': needs_refinement,
                    'refinement_applied': None
                }
                
                if needs_refinement and iteration < max_iterations - 1:
                    # Aplicar refinamento
                    refined_query = await self._refine_query(current_query, logic_validation)
                    iteration_result['refinement_applied'] = refined_query
                    current_query = refined_query
                    loop_result['semantic_refinements'].append(refined_query)
                
                loop_result['iterations'].append(iteration_result)
                loop_result['confidence_evolution'].append(logic_validation['confidence'])
                
                # Se atingiu confiança alta, parar o loop
                if logic_validation['confidence'] >= 0.9:
                    self._log_operation(f"Confiança alta atingida: {logic_validation['confidence']:.2f}")
                    break
            
            loop_result['final_interpretation'] = current_query
            
            # Adicionar metadados
            processing_time = (datetime.now() - start_time).total_seconds()
            loop_result['metadata'] = {
                'processing_time': processing_time,
                'iterations_used': len(loop_result['iterations']),
                'final_confidence': loop_result['confidence_evolution'][-1] if loop_result['confidence_evolution'] else 0
            }
            
            # Armazenar no cache
            self._set_cached_result(cache_key, loop_result, ttl=600)
            
            return loop_result
            
        except Exception as e:
            return self._get_error_response(f"Erro no loop semântico: {str(e)}")
    
    async def _analyze_semantics(self, query: str) -> Dict[str, Any]:
        """Análise semântica da consulta"""
        
        # Integrar com novo sistema de mapeamento semântico modular
        try:
            from app.claude_ai_novo.orchestrators.semantic_manager import SemanticManager
            semantic_manager = SemanticManager()
            
            # Mapear consulta completa usando nova arquitetura
            try:
                mapping_result = semantic_manager.mapear_consulta_completa(query)
                
                return {
                    'mapped_terms': mapping_result.get('termos_mapeados', []),
                    'confidence': mapping_result.get('confianca_geral', 0.5),
                    'domain_detected': mapping_result.get('dominio_detectado', 'geral'),
                    'semantic_complexity': len(query.split()) / 20.0,  # Normalizado
                    'semantic_manager_used': True  # Indica uso da nova arquitetura
                }
            except (AttributeError, KeyError) as e:
                self.logger.warning(f"Erro no mapeamento semântico modular: {e}")
                # Retornar análise básica sem mapeamento
                return {
                    'mapped_terms': [],
                    'confidence': 0.5,
                    'domain_detected': 'geral',
                    'semantic_complexity': len(query.split()) / 20.0,
                    'semantic_manager_used': False
                }
            
        except Exception as e:
            self.logger.warning(f"Erro na análise semântica: {e}")
            return {
                'mapped_terms': [],
                'confidence': 0.3,
                'domain_detected': 'unknown',
                'semantic_complexity': 0.5,
                'semantic_manager_used': False
            }
    
    async def _validate_logic(self, semantic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validação lógica da interpretação semântica"""
        
        validation = {
            'confidence': semantic_analysis.get('confidence', 0.5),
            'inconsistencies': [],
            'logic_score': 0.8,  # Base score
            'validation_notes': []
        }
        
        # Validar mapeamento de termos
        mapped_terms = semantic_analysis.get('mapped_terms', [])
        if len(mapped_terms) == 0:
            validation['inconsistencies'].append("Nenhum termo foi mapeado semanticamente")
            validation['confidence'] *= 0.5
        
        # Validar coerência de domínio
        domain = semantic_analysis.get('domain_detected', 'unknown')
        if domain == 'unknown':
            validation['inconsistencies'].append("Domínio não identificado claramente")
            validation['confidence'] *= 0.8
        
        # Calcular score lógico final
        if validation['inconsistencies']:
            validation['logic_score'] = max(0.3, validation['logic_score'] - len(validation['inconsistencies']) * 0.2)
        
        validation['confidence'] = (validation['confidence'] + validation['logic_score']) / 2
        
        return validation
    
    async def _refine_query(self, query: str, validation: Dict[str, Any]) -> str:
        """Refina consulta baseado na validação lógica"""
        
        refined_query = query
        
        # Aplicar refinamentos baseados nas inconsistências
        for inconsistency in validation['inconsistencies']:
            if "termo" in inconsistency.lower():
                # Expandir termos não mapeados
                refined_query = self._expand_unmapped_terms(refined_query)
            elif "domínio" in inconsistency.lower():
                # Clarificar domínio
                refined_query = self._clarify_domain_context(refined_query)
        
        self.logger.info(f"🔧 Query refinada: {query} → {refined_query}")
        
        return refined_query
    
    def _expand_unmapped_terms(self, query: str) -> str:
        """Expande termos não mapeados com sinônimos"""
        
        expansions = {
            'entregas': 'entregas monitoradas transportadoras',
            'fretes': 'fretes custos valores transportadoras',
            'pedidos': 'pedidos cotações separação clientes'
        }
        
        for term, expansion in expansions.items():
            if term in query.lower():
                query = query.replace(term, expansion)
                break
        
        return query
    
    def _clarify_domain_context(self, query: str) -> str:
        """Clarifica contexto de domínio"""
        
        # Adicionar contexto específico se não estiver claro
        if not any(domain in query.lower() for domain in ['entrega', 'frete', 'pedido', 'financeiro']):
            query += " (contexto: operações de entrega)"
        
        return query
    
    def _get_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Retorna resposta de erro padronizada"""
        
        return {
            'initial_query': "",
            'iterations': [],
            'final_interpretation': None,
            'confidence_evolution': [0.0],
            'semantic_refinements': [],
            'error': error_msg,
            'metadata': {
                'processing_time': 0,
                'iterations_used': 0,
                'final_confidence': 0.0
            }
        }

# Instância global
_semantic_loop_processor = None

def get_semantic_loop_processor() -> SemanticLoopProcessor:
    """Retorna instância do processador de loop semântico"""
    global _semantic_loop_processor
    if _semantic_loop_processor is None:
        _semantic_loop_processor = SemanticLoopProcessor()
    return _semantic_loop_processor 