#!/usr/bin/env python3
"""
ValidationUtils - Utilitários de Validação Centralizados
========================================================

Responsabilidade: VALIDAR dados, estruturas e regras de negócio
Classe centralizada para evitar dependências circulares
"""

import logging
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)

class BaseValidationUtils:
    """
    Classe centralizada para utilitários de validação genéricos.
    
    Responsabilidades:
    - Validar estruturas de dados
    - Validar regras de negócio genéricas
    - Validar formatos e padrões
    - Validar consistência de dados
    - Sanitização e segurança
    """
    
    def __init__(self):
        """Inicializa BaseValidationUtils"""
        self.logger = logging.getLogger(__name__ + ".BaseValidationUtils")
        self.logger.info("BaseValidationUtils inicializado")
    
    # ========================================================================
    # VALIDAÇÕES BÁSICAS
    # ========================================================================
    
    def validate(self, data: Any, rules: Optional[Dict] = None) -> bool:
        """
        Validação genérica baseada em regras.
        
        Args:
            data: Dados a validar
            rules: Regras de validação (opcional)
            
        Returns:
            bool: True se válido, False caso contrário
        """
        try:
            if data is None:
                return False
                
            if rules is None:
                # Validação básica
                return self._basic_validation(data)
                
            # Validação com regras específicas
            return self._validate_with_rules(data, rules)
            
        except Exception as e:
            self.logger.error(f"Erro na validação: {e}")
            return False
    
    def _basic_validation(self, data: Any) -> bool:
        """Validação básica sem regras específicas"""
        # Validação simples - dados não nulos e não vazios
        if data is None:
            return False
        
        if isinstance(data, str):
            return len(data.strip()) > 0
        
        if isinstance(data, (list, dict)):
            return len(data) > 0
        
        return True
    
    def _validate_with_rules(self, data: Any, rules: Dict) -> bool:
        """Validação com regras específicas"""
        try:
            # Validar tipo
            if 'type' in rules:
                expected_type = rules['type']
                if not isinstance(data, expected_type):
                    return False
            
            # Validar tamanho mínimo
            if 'min_length' in rules:
                if hasattr(data, '__len__') and len(data) < rules['min_length']:
                    return False
            
            # Validar tamanho máximo
            if 'max_length' in rules:
                if hasattr(data, '__len__') and len(data) > rules['max_length']:
                    return False
            
            # Validar padrão regex
            if 'pattern' in rules and isinstance(data, str):
                if not re.match(rules['pattern'], data):
                    return False
            
            # Validar valores permitidos
            if 'allowed_values' in rules:
                if data not in rules['allowed_values']:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação com regras: {e}")
            return False
    
    # ========================================================================
    # VALIDAÇÕES ESPECÍFICAS
    # ========================================================================
    
    def validate_query(self, query: str) -> bool:
        """
        Valida uma consulta/query.
        
        Args:
            query: Consulta a validar
            
        Returns:
            bool: True se válida
        """
        if not isinstance(query, str):
            return False
        
        query = query.strip()
        
        # Validações básicas
        if len(query) == 0:
            return False
        
        if len(query) > 10000:  # Limite máximo
            return False
        
        # Verificar caracteres suspeitos (básico)
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'eval\(',
            r'exec\(',
            r'system\(',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'UPDATE\s+.*\s+SET'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                self.logger.warning(f"Padrão suspeito encontrado na query: {pattern}")
                return False
        
        return True
    
    def validate_context(self, context: Dict) -> bool:
        """
        Valida um contexto de dados.
        
        Args:
            context: Contexto a validar
            
        Returns:
            bool: True se válido
        """
        if not isinstance(context, dict):
            return False
        
        # Validar se tem pelo menos algumas chaves básicas
        if len(context) == 0:
            return False
        
        # Validar tipos de valores
        for key, value in context.items():
            if not isinstance(key, str):
                return False
            
            # Valores None são permitidos
            if value is None:
                continue
            
            # Validar tipos básicos
            if not isinstance(value, (str, int, float, bool, list, dict)):
                return False
        
        return True
    
    def validate_mapping(self, mapping: Dict) -> bool:
        """
        Valida um mapeamento semântico.
        
        Args:
            mapping: Mapeamento a validar
            
        Returns:
            bool: True se válido
        """
        if not isinstance(mapping, dict):
            return False
        
        # Verificar chaves obrigatórias
        required_keys = ['natural_term', 'field', 'model']
        for key in required_keys:
            if key not in mapping:
                return False
            
            if not isinstance(mapping[key], str):
                return False
            
            if len(mapping[key].strip()) == 0:
                return False
        
        return True
    
    def validate_file_path(self, file_path: Union[str, Path]) -> bool:
        """
        Valida um caminho de arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            bool: True se válido
        """
        try:
            path = Path(file_path)
            
            # Verificar se é um caminho válido
            if not path.is_absolute() and not path.exists():
                # Para caminhos relativos, verificar se pelo menos é um path válido
                if '..' in str(path):
                    return False
            
            # Verificar extensão permitida (se for arquivo)
            if path.suffix and path.suffix.lower() not in ['.py', '.json', '.txt', '.md', '.csv', '.xlsx']:
                return False
            
            return True
            
        except Exception:
            return False
    
    def validate_date_range(self, start_date: Any, end_date: Any) -> bool:
        """
        Valida um intervalo de datas.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            bool: True se válido
        """
        try:
            # Converter para datetime se necessário
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Verificar se são datas válidas
            if not isinstance(start_date, (datetime, date)):
                return False
            
            if not isinstance(end_date, (datetime, date)):
                return False
            
            # Verificar se start_date <= end_date
            if start_date > end_date:
                return False
            
            return True
            
        except Exception:
            return False
    
    # ========================================================================
    # VALIDAÇÕES DE DADOS DE NEGÓCIO
    # ========================================================================
    
    def validate_business_rules(self, data: Dict, rules: Dict) -> Dict[str, Any]:
        """
        Valida regras de negócio específicas.
        
        Args:
            data: Dados a validar
            rules: Regras de negócio
            
        Returns:
            Dict com resultado da validação
        """
        try:
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'timestamp': datetime.now().isoformat()
            }
            
            # Validar regras específicas
            for rule_name, rule_config in rules.items():
                rule_result = self._validate_single_rule(data, rule_name, rule_config)
                
                if not rule_result['valid']:
                    result['valid'] = False
                    result['errors'].append({
                        'rule': rule_name,
                        'message': rule_result.get('message', 'Regra não atendida')
                    })
                
                if rule_result.get('warning'):
                    result['warnings'].append({
                        'rule': rule_name,
                        'message': rule_result['warning']
                    })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na validação de regras de negócio: {e}")
            return {
                'valid': False,
                'errors': [{'rule': 'system', 'message': str(e)}],
                'warnings': [],
                'timestamp': datetime.now().isoformat()
            }
    
    def _validate_single_rule(self, data: Dict, rule_name: str, rule_config: Dict) -> Dict[str, Any]:
        """Valida uma regra específica"""
        try:
            # Regra: campo obrigatório
            if rule_config.get('required'):
                field = rule_config.get('field')
                if field and field not in data:
                    return {
                        'valid': False,
                        'message': f'Campo obrigatório: {field}'
                    }
            
            # Regra: valor mínimo
            if 'min_value' in rule_config:
                field = rule_config.get('field')
                if field and field in data:
                    value = data[field]
                    if isinstance(value, (int, float)) and value < rule_config['min_value']:
                        return {
                            'valid': False,
                            'message': f'Valor mínimo para {field}: {rule_config["min_value"]}'
                        }
            
            # Regra: valor máximo
            if 'max_value' in rule_config:
                field = rule_config.get('field')
                if field and field in data:
                    value = data[field]
                    if isinstance(value, (int, float)) and value > rule_config['max_value']:
                        return {
                            'valid': False,
                            'message': f'Valor máximo para {field}: {rule_config["max_value"]}'
                        }
            
            return {'valid': True}
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'Erro na validação da regra {rule_name}: {str(e)}'
            }
    
    # ========================================================================
    # MÉTODOS UTILITÁRIOS
    # ========================================================================
    
    def sanitize_input(self, input_data: str) -> str:
        """
        Sanitiza entrada de dados.
        
        Args:
            input_data: Dados a sanitizar
            
        Returns:
            str: Dados sanitizados
        """
        if not isinstance(input_data, str):
            return str(input_data)
        
        # Remover tags HTML básicas
        input_data = re.sub(r'<[^>]+>', '', input_data)
        
        # Remover caracteres de controle
        input_data = re.sub(r'[\x00-\x1F\x7F]', '', input_data)
        
        # Limitar tamanho
        input_data = input_data[:10000]
        
        return input_data.strip()
    
    def get_validation_summary(self, validations: List[Dict]) -> Dict[str, Any]:
        """
        Gera resumo de validações.
        
        Args:
            validations: Lista de resultados de validação
            
        Returns:
            Dict com resumo
        """
        try:
            total = len(validations)
            valid_count = sum(1 for v in validations if v.get('valid', False))
            invalid_count = total - valid_count
            
            return {
                'total_validations': total,
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'success_rate': round((valid_count / total) * 100, 2) if total > 0 else 0,
                'status': 'PASSED' if invalid_count == 0 else 'FAILED',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo de validações: {e}")
            return {
                'total_validations': 0,
                'valid_count': 0,
                'invalid_count': 0,
                'success_rate': 0,
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Instância global para conveniência
_validation_utils = None

def get_validation_utils() -> BaseValidationUtils:
    """
    Retorna instância global de ValidationUtils.
    
    Returns:
        ValidationUtils: Instância do utilitário
    """
    global _validation_utils
    if _validation_utils is None:
        _validation_utils = BaseValidationUtils()
    return _validation_utils



# Funções de conveniência
def validate_data(data: Any, rules: Optional[Dict] = None) -> bool:
    """Função de conveniência para validação de dados"""
    return get_validation_utils().validate(data, rules)

def validate_query(query: str) -> bool:
    """Função de conveniência para validação de queries"""
    return get_validation_utils().validate_query(query)

def validate_context(context: Dict) -> bool:
    """Função de conveniência para validação de contexto"""
    return get_validation_utils().validate_context(context)

def sanitize_input(input_data: str) -> str:
    """Função de conveniência para sanitização"""
    return get_validation_utils().sanitize_input(input_data)

if __name__ == "__main__":
    # Testes básicos
    print("🧪 Testando BaseValidationUtils...")
    
    utils = get_validation_utils()
    
    # Teste 1: Validação básica
    print(f"✅ Teste 1 - Validação básica: {utils.validate('teste')}")
    print(f"❌ Teste 1 - Validação básica: {utils.validate('')}")
    
    # Teste 2: Validação de query
    print(f"✅ Teste 2 - Query válida: {utils.validate_query('SELECT * FROM users')}")
    print(f"❌ Teste 2 - Query inválida: {utils.validate_query('DROP TABLE users')}")
    
    # Teste 3: Validação de contexto
    print(f"✅ Teste 3 - Contexto válido: {utils.validate_context({'user': 'admin', 'role': 'admin'})}")
    print(f"❌ Teste 3 - Contexto inválido: {utils.validate_context({})}")
    
    print("🎯 Testes concluídos!") 