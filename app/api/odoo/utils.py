"""
Utilitários para API Odoo
"""

import logging
from flask import jsonify
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from app import db
from app.utils.timezone import agora_utc_naive
logger = logging.getLogger(__name__)

def create_response(success: bool, message: str, data: Any = None, errors: Optional[List[str]] = None, 
                   status_code: int = 200, **kwargs) -> tuple:
    """
    Cria resposta padronizada para API
    
    Args:
        success (bool): Se a operação foi bem-sucedida
        message (str): Mensagem descritiva
        data (Any): Dados da resposta
        errors (Optional[List[str]]): Lista de erros
        status_code (int): Código HTTP
        **kwargs: Campos adicionais para resposta
        
    Returns:
        tuple: (resposta_json, status_code)
    """
    response = {
        'success': success,
        'message': message,
        'timestamp': agora_utc_naive().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if errors:
        response['errors'] = errors
    
    # Adicionar campos extras
    response.update(kwargs)
    
    return jsonify(response), status_code

def process_bulk_operation(items: List[Dict], processor_func: Callable, operation_name: str) -> Dict:
    """
    Processa operações em lote com controle de transações
    
    Args:
        items (List[Dict]): Lista de itens para processar
        processor_func (Callable): Função que processa cada item
        operation_name (str): Nome da operação para logs
        
    Returns:
        Dict: Resultado da operação em lote
    """
    result = {
        'processed': 0,
        'created': 0,
        'updated': 0,
        'errors': []
    }
    
    logger.info(f"Iniciando processamento em lote de {operation_name}: {len(items)} itens")
    
    for index, item in enumerate(items):
        try:
            # Processar item individual
            action = processor_func(item)
            
            result['processed'] += 1
            
            if action == 'created':
                result['created'] += 1
            elif action == 'updated':
                result['updated'] += 1
            
            # Log a cada 100 itens processados
            if (index + 1) % 100 == 0:
                logger.info(f"Processados {index + 1}/{len(items)} itens de {operation_name}")
                
        except Exception as e:
            error_msg = f"Erro no item {index + 1}: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(f"Erro ao processar item {index + 1} de {operation_name}: {str(e)}")
            
            # Para operações críticas, pode ser necessário fazer rollback
            # db.session.rollback()
    
    logger.info(f"Processamento em lote de {operation_name} concluído: {result}")
    return result

def validate_date_format(date_str: str, formats: Optional[List[str]] = None) -> str:
    """
    Valida e normaliza formato de data
    
    Args:
        date_str (str): String de data
        formats (Optional[List[str]]): Formatos aceitos
        
    Returns:
        str: Data no formato YYYY-MM-DD
        
    Raises:
        ValueError: Se formato inválido
    """
    if formats is None:
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    raise ValueError(f"Formato de data inválido: {date_str}")

def sanitize_string(value: Any, max_length: Optional[int] = None) -> str:
    """
    Sanitiza string para uso seguro
    
    Args:
        value (Any): Valor a ser sanitizado
        max_length (Optional[int]): Tamanho máximo
        
    Returns:
        str: String sanitizada
    """
    if value is None:
        return ''
    
    # Converter para string
    str_value = str(value).strip()
    
    # Remover caracteres de controle
    str_value = ''.join(char for char in str_value if ord(char) >= 32)
    
    # Limitar tamanho
    if max_length and len(str_value) > max_length:
        str_value = str_value[:max_length]
    
    return str_value

def validate_numeric(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    """
    Valida e converte valor numérico
    
    Args:
        value (Any): Valor a ser validado
        min_value (Optional[float]): Valor mínimo
        max_value (Optional[float]): Valor máximo
        
    Returns:
        float: Valor numérico validado
        
    Raises:
        ValueError: Se valor inválido
    """
    try:
        numeric_value = float(value)
        
        if min_value is not None and numeric_value < min_value:
            raise ValueError(f"Valor {numeric_value} menor que o mínimo {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            raise ValueError(f"Valor {numeric_value} maior que o máximo {max_value}")
        
        return numeric_value
        
    except (ValueError, TypeError):
        raise ValueError(f"Valor numérico inválido: {value}")

def batch_commit(items: List[Any], batch_size: int = 1000) -> None:
    """
    Faz commit em lotes para otimizar performance
    
    Args:
        items (List[Any]): Lista de itens para adicionar
        batch_size (int): Tamanho do lote
    """
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        db.session.add_all(batch)
        
        try:
            db.session.commit()
            logger.info(f"Commit em lote {i//batch_size + 1}: {len(batch)} itens")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro no commit em lote {i//batch_size + 1}: {str(e)}")
            raise

def log_operation(operation: str, user_id: Optional[int] = None, details: Optional[Dict] = None) -> None:
    """
    Registra operação para auditoria
    
    Args:
        operation (str): Tipo de operação
        user_id (Optional[int]): ID do usuário
        details (Optional[Dict]): Detalhes da operação
    """
    try:
        log_entry = {
            'timestamp': agora_utc_naive().isoformat(),
            'operation': operation,
            'user_id': user_id,
            'details': details or {}
        }
        
        logger.info(f"Operação registrada: {log_entry}")
        
        # Em produção, salvar em tabela de auditoria
        # audit_log = AuditLog(**log_entry)
        # db.session.add(audit_log)
        # db.session.commit()
        
    except Exception as e:
        logger.error(f"Erro ao registrar operação: {str(e)}")

def calculate_batch_statistics(results: List[Dict]) -> Dict:
    """
    Calcula estatísticas de operações em lote
    
    Args:
        results (List[Dict]): Lista de resultados
        
    Returns:
        Dict: Estatísticas calculadas
    """
    if not results:
        return {'total': 0, 'success_rate': 0.0, 'error_rate': 0.0}
    
    total = len(results)
    success_count = sum(1 for r in results if r.get('success', False))
    error_count = total - success_count
    
    return {
        'total': total,
        'success_count': success_count,
        'error_count': error_count,
        'success_rate': (success_count / total) * 100 if total > 0 else 0.0,
        'error_rate': (error_count / total) * 100 if total > 0 else 0.0
    }

def format_currency(value: float, currency: str = 'BRL') -> str:
    """
    Formata valor monetário
    
    Args:
        value (float): Valor a ser formatado
        currency (str): Moeda
        
    Returns:
        str: Valor formatado
    """
    try:
        if currency == 'BRL':
            return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"{value:,.2f}"
    except:
        return str(value)

def validate_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ brasileiro
    
    Args:
        cnpj (str): CNPJ a ser validado
        
    Returns:
        bool: True se válido
    """
    # Remover caracteres não numéricos
    cnpj = ''.join(filter(str.isdigit, cnpj))
    
    # Verificar se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verificar se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcular primeiro dígito verificador
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_products = sum(int(cnpj[i]) * weights[i] for i in range(12))
    remainder = sum_products % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    if int(cnpj[12]) != first_digit:
        return False
    
    # Calcular segundo dígito verificador
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_products = sum(int(cnpj[i]) * weights[i] for i in range(13))
    remainder = sum_products % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return int(cnpj[13]) == second_digit

def clean_phone_number(phone: str) -> str:
    """
    Limpa e formata número de telefone
    
    Args:
        phone (str): Número de telefone
        
    Returns:
        str: Número limpo
    """
    if not phone:
        return ''
    
    # Remover caracteres não numéricos
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Formatação básica para números brasileiros
    if len(clean_phone) == 11:  # Celular com DDD
        return f"({clean_phone[:2]}) {clean_phone[2:7]}-{clean_phone[7:]}"
    elif len(clean_phone) == 10:  # Fixo com DDD
        return f"({clean_phone[:2]}) {clean_phone[2:6]}-{clean_phone[6:]}"
    else:
        return clean_phone

def generate_operation_id() -> str:
    """
    Gera ID único para operação
    
    Returns:
        str: ID da operação
    """
    from uuid import uuid4
    return str(uuid4())

def measure_execution_time(func):
    """
    Decorator para medir tempo de execução
    
    Args:
        func: Função a ser medida
        
    Returns:
        function: Função decorada
    """
    from functools import wraps
    import time
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"Função {func.__name__} executada em {execution_time:.3f}s")
        
        return result
    
    return wrapper 