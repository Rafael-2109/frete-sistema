"""
🏗️ STRUCTURAL ANALYZER - Análise Estrutural
==========================================

Módulo responsável por análise estrutural de código, dados e arquitetura.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StructuralAnalyzer:
    """
    Analisador estrutural para código, dados e arquitetura.
    
    Responsabilidades:
    - Análise de estrutura de código
    - Validação de arquitetura
    - Detecção de problemas estruturais
    - Recomendações de melhoria
    """
    
    def __init__(self):
        """Inicializa o analisador estrutural."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("🏗️ StructuralAnalyzer inicializado")
    
    def analyze_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa estrutura de dados ou código.
        
        Args:
            data: Dados para análise estrutural
            
        Returns:
            Resultado da análise estrutural
        """
        try:
            result = {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'structural',
                'status': 'success',
                'structure_quality': 'good',
                'issues': [],
                'recommendations': [],
                'metrics': {}
            }
            
            # Análise básica de estrutura
            if isinstance(data, dict):
                result['metrics']['total_keys'] = len(data)
                result['metrics']['nested_levels'] = self._count_nested_levels(data)
                result['metrics']['data_types'] = self._analyze_data_types(data)
                
                # Verificar problemas estruturais
                issues = self._detect_structural_issues(data)
                result['issues'] = issues
                
                # Gerar recomendações
                result['recommendations'] = self._generate_recommendations(data, issues)
                
                # Determinar qualidade estrutural
                result['structure_quality'] = self._assess_structure_quality(data, issues)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise estrutural: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'structural',
                'status': 'error',
                'error': str(e),
                'structure_quality': 'unknown'
            }
    
    def validate_architecture(self, architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida arquitetura de sistema.
        
        Args:
            architecture_data: Dados da arquitetura
            
        Returns:
            Resultado da validação
        """
        try:
            validation = {
                'timestamp': datetime.now().isoformat(),
                'validation_type': 'architecture',
                'status': 'valid',
                'score': 100,
                'violations': [],
                'recommendations': []
            }
            
            # Validações arquiteturais básicas
            violations = []
            
            # Verificar componentes essenciais
            if not architecture_data.get('components'):
                violations.append("Componentes não definidos")
            
            # Verificar dependências
            if not architecture_data.get('dependencies'):
                violations.append("Dependências não mapeadas")
            
            # Verificar interfaces
            if not architecture_data.get('interfaces'):
                violations.append("Interfaces não documentadas")
            
            validation['violations'] = violations
            validation['score'] = max(0, 100 - len(violations) * 20)
            
            if violations:
                validation['status'] = 'invalid'
                validation['recommendations'] = [
                    f"Corrigir violação: {v}" for v in violations
                ]
            
            return validation
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação arquitetural: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'validation_type': 'architecture',
                'status': 'error',
                'error': str(e),
                'score': 0
            }
    
    def detect_patterns(self, code_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecta padrões estruturais no código.
        
        Args:
            code_structure: Estrutura do código
            
        Returns:
            Padrões detectados
        """
        try:
            patterns = {
                'timestamp': datetime.now().isoformat(),
                'detected_patterns': [],
                'anti_patterns': [],
                'complexity_score': 0,
                'maintainability': 'good'
            }
            
            # Detectar padrões comuns
            detected = []
            
            if 'classes' in code_structure:
                classes = code_structure['classes']
                if len(classes) > 1:
                    detected.append("Multiple Classes")
                
                for class_name, class_data in classes.items():
                    if 'methods' in class_data:
                        methods = class_data['methods']
                        if len(methods) > 10:
                            detected.append(f"Large Class: {class_name}")
            
            if 'functions' in code_structure:
                functions = code_structure['functions']
                if len(functions) > 20:
                    detected.append("Many Functions")
            
            patterns['detected_patterns'] = detected
            
            # Calcular complexidade
            patterns['complexity_score'] = self._calculate_complexity(code_structure)
            
            # Determinar manutenibilidade
            if patterns['complexity_score'] > 80:
                patterns['maintainability'] = 'poor'
            elif patterns['complexity_score'] > 60:
                patterns['maintainability'] = 'fair'
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ Erro na detecção de padrões: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'detected_patterns': [],
                'complexity_score': 0
            }
    
    def _count_nested_levels(self, data: Dict[str, Any], level: int = 0) -> int:
        """Conta níveis de aninhamento."""
        max_level = level
        for value in data.values():
            if isinstance(value, dict):
                max_level = max(max_level, self._count_nested_levels(value, level + 1))
        return max_level
    
    def _analyze_data_types(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Analisa tipos de dados."""
        types = {}
        for value in data.values():
            type_name = type(value).__name__
            types[type_name] = types.get(type_name, 0) + 1
        return types
    
    def _detect_structural_issues(self, data: Dict[str, Any]) -> List[str]:
        """Detecta problemas estruturais."""
        issues = []
        
        # Verificar profundidade excessiva
        if self._count_nested_levels(data) > 5:
            issues.append("Estrutura muito profunda (>5 níveis)")
        
        # Verificar chaves muito longas
        long_keys = [k for k in data.keys() if len(str(k)) > 50]
        if long_keys:
            issues.append(f"Chaves muito longas: {len(long_keys)}")
        
        # Verificar valores nulos excessivos
        null_values = sum(1 for v in data.values() if v is None)
        if null_values > len(data) * 0.3:
            issues.append("Muitos valores nulos (>30%)")
        
        return issues
    
    def _generate_recommendations(self, data: Dict[str, Any], issues: List[str]) -> List[str]:
        """Gera recomendações."""
        recommendations = []
        
        for issue in issues:
            if "muito profunda" in issue:
                recommendations.append("Considerar refatoração para reduzir aninhamento")
            elif "muito longas" in issue:
                recommendations.append("Encurtar nomes de chaves para melhor legibilidade")
            elif "valores nulos" in issue:
                recommendations.append("Revisar dados para reduzir valores nulos")
        
        return recommendations
    
    def _assess_structure_quality(self, data: Dict[str, Any], issues: List[str]) -> str:
        """Avalia qualidade estrutural."""
        if not issues:
            return "excellent"
        elif len(issues) <= 2:
            return "good"
        elif len(issues) <= 4:
            return "fair"
        else:
            return "poor"
    
    def _calculate_complexity(self, code_structure: Dict[str, Any]) -> int:
        """Calcula pontuação de complexidade."""
        complexity = 0
        
        # Complexidade baseada em classes
        if 'classes' in code_structure:
            classes = code_structure['classes']
            complexity += len(classes) * 10
            
            for class_data in classes.values():
                if 'methods' in class_data:
                    complexity += len(class_data['methods']) * 5
        
        # Complexidade baseada em funções
        if 'functions' in code_structure:
            complexity += len(code_structure['functions']) * 3
        
        return min(complexity, 100)


def get_structural_analyzer() -> StructuralAnalyzer:
    """
    Obtém instância do analisador estrutural.
    
    Returns:
        Instância do StructuralAnalyzer
    """
    return StructuralAnalyzer() 