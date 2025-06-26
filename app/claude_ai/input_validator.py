"""
🛡️ VALIDADOR DE ENTRADA - Sistema Claude AI
Centraliza validação de dados de entrada para evitar vulnerabilidades
"""

import re
from typing import Dict, Any, Optional, List, Union
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """Validador centralizado de entrada para o sistema Claude AI"""
    
    # Limites seguros
    MAX_QUERY_LENGTH = 5000
    MAX_CLIENT_NAME_LENGTH = 200
    MAX_FILENAME_LENGTH = 255
    MAX_JSON_SIZE = 1024 * 1024  # 1MB
    
    # Padrões de validação
    PATTERNS = {
        'query': re.compile(r'^[\w\s\.,;:!?\-áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ()[\]{}/@#$%&*+=<>"\'\n]+$', re.UNICODE),
        'client_name': re.compile(r'^[\w\s\-\.áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]+$', re.UNICODE),
        'filename': re.compile(r'^[\w\-\.]+$'),
        'date': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
        'cnpj': re.compile(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$'),
        'nf': re.compile(r'^\d{6}$'),
        'integer': re.compile(r'^\d+$'),
        'float': re.compile(r'^\d+(\.\d{1,2})?$')
    }
    
    # Palavras-chave perigosas (SQL injection, XSS, etc)
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'EXEC', 'EXECUTE',
        '<script', 'javascript:', 'onerror=', 'onload=', 'onclick=',
        '../', '..\\', 'file://', 'ftp://', 'ssh://',
        'SELECT * FROM', 'UNION SELECT', 'OR 1=1', '; --'
    ]
    
    @classmethod
    def validate_query(cls, query: Optional[str]) -> tuple[bool, str]:
        """
        Valida consulta do usuário
        
        Returns:
            tuple: (válido, mensagem_erro)
        """
        if not query:
            return False, "Consulta não pode estar vazia"
            
        if isinstance(query, str):
            query = query.strip()
        else:
            return False, "Consulta deve ser uma string"
            
        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, f"Consulta muito longa (máximo {cls.MAX_QUERY_LENGTH} caracteres)"
            
        # Verificar palavras-chave perigosas
        query_upper = query.upper()
        for keyword in cls.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                logger.warning(f"⚠️ Palavra-chave perigosa detectada: {keyword}")
                return False, "Consulta contém termos não permitidos"
        
        return True, ""
    
    @classmethod
    def validate_client_name(cls, name: Optional[str]) -> tuple[bool, str]:
        """Valida nome de cliente"""
        if not name:
            return True, ""  # Nome opcional
            
        if not isinstance(name, str):
            return False, "Nome do cliente deve ser uma string"
            
        name = name.strip()
        if len(name) > cls.MAX_CLIENT_NAME_LENGTH:
            return False, f"Nome muito longo (máximo {cls.MAX_CLIENT_NAME_LENGTH} caracteres)"
            
        if not cls.PATTERNS['client_name'].match(name):
            return False, "Nome contém caracteres inválidos"
            
        return True, ""
    
    @classmethod
    def validate_date_range(cls, start_date: Optional[str], end_date: Optional[str]) -> tuple[bool, str]:
        """Valida intervalo de datas"""
        if start_date and not cls.PATTERNS['date'].match(str(start_date)):
            return False, "Data inicial inválida (formato: AAAA-MM-DD)"
            
        if end_date and not cls.PATTERNS['date'].match(str(end_date)):
            return False, "Data final inválida (formato: AAAA-MM-DD)"
            
        if start_date and end_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                
                if start > end:
                    return False, "Data inicial não pode ser maior que data final"
                    
                # Limite de 1 ano
                if (end - start).days > 365:
                    return False, "Intervalo máximo permitido: 1 ano"
                    
            except ValueError:
                return False, "Formato de data inválido"
                
        return True, ""
    
    @classmethod
    def validate_json_request(cls, data: Any, required_fields: Optional[List[str]] = None) -> tuple[bool, str, Dict]:
        """
        Valida requisição JSON completa
        
        Args:
            data: Dados JSON da requisição
            required_fields: Lista de campos obrigatórios
            
        Returns:
            tuple: (válido, mensagem_erro, dados_validados)
        """
        if not data:
            return False, "Dados JSON não fornecidos", {}
            
        if not isinstance(data, dict):
            return False, "Dados devem ser um objeto JSON", {}
            
        # Verificar tamanho
        import json
        json_str = json.dumps(data)
        if len(json_str) > cls.MAX_JSON_SIZE:
            return False, f"JSON muito grande (máximo {cls.MAX_JSON_SIZE/1024/1024:.1f}MB)", {}
            
        # Verificar campos obrigatórios
        if required_fields:
            for field in required_fields:
                if field not in data:
                    return False, f"Campo obrigatório ausente: {field}", {}
        
        # Validar campos individuais
        validated_data = {}
        
        # Query
        if 'query' in data:
            valid, msg = cls.validate_query(data['query'])
            if not valid:
                return False, msg, {}
            validated_data['query'] = data['query'].strip()
        
        # Cliente
        if 'client' in data:
            valid, msg = cls.validate_client_name(data['client'])
            if not valid:
                return False, msg, {}
            validated_data['client'] = data['client'].strip() if data['client'] else None
        
        # Datas
        if 'start_date' in data or 'end_date' in data:
            valid, msg = cls.validate_date_range(
                data.get('start_date'),
                data.get('end_date')
            )
            if not valid:
                return False, msg, {}
            validated_data['start_date'] = data.get('start_date')
            validated_data['end_date'] = data.get('end_date')
        
        # Outros campos seguros
        safe_fields = ['csrf_token', 'context_id', 'session_id', 'feedback_type']
        for field in safe_fields:
            if field in data:
                validated_data[field] = data[field]
        
        return True, "", validated_data
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> Optional[str]:
        """
        Sanitiza nome de arquivo para download seguro
        
        Returns:
            Nome sanitizado ou None se inválido
        """
        if not filename:
            return None
            
        # Remover path traversal
        import os
        filename = os.path.basename(filename)
        
        # Verificar extensão permitida
        allowed_extensions = ['.xlsx', '.xls', '.csv', '.pdf', '.json']
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return None
            
        # Verificar padrão
        if not cls.PATTERNS['filename'].match(filename):
            return None
            
        # Limitar tamanho
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            return None
            
        return filename
    
    @classmethod
    def validate_pagination(cls, page: Any, per_page: Any) -> tuple[int, int]:
        """
        Valida e sanitiza parâmetros de paginação
        
        Returns:
            tuple: (page, per_page) sanitizados
        """
        try:
            page = int(page) if page else 1
            per_page = int(per_page) if per_page else 20
        except (ValueError, TypeError):
            page, per_page = 1, 20
        
        # Limites seguros
        page = max(1, min(page, 10000))
        per_page = max(5, min(per_page, 100))
        
        return page, per_page
    
    @classmethod
    def validate_nf_list(cls, nfs: Union[str, List[str]]) -> tuple[bool, str, List[str]]:
        """
        Valida lista de NFs
        
        Returns:
            tuple: (válido, mensagem_erro, lista_validada)
        """
        if isinstance(nfs, str):
            # Converter string separada por vírgulas em lista
            nfs = [nf.strip() for nf in nfs.split(',') if nf.strip()]
        
        if not isinstance(nfs, list):
            return False, "Lista de NFs inválida", []
        
        # Limite de NFs
        if len(nfs) > 100:
            return False, "Máximo 100 NFs por consulta", []
        
        validated_nfs = []
        for nf in nfs:
            if cls.PATTERNS['nf'].match(str(nf)):
                validated_nfs.append(str(nf))
            else:
                return False, f"NF inválida: {nf}", []
        
        return True, "", validated_nfs
    
    @classmethod
    def escape_html(cls, text: str) -> str:
        """Escapa HTML para prevenir XSS"""
        if not text:
            return ""
            
        import html
        return html.escape(str(text))
    
    @classmethod
    def validate_api_key(cls, key: Optional[str]) -> bool:
        """Valida formato de API key"""
        if not key:
            return False
            
        # Formato básico de API key (ajustar conforme necessário)
        if not re.match(r'^[A-Za-z0-9\-_]{32,128}$', key):
            return False
            
        return True 